from __future__ import annotations

from qanuni import LegalClient
from qanuni.catalog import list_tools


def test_catalog_filters_by_namespace() -> None:
    """The central tool catalog should support namespace filtering."""
    tools = list_tools(namespace="contracts")
    assert any(tool.tool_id == "contracts.generate_nda" for tool in tools)
    assert all(tool.namespace == "contracts" for tool in tools)


def test_catalog_lists_atomic_legal_tools() -> None:
    """The catalog should expose the new atomic legal namespace."""
    tools = list_tools(namespace="legal")
    assert {tool.tool_id for tool in tools} == {
        "legal.extract_clauses",
        "legal.extract_parties",
        "legal.extract_dates",
        "legal.extract_amounts",
        "legal.extract_obligations",
        "legal.extract_termination_terms",
        "legal.extract_dispute_resolution",
        "legal.classify_document_type",
    }


def test_catalog_covers_phase_two_required_toolset() -> None:
    """The catalog should cover the full cross-namespace Phase 2 atomic roadmap."""
    tools = list_tools(tier="free")
    tool_ids = {tool.tool_id for tool in tools}

    assert {
        "drafting.extract_clauses",
        "legal.extract_parties",
        "legal.extract_dates",
        "legal.extract_amounts",
        "legal.extract_obligations",
        "legal.extract_termination_terms",
        "legal.extract_dispute_resolution",
        "legal.classify_document_type",
        "contracts.risk_score",
        "compliance.pdpl_check",
        "compliance.vat_check",
        "labor.generate_contract",
    } <= tool_ids


def test_client_exposes_catalog_listing() -> None:
    """The client should expose the implemented tool catalog ergonomically."""
    client = LegalClient(api_key="sk-test")
    tools = client.list_tools(tier="free")
    assert any(tool.tool_id == "compliance.demand_letter" for tool in tools)


def test_client_can_describe_current_tool_access() -> None:
    """Free tools should appear available in access listings without extra gating."""
    client = LegalClient(api_key="sk-test")
    access_records = client.list_tool_access(tier="free")
    assert access_records
    assert all(record.available for record in access_records)


def test_client_exposes_legal_namespace(provider_factory) -> None:
    """The client should lazily expose the atomic legal namespace."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.extract_parties(
        document_text="اتفق الطرف الأول شركة ألف مع الطرف الثاني شركة باء.",
        document_type="اتفاقية خدمات",
    )
    assert len(result.parties) == 2
