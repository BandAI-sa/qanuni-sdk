"""Runtime pricing helpers used by benchmarks and observability."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, model_validator

from qanuni.providers.base_provider import ProviderUsage


class ModelPricingRecord(BaseModel):
    """Store one model-pricing configuration entry.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    input_cost_per_1m_usd: float = Field(ge=0.0)
    output_cost_per_1m_usd: float = Field(ge=0.0)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_units(cls, value: object) -> object:
        """Convert legacy per-1K pricing keys into the new per-1M schema.

        Args:
            value: Raw model-pricing payload supplied by YAML or JSON loading.

        Returns:
            Normalized model-pricing payload.

        Raises:
            None.
        """
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if (
            "input_cost_per_1m_usd" not in normalized
            and "input_cost_per_1k_usd" in normalized
        ):
            normalized["input_cost_per_1m_usd"] = (
                float(normalized["input_cost_per_1k_usd"]) * 1000.0
            )
        if (
            "output_cost_per_1m_usd" not in normalized
            and "output_cost_per_1k_usd" in normalized
        ):
            normalized["output_cost_per_1m_usd"] = (
                float(normalized["output_cost_per_1k_usd"]) * 1000.0
            )
        return normalized


class ModelPricingCatalog(BaseModel):
    """Store pricing records used to estimate request cost.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    models: dict[str, ModelPricingRecord] = Field(default_factory=dict)

    def estimate_cost(self, model: str | None, usage: ProviderUsage) -> float | None:
        """Estimate request cost from token usage.

        Args:
            model: Effective model identifier used for the request.
            usage: Provider token-usage payload.

        Returns:
            Estimated USD cost, or `None` when pricing data is unavailable.

        Raises:
            None.
        """
        if model is None or model not in self.models:
            return None
        pricing_record = self.models[model]
        input_tokens: int = usage.input_tokens or 0
        output_tokens: int = usage.output_tokens or 0
        return round(
            (input_tokens / 1_000_000.0) * pricing_record.input_cost_per_1m_usd
            + (output_tokens / 1_000_000.0) * pricing_record.output_cost_per_1m_usd,
            8,
        )


def load_pricing_catalog(path: Path | None) -> ModelPricingCatalog:
    """Load a pricing catalog from disk when configured.

    Args:
        path: Optional file path to a JSON or YAML pricing catalog.

    Returns:
        A validated pricing catalog. Empty catalogs simply disable cost estimation.

    Raises:
        OSError: If the configured file cannot be read.
        ValueError: If the configured file has an unsupported extension.
    """
    if path is None:
        return _load_default_pricing_catalog_cached()
    return _load_pricing_catalog_cached(str(path.resolve()))


@lru_cache(maxsize=1)
def _load_default_pricing_catalog_cached() -> ModelPricingCatalog:
    """Load the bundled default pricing catalog shipped with the SDK.

    Args:
        None.

    Returns:
        The bundled validated pricing catalog.

    Raises:
        ValueError: If the bundled pricing asset is malformed.
    """
    bundled_resource = files("qanuni.observability").joinpath("default_pricing.yaml")
    raw_text = bundled_resource.read_text(encoding="utf-8")
    payload = yaml.safe_load(raw_text)
    return ModelPricingCatalog.model_validate(payload or {})


@lru_cache(maxsize=8)
def _load_pricing_catalog_cached(resolved_path: str) -> ModelPricingCatalog:
    """Load and cache one pricing catalog by resolved path.

    Args:
        resolved_path: Absolute file path to a JSON or YAML pricing catalog.

    Returns:
        A validated pricing catalog.

    Raises:
        OSError: If the configured file cannot be read.
        ValueError: If the configured file has an unsupported extension.
    """
    path = Path(resolved_path)
    raw_text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(raw_text)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(raw_text)
    else:
        raise ValueError(f"Unsupported pricing-file extension: {path.suffix}")
    return ModelPricingCatalog.model_validate(payload or {})
