"""Tests for bundled and backward-compatible pricing catalogs."""

from __future__ import annotations

from pathlib import Path

from qanuni.observability.pricing import load_pricing_catalog
from qanuni.providers.base_provider import ProviderUsage


def test_bundled_default_pricing_catalog_contains_gpt_5_mini() -> None:
    """The SDK should always ship a default pricing catalog.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If the bundled catalog is missing the default model.
    """
    catalog = load_pricing_catalog(None)

    assert "gpt-5-mini" in catalog.models
    assert (
        catalog.estimate_cost(
            "gpt-5-mini",
            ProviderUsage(input_tokens=123, output_tokens=198, total_tokens=321),
        )
        is not None
    )


def test_legacy_per_1k_pricing_file_remains_supported(tmp_path: Path) -> None:
    """Legacy pricing files should be converted into per-1M pricing automatically.

    Args:
        tmp_path: Temporary directory used for the pricing fixture.

    Returns:
        None.

    Raises:
        AssertionError: If legacy pricing units are no longer accepted.
    """
    pricing_file = tmp_path / "pricing.yaml"
    pricing_file.write_text(
        """
models:
  gpt-5-mini:
    input_cost_per_1k_usd: 0.01
    output_cost_per_1k_usd: 0.02
        """.strip(),
        encoding="utf-8",
    )

    catalog = load_pricing_catalog(pricing_file)
    estimated_cost = catalog.estimate_cost(
        "gpt-5-mini",
        ProviderUsage(input_tokens=123, output_tokens=198, total_tokens=321),
    )

    assert estimated_cost == 0.00519
