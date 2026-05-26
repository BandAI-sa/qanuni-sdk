"""Runtime layer shared by the Qanuni MCP server and its tests."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from uuid import uuid4

from pydantic import BaseModel

from qanuni.client import LegalClient
from qanuni.core.exceptions import ErrorCode, QanuniError, QanuniValidationError
from qanuni.legal_references import LegalReferenceLoader
from qanuni.mcp.audit import QanuniMcpAuditLogger
from qanuni.mcp.models import McpAuditEvent, McpExecutionEnvelope, McpResourceLinks, McpRunRecord
from qanuni.mcp.run_store import QanuniMcpRunStore
from qanuni.mcp.surface import McpReferencePacketDescriptor, McpSurfaceMetadata, McpSurfaceRegistry


class QanuniMcpRuntime:
    """Execute curated SDK surfaces and expose their persisted run resources.

    Args:
        client: Shared SDK client used to execute tools and workflows.
        surface_registry: Optional curated surface registry override.
        run_store: Optional execution store used for follow-up resources.
        audit_logger: Optional audit logger used for tool and resource events.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        client: LegalClient,
        *,
        surface_registry: McpSurfaceRegistry | None = None,
        run_store: QanuniMcpRunStore | None = None,
        audit_logger: QanuniMcpAuditLogger | None = None,
    ) -> None:
        """Store the dependencies used by MCP tools and resources.

        Args:
            client: Shared SDK client used to execute tools and workflows.
            surface_registry: Optional curated surface registry override.
            run_store: Optional execution store used for follow-up resources.
            audit_logger: Optional audit logger used for tool and resource events.

        Returns:
            None.

        Raises:
            None.
        """
        self._client: LegalClient = client
        self._surface_registry: McpSurfaceRegistry = surface_registry or McpSurfaceRegistry()
        self._run_store: QanuniMcpRunStore = run_store or QanuniMcpRunStore()
        self._audit_logger: QanuniMcpAuditLogger | None = audit_logger

    def list_surfaces(self) -> list[McpSurfaceMetadata]:
        """Return the curated MCP surfaces supported by this runtime.

        Args:
            None.

        Returns:
            A list of curated surface metadata records.

        Raises:
            None.
        """
        return self._surface_registry.list_surfaces()

    def invoke_surface(
        self,
        surface_id: str,
        payload: BaseModel | dict[str, object],
        *,
        principal: str | None = None,
        request_id: str | None = None,
        client_id: str | None = None,
    ) -> McpExecutionEnvelope:
        """Execute one curated surface synchronously and persist its run record.

        Args:
            surface_id: Stable surface identifier exposed by the MCP registry.
            payload: Validated model instance or raw dictionary matching the surface input.
            principal: Optional authenticated caller label.
            request_id: Optional MCP request identifier for audit correlation.
            client_id: Optional MCP client identifier for audit correlation.

        Returns:
            A structured execution envelope containing the result and follow-up resource URIs.

        Raises:
            QanuniError: If validation or SDK execution fails.
        """
        surface: McpSurfaceMetadata = self._surface_registry.get_surface(surface_id)
        validated_payload: BaseModel = self._validate_payload(surface=surface, payload=payload)
        namespace_object: object = getattr(self._client, surface.namespace_attribute)
        surface_callable = getattr(
            namespace_object,
            surface.method_name,
        )
        return self._execute_surface_call(
            surface=surface,
            validated_payload=validated_payload,
            surface_callable=surface_callable,
            principal=principal,
            request_id=request_id,
            client_id=client_id,
        )

    async def ainvoke_surface(
        self,
        surface_id: str,
        payload: BaseModel | dict[str, object],
        *,
        principal: str | None = None,
        request_id: str | None = None,
        client_id: str | None = None,
    ) -> McpExecutionEnvelope:
        """Execute one curated surface asynchronously and persist its run record.

        Args:
            surface_id: Stable surface identifier exposed by the MCP registry.
            payload: Validated model instance or raw dictionary matching the surface input.
            principal: Optional authenticated caller label.
            request_id: Optional MCP request identifier for audit correlation.
            client_id: Optional MCP client identifier for audit correlation.

        Returns:
            A structured execution envelope containing the result and follow-up resource URIs.

        Raises:
            QanuniError: If validation or SDK execution fails.
        """
        surface: McpSurfaceMetadata = self._surface_registry.get_surface(surface_id)
        validated_payload: BaseModel = self._validate_payload(surface=surface, payload=payload)
        namespace_object: object = getattr(self._client, surface.namespace_attribute)
        surface_callable: Callable[[dict[str, object]], Awaitable[BaseModel]] = getattr(
            namespace_object,
            surface.async_method_name,
        )
        try:
            result: BaseModel = await surface_callable(validated_payload.model_dump(mode="json"))
        except QanuniError as exc:
            self._log_audit_event(
                actor=principal or "unknown",
                action="surface_execution_failed",
                target=surface.surface_id,
                status="failed",
                request_id=request_id,
                client_id=client_id,
                metadata={
                    "tool_name": surface.tool_name,
                    "error_code": exc.error_code.value,
                    "input_summary": self._summarize_input_payload(validated_payload),
                },
            )
            raise
        return self._finalize_execution(
            surface=surface,
            validated_payload=validated_payload,
            result=result,
            principal=principal,
            request_id=request_id,
            client_id=client_id,
        )

    def read_reference_catalog(self) -> str:
        """Return the curated legal-reference catalog as formatted JSON text.

        Args:
            None.

        Returns:
            A JSON string describing the exposed legal-reference packets.

        Raises:
            None.
        """
        payload: list[dict[str, object]] = [
            {
                "packet_key": packet.packet_key,
                "relative_path": packet.relative_path,
                "title": packet.title,
                "surface_ids": list(packet.surface_ids),
            }
            for packet in self._surface_registry.list_reference_packets()
        ]
        return self._serialize_resource(payload)

    def read_reference_packet(self, packet_key: str) -> str:
        """Return one curated legal-reference packet as formatted JSON text.

        Args:
            packet_key: Stable packet identifier exposed by the catalog resource.

        Returns:
            A JSON string containing the validated legal-reference packet payload.

        Raises:
            QanuniValidationError: If the requested packet key is not curated for Phase 5.
        """
        packet: McpReferencePacketDescriptor = self._get_reference_packet(packet_key)
        profile = LegalReferenceLoader.load(
            packet.relative_path,
            external_catalog_dir=self._client.config.legal_reference_catalog_dir,
        )
        self._log_audit_event(
            actor="resource",
            action="reference_packet_read",
            target=packet_key,
            status="success",
            metadata={"relative_path": packet.relative_path},
        )
        return self._serialize_resource(profile.model_dump(mode="json"))

    def read_runs_index(self) -> str:
        """Return a JSON index describing recent persisted MCP runs.

        Args:
            None.

        Returns:
            A JSON string containing recent run metadata.

        Raises:
            None.
        """
        payload: list[dict[str, object]] = [
            {
                "run_id": record.run_id,
                "surface_id": record.surface_id,
                "tool_name": record.tool_name,
                "kind": record.kind.value,
                "created_at": record.created_at.isoformat(),
                "summary": record.summary,
            }
            for record in self._run_store.list_recent()
        ]
        return self._serialize_resource(payload)

    def read_run_output(self, run_id: str) -> str:
        """Return the persisted output payload for one prior MCP execution.

        Args:
            run_id: Stable execution identifier returned by one MCP tool call.

        Returns:
            A JSON string containing the stored output payload.

        Raises:
            QanuniValidationError: If the run identifier does not exist.
        """
        record: McpRunRecord = self._run_store.get(run_id)
        self._log_resource_read(action="run_output_read", target=run_id)
        return self._serialize_resource(record.output_payload)

    def read_run_state(self, run_id: str) -> str:
        """Return the stored workflow state payload for one prior execution.

        Args:
            run_id: Stable execution identifier returned by one MCP tool call.

        Returns:
            A JSON string containing the stored workflow state payload.

        Raises:
            QanuniValidationError: If the run identifier does not exist or has no workflow state.
        """
        record: McpRunRecord = self._run_store.get(run_id)
        if record.state_payload is None:
            raise QanuniValidationError(
                f"MCP run '{run_id}' does not expose a workflow state resource.",
                error_code=ErrorCode.MCP_RESOURCE_NOT_FOUND,
                details={"run_id": run_id, "resource": "state"},
            )
        self._log_resource_read(action="run_state_read", target=run_id)
        return self._serialize_resource(record.state_payload)

    def read_run_findings(self, run_id: str) -> str:
        """Return the stored findings payload for one prior execution.

        Args:
            run_id: Stable execution identifier returned by one MCP tool call.

        Returns:
            A JSON string containing the stored findings payload.

        Raises:
            QanuniValidationError: If the run identifier does not exist.
        """
        record: McpRunRecord = self._run_store.get(run_id)
        self._log_resource_read(action="run_findings_read", target=run_id)
        return self._serialize_resource(record.findings_payload)

    def read_run_artifact(self, run_id: str, artifact_name: str) -> str:
        """Return one generated artifact text emitted by a prior workflow run.

        Args:
            run_id: Stable execution identifier returned by one MCP tool call.
            artifact_name: Artifact key exposed in the execution envelope resource links.

        Returns:
            The generated artifact text.

        Raises:
            QanuniValidationError: If the run or artifact name does not exist.
        """
        record: McpRunRecord = self._run_store.get(run_id)
        artifact_text: str | None = record.artifact_payloads.get(artifact_name)
        if artifact_text is None:
            raise QanuniValidationError(
                f"Artifact '{artifact_name}' was not found for MCP run '{run_id}'.",
                error_code=ErrorCode.MCP_RESOURCE_NOT_FOUND,
                details={"run_id": run_id, "artifact_name": artifact_name},
            )
        self._log_resource_read(action="run_artifact_read", target=f"{run_id}:{artifact_name}")
        return artifact_text

    def _execute_surface_call(
        self,
        *,
        surface: McpSurfaceMetadata,
        validated_payload: BaseModel,
        surface_callable: Callable[[dict[str, object]], BaseModel],
        principal: str | None,
        request_id: str | None,
        client_id: str | None,
    ) -> McpExecutionEnvelope:
        """Execute one synchronous SDK surface and finalize the MCP envelope.

        Args:
            surface: Curated surface metadata entry being executed.
            validated_payload: Fully validated input payload for the surface.
            surface_callable: Bound synchronous namespace method to invoke.
            principal: Optional authenticated caller label.
            request_id: Optional MCP request identifier for audit correlation.
            client_id: Optional MCP client identifier for audit correlation.

        Returns:
            A structured execution envelope containing the result and follow-up resource URIs.

        Raises:
            QanuniError: If the underlying SDK surface fails.
        """
        try:
            result: BaseModel = surface_callable(validated_payload.model_dump(mode="json"))
        except QanuniError as exc:
            self._log_audit_event(
                actor=principal or "unknown",
                action="surface_execution_failed",
                target=surface.surface_id,
                status="failed",
                request_id=request_id,
                client_id=client_id,
                metadata={
                    "tool_name": surface.tool_name,
                    "error_code": exc.error_code.value,
                    "input_summary": self._summarize_input_payload(validated_payload),
                },
            )
            raise
        return self._finalize_execution(
            surface=surface,
            validated_payload=validated_payload,
            result=result,
            principal=principal,
            request_id=request_id,
            client_id=client_id,
        )

    def _validate_payload(
        self,
        *,
        surface: McpSurfaceMetadata,
        payload: BaseModel | dict[str, object],
    ) -> BaseModel:
        """Normalize and validate one payload against the surface input model.

        Args:
            surface: Curated surface metadata entry being executed.
            payload: Validated model instance or raw dictionary payload.

        Returns:
            A validated Pydantic model instance matching the surface input schema.

        Raises:
            QanuniValidationError: If the supplied payload does not satisfy the schema.
        """
        if isinstance(payload, surface.input_model):
            return payload
        if not isinstance(payload, dict):
            raise QanuniValidationError(
                "The MCP surface payload must be a dictionary or matching Pydantic model.",
                error_code=ErrorCode.VALIDATION_INPUT_TYPE,
                details={
                    "surface_id": surface.surface_id,
                    "input_model": surface.input_model.__name__,
                },
            )
        return surface.input_model.model_validate(payload)

    def _finalize_execution(
        self,
        *,
        surface: McpSurfaceMetadata,
        validated_payload: BaseModel,
        result: BaseModel,
        principal: str | None,
        request_id: str | None,
        client_id: str | None,
    ) -> McpExecutionEnvelope:
        """Persist one successful execution and build the MCP response envelope.

        Args:
            surface: Curated surface metadata entry being executed.
            validated_payload: Fully validated input payload for the surface.
            result: Structured SDK result returned by the invoked surface.
            principal: Optional authenticated caller label.
            request_id: Optional MCP request identifier for audit correlation.
            client_id: Optional MCP client identifier for audit correlation.

        Returns:
            A structured execution envelope containing the result and follow-up resource URIs.

        Raises:
            None.
        """
        run_id: str = f"mcp_run_{uuid4().hex}"
        output_payload: dict[str, object] = result.model_dump(mode="json")
        state_payload: dict[str, object] | None = self._extract_state_payload(result=result)
        findings_payload: list[dict[str, object]] = self._extract_findings_payload(
            output_payload=output_payload,
            state_payload=state_payload,
        )
        artifact_payloads: dict[str, str] = self._extract_artifact_payloads(result=result)
        legal_reference_packet_keys: list[str] = [
            path.removesuffix(".yaml").replace("/", ".")
            for path in surface.legal_reference_paths
        ]
        summary: str = self._build_summary(surface=surface, output_payload=output_payload)
        record: McpRunRecord = self._run_store.save(
            McpRunRecord(
                run_id=run_id,
                surface_id=surface.surface_id,
                tool_name=surface.tool_name,
                kind=surface.kind,
                principal=principal,
                request_id=request_id,
                client_id=client_id,
                input_payload=validated_payload.model_dump(mode="json"),
                output_payload=output_payload,
                summary=summary,
                state_payload=state_payload,
                findings_payload=findings_payload,
                artifact_payloads=artifact_payloads,
                legal_reference_packet_keys=legal_reference_packet_keys,
            )
        )
        resource_links: McpResourceLinks = self._build_resource_links(record=record)
        envelope: McpExecutionEnvelope = McpExecutionEnvelope(
            run_id=record.run_id,
            surface_id=record.surface_id,
            tool_name=record.tool_name,
            kind=record.kind,
            summary=record.summary,
            output=record.output_payload,
            resource_uris=resource_links,
        )
        self._log_audit_event(
            actor=principal or "unknown",
            action="surface_execution_succeeded",
            target=surface.surface_id,
            status="success",
            request_id=request_id,
            client_id=client_id,
            metadata={
                "tool_name": surface.tool_name,
                "kind": surface.kind.value,
                "run_id": record.run_id,
                "input_summary": self._summarize_input_payload(validated_payload),
            },
        )
        return envelope

    def _build_resource_links(self, *, record: McpRunRecord) -> McpResourceLinks:
        """Build follow-up resource URIs for one persisted execution record.

        Args:
            record: Persisted MCP run record.

        Returns:
            A structured set of MCP resource URIs related to the execution.

        Raises:
            None.
        """
        state_uri: str | None = None
        if record.state_payload is not None:
            state_uri = f"qanuni://runs/{record.run_id}/state"
        findings_uri: str | None = None
        if record.findings_payload:
            findings_uri = f"qanuni://runs/{record.run_id}/findings"
        artifact_uris: dict[str, str] = {
            artifact_name: f"qanuni://runs/{record.run_id}/artifacts/{artifact_name}"
            for artifact_name in record.artifact_payloads
        }
        legal_reference_uris: list[str] = [
            f"qanuni://references/{packet_key}"
            for packet_key in record.legal_reference_packet_keys
        ]
        return McpResourceLinks(
            output_uri=f"qanuni://runs/{record.run_id}/output",
            state_uri=state_uri,
            findings_uri=findings_uri,
            artifact_uris=artifact_uris,
            legal_reference_uris=legal_reference_uris,
        )

    def _build_summary(
        self,
        *,
        surface: McpSurfaceMetadata,
        output_payload: dict[str, object],
    ) -> str:
        """Derive a concise Arabic summary from one result payload.

        Args:
            surface: Curated surface metadata entry being executed.
            output_payload: JSON-ready result payload emitted by the SDK surface.

        Returns:
            A concise Arabic summary suitable for audit trails and execution envelopes.

        Raises:
            None.
        """
        candidate_field: str
        for candidate_field in (
            "executive_summary",
            "summary",
            "rationale",
            "legal_explanation",
            "vat_treatment",
        ):
            candidate_value: object | None = output_payload.get(candidate_field)
            if isinstance(candidate_value, str) and candidate_value.strip():
                return candidate_value.strip()
        text_field: str
        for text_field in ("demand_letter_text", "letter_text", "contract_text"):
            text_value: object | None = output_payload.get(text_field)
            if isinstance(text_value, str) and text_value.strip():
                return f"تم تنفيذ {surface.title} وإنتاج نص قانوني قابل للاستخدام."
        return f"تم تنفيذ surface '{surface.surface_id}' بنجاح."

    def _extract_state_payload(self, *, result: BaseModel) -> dict[str, object] | None:
        """Return the workflow state payload when the result exposes one.

        Args:
            result: Structured SDK result emitted by a tool or workflow.

        Returns:
            A JSON-ready workflow state payload, or `None` for atomic tools.

        Raises:
            None.
        """
        state_object: object | None = getattr(result, "state", None)
        if isinstance(state_object, BaseModel):
            return state_object.model_dump(mode="json")
        return None

    def _extract_findings_payload(
        self,
        *,
        output_payload: dict[str, object],
        state_payload: dict[str, object] | None,
    ) -> list[dict[str, object]]:
        """Return workflow or tool findings as a uniform JSON-ready list.

        Args:
            output_payload: JSON-ready result payload emitted by the surface.
            state_payload: Optional workflow state payload associated with the execution.

        Returns:
            A list of normalized finding dictionaries.

        Raises:
            None.
        """
        if state_payload is not None:
            findings_value: object | None = state_payload.get("findings")
            if isinstance(findings_value, list):
                return [
                    item for item in findings_value if isinstance(item, dict)
                ]
        findings_value = output_payload.get("findings")
        if isinstance(findings_value, list):
            return [item for item in findings_value if isinstance(item, dict)]
        return []

    def _extract_artifact_payloads(self, *, result: BaseModel) -> dict[str, str]:
        """Return generated workflow artifacts as a string map when available.

        Args:
            result: Structured SDK result emitted by a tool or workflow.

        Returns:
            A mapping of artifact names to generated text.

        Raises:
            None.
        """
        state_object: object | None = getattr(result, "state", None)
        if not isinstance(state_object, BaseModel):
            return {}
        state_payload: dict[str, object] = state_object.model_dump(mode="json")
        artifacts_value: object | None = state_payload.get("generated_artifacts")
        if not isinstance(artifacts_value, dict):
            return {}
        artifacts: dict[str, str] = {}
        artifact_name: str
        artifact_value: object
        for artifact_name, artifact_value in artifacts_value.items():
            if isinstance(artifact_value, str):
                artifacts[artifact_name] = artifact_value
        return artifacts

    def _get_reference_packet(self, packet_key: str) -> McpReferencePacketDescriptor:
        """Resolve one curated reference packet descriptor by its public key.

        Args:
            packet_key: Stable packet identifier exposed by the catalog resource.

        Returns:
            The matching packet descriptor.

        Raises:
            QanuniValidationError: If the packet key is not curated for Phase 5.
        """
        packet: McpReferencePacketDescriptor
        for packet in self._surface_registry.list_reference_packets():
            if packet.packet_key == packet_key:
                return packet
        raise QanuniValidationError(
            f"Reference packet '{packet_key}' is not exposed by the current MCP surface.",
            error_code=ErrorCode.MCP_RESOURCE_NOT_FOUND,
            details={"packet_key": packet_key},
        )

    def _serialize_resource(self, payload: object) -> str:
        """Serialize one resource payload into human-readable JSON text.

        Args:
            payload: Arbitrary JSON-serializable payload.

        Returns:
            A UTF-8 JSON string using Arabic-safe serialization settings.

        Raises:
            TypeError: If the payload is not JSON serializable.
        """
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _summarize_input_payload(self, payload: BaseModel) -> dict[str, object]:
        """Return a privacy-conscious input summary for audit logging.

        Args:
            payload: Validated Pydantic input model for the current execution.

        Returns:
            A small dictionary describing field presence without storing full documents.

        Raises:
            None.
        """
        payload_dict: dict[str, object] = payload.model_dump(mode="json")
        summary: dict[str, object] = {"present_fields": sorted(payload_dict.keys())}
        if "document_text" in payload_dict and isinstance(payload_dict["document_text"], str):
            summary["document_text_length"] = len(str(payload_dict["document_text"]))
        if "contract_text" in payload_dict and isinstance(payload_dict["contract_text"], str):
            summary["contract_text_length"] = len(str(payload_dict["contract_text"]))
        if "support_document_text" in payload_dict and isinstance(
            payload_dict["support_document_text"],
            str,
        ):
            summary["support_document_text_length"] = len(
                str(payload_dict["support_document_text"])
            )
        return summary

    def _log_resource_read(self, *, action: str, target: str) -> None:
        """Append an audit event describing one resource read.

        Args:
            action: Stable action label such as `run_state_read`.
            target: Resource target identifier such as the run ID.

        Returns:
            None.

        Raises:
            None.
        """
        self._log_audit_event(
            actor="resource",
            action=action,
            target=target,
            status="success",
        )

    def _log_audit_event(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        status: str,
        request_id: str | None = None,
        client_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Append one audit event when an audit logger is configured.

        Args:
            actor: Stable actor label associated with the event.
            action: Stable action label associated with the event.
            target: Tool, resource, or workflow target identifier.
            status: Outcome label such as `success` or `failed`.
            request_id: Optional MCP request identifier for correlation.
            client_id: Optional MCP client identifier for correlation.
            metadata: Optional structured metadata stored with the event.

        Returns:
            None.

        Raises:
            None.
        """
        if self._audit_logger is None:
            return
        self._audit_logger.log(
            McpAuditEvent(
                event_id=f"audit_{uuid4().hex}",
                actor=actor,
                action=action,
                target=target,
                status=status,
                request_id=request_id,
                client_id=client_id,
                metadata=metadata or {},
            )
        )
