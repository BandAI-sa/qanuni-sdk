from __future__ import annotations

import json

import pytest

from qanuni.client import LegalClient
from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.mcp.audit import QanuniMcpAuditLogger
from qanuni.mcp.runtime import QanuniMcpRuntime
from tests.conftest import FakeProvider


def test_runtime_invokes_contract_review_and_persists_resources(tmp_path) -> None:
    client = LegalClient(provider_factory=FakeProvider)
    runtime = QanuniMcpRuntime(
        client,
        audit_logger=QanuniMcpAuditLogger(tmp_path / "audit.jsonl"),
    )

    envelope = runtime.invoke_surface(
        "workflow.contract_review",
        {
            "document_text": "يتعهد الطرف الثاني بالتنفيذ ويتم السداد لاحقًا.",
            "include_redlines": True,
        },
        principal="tester",
        request_id="req-1",
        client_id="client-1",
    )

    assert envelope.surface_id == "workflow.contract_review"
    assert envelope.resource_uris.state_uri == f"qanuni://runs/{envelope.run_id}/state"
    assert envelope.resource_uris.output_uri == f"qanuni://runs/{envelope.run_id}/output"
    assert envelope.resource_uris.findings_uri == f"qanuni://runs/{envelope.run_id}/findings"

    state_payload = json.loads(runtime.read_run_state(envelope.run_id))
    assert state_payload["workflow_id"] == "workflow.contract_review"
    output_payload = json.loads(runtime.read_run_output(envelope.run_id))
    assert output_payload["risk_level"] == "high"
    findings_payload = json.loads(runtime.read_run_findings(envelope.run_id))
    assert isinstance(findings_payload, list)


def test_runtime_exposes_reference_catalog_and_packet() -> None:
    client = LegalClient(provider_factory=FakeProvider)
    runtime = QanuniMcpRuntime(client)

    catalog_payload = json.loads(runtime.read_reference_catalog())
    packet_keys = {item["packet_key"] for item in catalog_payload}

    assert "sa.legal.extraction_baseline" in packet_keys

    packet_payload = json.loads(runtime.read_reference_packet("sa.legal.extraction_baseline"))

    assert packet_payload["profile_id"] == "sa.legal.extraction_baseline"
    assert packet_payload["jurisdiction"] == "SA"


def test_runtime_raises_for_missing_run_resource() -> None:
    client = LegalClient(provider_factory=FakeProvider)
    runtime = QanuniMcpRuntime(client)

    with pytest.raises(QanuniValidationError) as error:
        runtime.read_run_output("missing-run")

    assert error.value.error_code == ErrorCode.MCP_RUN_NOT_FOUND
