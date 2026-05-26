"""Benchmark models for Phase 6 hardening."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BenchmarkResult(BaseModel):
    """Represent one measured tool or workflow execution.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    case_id: str
    scope_type: Literal["tool", "workflow"]
    scope_id: str
    latency_ms: int = Field(ge=0)
    model_used: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    cache_hit: bool = False


class BenchmarkSuiteResult(BaseModel):
    """Represent an aggregated benchmark run.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    results: list[BenchmarkResult]

    @property
    def total_latency_ms(self) -> int:
        """Return the total latency across all cases.

        Args:
            None.

        Returns:
            Sum of case latencies in milliseconds.

        Raises:
            None.
        """
        return sum(item.latency_ms for item in self.results)

    @property
    def total_tokens(self) -> int:
        """Return the total token count across all cases.

        Args:
            None.

        Returns:
            Sum of token counts across all cases.

        Raises:
            None.
        """
        return sum(item.total_tokens or 0 for item in self.results)

    @property
    def total_estimated_cost_usd(self) -> float | None:
        """Return aggregated estimated cost when available.

        Args:
            None.

        Returns:
            Sum of estimated cost across all cases, or `None` when no case includes cost.

        Raises:
            None.
        """
        costs = [
            item.estimated_cost_usd
            for item in self.results
            if item.estimated_cost_usd is not None
        ]
        if not costs:
            return None
        return round(sum(costs), 8)
