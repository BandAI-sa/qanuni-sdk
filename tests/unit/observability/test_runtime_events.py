"""Tests for structured observability events."""

from __future__ import annotations

from pathlib import Path

import pytest

from qanuni.client import LegalClient
from qanuni.core.exceptions import QanuniValidationError


def test_tool_success_event_includes_usage_and_cost(
    provider_factory: object,
    tmp_path: Path,
) -> None:
    """Record usage, latency, and cost for a successful tool call.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.
        tmp_path: Temporary directory used for the pricing fixture.

    Returns:
        None.

    Raises:
        AssertionError: If the success event misses expected metrics.
    """
    pricing_file = tmp_path / "pricing.yaml"
    pricing_file.write_text(
        """
models:
  gpt-5-mini:
    input_cost_per_1m_usd: 10.0
    output_cost_per_1m_usd: 20.0
        """.strip(),
        encoding="utf-8",
    )
    client = LegalClient(
        provider_factory=provider_factory,
        asset_manifest_enforced=False,
        model_pricing_file=pricing_file,
    )
    client.observability.clear()

    result = client.contracts.risk_score(
        contract_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        contract_type="service_agreement",
    )

    events = client.observability.snapshot()
    assert result.tokens_used == 321
    assert result.input_tokens == 123
    assert result.output_tokens == 198
    assert result.estimated_cost_usd is not None
    assert events[-1].scope_type == "tool"
    assert events[-1].scope_id == "contracts.risk_score"
    assert events[-1].status == "success"
    assert events[-1].total_tokens == 321
    assert events[-1].estimated_cost_usd == result.estimated_cost_usd


def test_tool_failure_event_records_error_code(provider_factory: object) -> None:
    """Record the failure mode and stable error code for invalid input.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.

    Returns:
        None.

    Raises:
        AssertionError: If the failure event misses expected metadata.
    """
    client = LegalClient(provider_factory=provider_factory, asset_manifest_enforced=False)
    client.observability.clear()

    with pytest.raises(QanuniValidationError):
        client.contracts.gap_analysis(contract_type="service_agreement")

    events = client.observability.snapshot()
    assert events[-1].scope_id == "contracts.gap_analysis"
    assert events[-1].status == "failure"
    assert events[-1].error_code == "QANUNI_VALIDATION_DOCUMENT_SOURCE_MISSING"


def test_tool_success_event_uses_bundled_default_pricing(provider_factory: object) -> None:
    """Bundled pricing should estimate cost without any custom pricing file.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.

    Returns:
        None.

    Raises:
        AssertionError: If bundled default pricing is not applied.
    """
    client = LegalClient(provider_factory=provider_factory, asset_manifest_enforced=False)
    client.observability.clear()

    result = client.legal.extract_obligations(
        document_text="يلتزم الطرف الثاني بتنفيذ الأعمال ويلتزم الطرف الأول بالسداد خلال 15 يومًا.",
        document_type="service_agreement",
    )

    events = client.observability.snapshot()
    assert result.estimated_cost_usd is not None
    assert events[-1].estimated_cost_usd == result.estimated_cost_usd
