"""Metadata for the curated MCP surface exposed by Qanuni."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from qanuni.mcp.models import McpSurfaceKind
from qanuni.models.compliance import DemandLetterInput
from qanuni.models.contracts import ContractRiskScoreInput
from qanuni.models.legal import LegalExtractionInput
from qanuni.models.workflows import ContractReviewWorkflowInput, PreLitigationNoticeWorkflowInput


@dataclass(frozen=True, slots=True)
class McpReferencePacketDescriptor:
    """Describe one legal-reference packet exposed as an MCP resource.

    Args:
        packet_key: Stable URI-safe identifier for the packet.
        relative_path: Slash-delimited path under `qanuni/legal_references_data/`.
        title: Human-readable Arabic title for MCP clients.
        surface_ids: MCP surfaces that rely on this packet.

    Returns:
        None.

    Raises:
        None.
    """

    packet_key: str
    relative_path: str
    title: str
    surface_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class McpSurfaceMetadata:
    """Describe one curated tool or workflow exposed through the MCP server.

    Args:
        surface_id: Stable internal surface identifier.
        tool_name: Public MCP tool name exposed to clients.
        title: Human-readable Arabic title for the tool.
        description: Arabic description of the tool behavior.
        kind: Whether the surface is an atomic tool or a workflow.
        namespace_attribute: Attribute name on `LegalClient` that resolves the namespace.
        method_name: Synchronous method name exposed by that namespace.
        async_method_name: Async method name exposed by that namespace.
        input_model: Pydantic input model mirrored from the SDK surface.
        required_inputs: Core inputs the planner or caller must supply.
        produced_entities: Structured entities returned by the surface.
        risk_domain: Legal domain or risk area covered by the surface.
        cost_hint: Relative token or provider cost hint.
        latency_hint: Relative latency hint.
        recommended_predecessors: Surfaces that usually improve this surface's quality.
        legal_reference_paths: Curated legal-reference packet files used by this surface.

    Returns:
        None.

    Raises:
        None.
    """

    surface_id: str
    tool_name: str
    title: str
    description: str
    kind: McpSurfaceKind
    namespace_attribute: str
    method_name: str
    async_method_name: str
    input_model: type[BaseModel]
    required_inputs: tuple[str, ...]
    produced_entities: tuple[str, ...]
    risk_domain: str
    cost_hint: Literal["low", "medium", "high"]
    latency_hint: Literal["low", "medium", "high"]
    recommended_predecessors: tuple[str, ...]
    legal_reference_paths: tuple[str, ...]

    def meta_payload(self) -> dict[str, object]:
        """Return MCP metadata hints describing this surface.

        Args:
            None.

        Returns:
            A metadata dictionary suitable for the MCP tool registration payload.

        Raises:
            None.
        """
        return {
            "qanuni:surface_id": self.surface_id,
            "qanuni:kind": self.kind.value,
            "qanuni:required_inputs": list(self.required_inputs),
            "qanuni:produced_entities": list(self.produced_entities),
            "qanuni:risk_domain": self.risk_domain,
            "qanuni:cost_hint": self.cost_hint,
            "qanuni:latency_hint": self.latency_hint,
            "qanuni:recommended_predecessors": list(self.recommended_predecessors),
            "qanuni:legal_reference_paths": list(self.legal_reference_paths),
            "qanuni:input_model": self.input_model.__name__,
        }


class McpSurfaceRegistry:
    """Store the intentionally limited MCP surface for the current phase.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self) -> None:
        """Create the curated Phase-5 surface registry.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._surfaces: tuple[McpSurfaceMetadata, ...] = (
            McpSurfaceMetadata(
                surface_id="workflow.contract_review",
                tool_name="workflow_contract_review",
                title="مراجعة عقد مركبة",
                description=(
                    "يراجع العقد بصورة مركبة عبر التصنيف والاستخراج وتحليل الثغرات وقياس "
                    "المخاطر وتجميع التوصيات المرجعية."
                ),
                kind=McpSurfaceKind.WORKFLOW,
                namespace_attribute="workflow",
                method_name="contract_review",
                async_method_name="acontract_review",
                input_model=ContractReviewWorkflowInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=(
                    "workflow_state",
                    "risk_score",
                    "missing_mandatory_clauses",
                    "amendment_recommendations",
                ),
                risk_domain="contracts",
                cost_hint="high",
                latency_hint="high",
                recommended_predecessors=(),
                legal_reference_paths=(
                    "sa/legal/extraction_baseline.yaml",
                    "sa/contracts/review_baseline.yaml",
                    "sa/contracts/risk_scoring_baseline.yaml",
                ),
            ),
            McpSurfaceMetadata(
                surface_id="workflow.pre_litigation_notice",
                tool_name="workflow_pre_litigation_notice",
                title="خطاب مطالبة قبل النزاع",
                description=(
                    "يبني خطاب مطالبة قانونية عبر تحليل المستند الداعم واستخراج عناصره "
                    "ثم توليد الخطاب ونقاط التفاوض."
                ),
                kind=McpSurfaceKind.WORKFLOW,
                namespace_attribute="workflow",
                method_name="pre_litigation_notice",
                async_method_name="apre_litigation_notice",
                input_model=PreLitigationNoticeWorkflowInput,
                required_inputs=(
                    "sender_name",
                    "recipient_name",
                    "claim_type",
                    "incident_description",
                    "deadline_days",
                    "threat_of_action",
                ),
                produced_entities=(
                    "workflow_state",
                    "demand_letter",
                    "claim_support_summary",
                    "negotiation_points",
                ),
                risk_domain="pre_litigation",
                cost_hint="high",
                latency_hint="high",
                recommended_predecessors=("workflow.contract_review",),
                legal_reference_paths=(
                    "sa/legal/extraction_baseline.yaml",
                    "sa/compliance/legal_notice_baseline.yaml",
                ),
            ),
            McpSurfaceMetadata(
                surface_id="legal.classify_document_type",
                tool_name="legal_classify_document_type",
                title="تصنيف نوع المستند",
                description="يصنف المستند القانوني العربي لتوجيه الـ agent إلى المسار الأنسب.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="classify_document_type",
                async_method_name="aclassify_document_type",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("document_type_classification",),
                risk_domain="document_intake",
                cost_hint="low",
                latency_hint="low",
                recommended_predecessors=(),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_clauses",
                tool_name="legal_extract_clauses",
                title="استخراج البنود",
                description="يستخرج البنية البندية للمستند القانوني مع أنواع البنود ومقتطفاتها.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_clauses",
                async_method_name="aextract_clauses",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("clauses", "clause_types"),
                risk_domain="contracts",
                cost_hint="medium",
                latency_hint="medium",
                recommended_predecessors=("legal.classify_document_type",),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_parties",
                tool_name="legal_extract_parties",
                title="استخراج الأطراف",
                description="يحدد الأطراف وأدوارهم المعيارية من المستند القانوني العربي.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_parties",
                async_method_name="aextract_parties",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("parties",),
                risk_domain="document_intake",
                cost_hint="low",
                latency_hint="low",
                recommended_predecessors=("legal.classify_document_type",),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_dates",
                tool_name="legal_extract_dates",
                title="استخراج التواريخ",
                description="يستخرج التواريخ والمواعيد القانونية ويصنف معناها العملي.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_dates",
                async_method_name="aextract_dates",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("dates",),
                risk_domain="document_intake",
                cost_hint="low",
                latency_hint="low",
                recommended_predecessors=("legal.classify_document_type",),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_amounts",
                tool_name="legal_extract_amounts",
                title="استخراج المبالغ",
                description="يستخرج المبالغ المالية والقيم الضريبية من النصوص القانونية.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_amounts",
                async_method_name="aextract_amounts",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("amounts",),
                risk_domain="financial_terms",
                cost_hint="low",
                latency_hint="low",
                recommended_predecessors=("legal.classify_document_type",),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_obligations",
                tool_name="legal_extract_obligations",
                title="استخراج الالتزامات",
                description="يستخرج الالتزامات الجوهرية ويوزعها على الأطراف بصورة قابلة للتركيب.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_obligations",
                async_method_name="aextract_obligations",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("obligations",),
                risk_domain="contracts",
                cost_hint="medium",
                latency_hint="medium",
                recommended_predecessors=("legal.extract_parties", "legal.classify_document_type"),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_termination_terms",
                tool_name="legal_extract_termination_terms",
                title="استخراج أحكام الإنهاء",
                description="يستخرج أحكام الإنهاء والإشعار وآثار الخروج من العلاقة التعاقدية.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_termination_terms",
                async_method_name="aextract_termination_terms",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("termination_terms",),
                risk_domain="contracts",
                cost_hint="medium",
                latency_hint="medium",
                recommended_predecessors=("legal.extract_clauses",),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="legal.extract_dispute_resolution",
                tool_name="legal_extract_dispute_resolution",
                title="استخراج مسار فض النزاع",
                description="يستخرج آلية فض النزاع ومكانها وتدرجها الإجرائي من المستند.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="legal",
                method_name="extract_dispute_resolution",
                async_method_name="aextract_dispute_resolution",
                input_model=LegalExtractionInput,
                required_inputs=("document_text أو document_file",),
                produced_entities=("dispute_resolution_terms",),
                risk_domain="dispute_resolution",
                cost_hint="medium",
                latency_hint="medium",
                recommended_predecessors=("legal.extract_clauses",),
                legal_reference_paths=("sa/legal/extraction_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="contracts.risk_score",
                tool_name="contracts_risk_score",
                title="قياس مخاطر العقد",
                description="يحّول جودة العقد إلى درجة مخاطر عملية مع أولويات المعالجة.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="contracts",
                method_name="risk_score",
                async_method_name="arisk_score",
                input_model=ContractRiskScoreInput,
                required_inputs=("contract_text أو contract_file",),
                produced_entities=("risk_score", "mitigation_priorities"),
                risk_domain="contracts",
                cost_hint="medium",
                latency_hint="medium",
                recommended_predecessors=("legal.classify_document_type", "legal.extract_clauses"),
                legal_reference_paths=("sa/contracts/risk_scoring_baseline.yaml",),
            ),
            McpSurfaceMetadata(
                surface_id="compliance.demand_letter",
                tool_name="compliance_demand_letter",
                title="توليد خطاب مطالبة",
                description="ينشئ خطاب مطالبة قانونية عربيًا بصورة مباشرة عند اكتمال المعطيات.",
                kind=McpSurfaceKind.ATOMIC_TOOL,
                namespace_attribute="compliance",
                method_name="demand_letter",
                async_method_name="ademand_letter",
                input_model=DemandLetterInput,
                required_inputs=(
                    "sender_name",
                    "recipient_name",
                    "claim_type",
                    "incident_description",
                    "deadline_days",
                    "threat_of_action",
                ),
                produced_entities=("demand_letter", "strategic_notes"),
                risk_domain="pre_litigation",
                cost_hint="medium",
                latency_hint="medium",
                recommended_predecessors=(),
                legal_reference_paths=("sa/compliance/legal_notice_baseline.yaml",),
            ),
        )

    def list_surfaces(self) -> list[McpSurfaceMetadata]:
        """Return the curated MCP surfaces exposed in the current phase.

        Args:
            None.

        Returns:
            A list of curated surface metadata entries.

        Raises:
            None.
        """
        return list(self._surfaces)

    def get_surface(self, surface_id: str) -> McpSurfaceMetadata:
        """Return metadata for one curated MCP surface.

        Args:
            surface_id: Stable surface identifier such as `workflow.contract_review`.

        Returns:
            The matching surface metadata entry.

        Raises:
            KeyError: If the requested surface is not curated for Phase 5.
        """
        surface: McpSurfaceMetadata
        for surface in self._surfaces:
            if surface.surface_id == surface_id:
                return surface
        raise KeyError(surface_id)

    def list_reference_packets(self) -> list[McpReferencePacketDescriptor]:
        """Return deduplicated reference packets for the curated MCP surface.

        Args:
            None.

        Returns:
            A list of deduplicated reference-packet descriptors.

        Raises:
            None.
        """
        packets: dict[str, McpReferencePacketDescriptor] = {}
        surface: McpSurfaceMetadata
        for surface in self._surfaces:
            relative_path: str
            for relative_path in surface.legal_reference_paths:
                packet_key: str = relative_path.removesuffix(".yaml").replace("/", ".")
                title: str = relative_path.removesuffix(".yaml").replace("/", " -> ")
                existing: McpReferencePacketDescriptor | None = packets.get(packet_key)
                if existing is None:
                    packets[packet_key] = McpReferencePacketDescriptor(
                        packet_key=packet_key,
                        relative_path=relative_path,
                        title=title,
                        surface_ids=(surface.surface_id,),
                    )
                else:
                    packets[packet_key] = McpReferencePacketDescriptor(
                        packet_key=existing.packet_key,
                        relative_path=existing.relative_path,
                        title=existing.title,
                        surface_ids=(*existing.surface_ids, surface.surface_id),
                    )
        return list(packets.values())
