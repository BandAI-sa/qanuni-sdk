"""Tests for benchmark collection across tools and workflows."""

from __future__ import annotations

from pathlib import Path

from qanuni.benchmarks import BenchmarkCase, run_benchmarks
from qanuni.client import LegalClient


def test_benchmark_runner_collects_latency_tokens_and_cost(
    provider_factory: object,
    tmp_path: Path,
) -> None:
    """Benchmark representative tool and workflow paths with cost estimation.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.
        tmp_path: Temporary directory used for the pricing fixture.

    Returns:
        None.

    Raises:
        AssertionError: If benchmark metrics are incomplete.
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

    suite = run_benchmarks(
        [
            BenchmarkCase(
                case_id="tool_risk_score",
                scope_type="tool",
                scope_id="contracts.risk_score",
                execute=lambda: client.contracts.risk_score(
                    contract_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
                    contract_type="service_agreement",
                ),
            ),
            BenchmarkCase(
                case_id="workflow_contract_review",
                scope_type="workflow",
                scope_id="workflow.contract_review",
                execute=lambda: client.workflow.contract_review(
                    document_text=(
                        "يلتزم الطرف الثاني بتنفيذ الأعمال ويتم السداد لاحقًا "
                        "ويجوز إنهاء العقد عند الحاجة."
                    ),
                    contract_type="service_agreement",
                ),
            ),
        ]
    )

    assert len(suite.results) == 2
    assert suite.total_latency_ms >= 0
    assert suite.total_tokens > 0
    assert suite.total_estimated_cost_usd is not None


def test_benchmark_runner_uses_bundled_default_pricing(provider_factory: object) -> None:
    """Benchmarks should estimate cost even without a custom pricing file.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.

    Returns:
        None.

    Raises:
        AssertionError: If bundled default pricing is not applied.
    """
    client = LegalClient(
        provider_factory=provider_factory,
        asset_manifest_enforced=False,
    )

    suite = run_benchmarks(
        [
            BenchmarkCase(
                case_id="tool_risk_score_default_pricing",
                scope_type="tool",
                scope_id="contracts.risk_score",
                execute=lambda: client.contracts.risk_score(
                    contract_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
                    contract_type="service_agreement",
                ),
            )
        ]
    )

    assert len(suite.results) == 1
    assert suite.results[0].estimated_cost_usd is not None
    assert suite.total_estimated_cost_usd is not None
