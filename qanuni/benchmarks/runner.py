"""Benchmark runner for tool and workflow surfaces."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from time import perf_counter
from typing import Any

from qanuni.benchmarks.models import BenchmarkResult, BenchmarkSuiteResult
from qanuni.models.common import BaseResult
from qanuni.models.workflows import WorkflowState


class BenchmarkCase:
    """Represent one callable benchmark case.

    Args:
        case_id: Stable benchmark case identifier.
        scope_type: Whether the benchmark targets a tool or workflow.
        scope_id: Stable tool or workflow identifier.
        execute: Zero-argument callable that executes the benchmark target.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        *,
        case_id: str,
        scope_type: str,
        scope_id: str,
        execute: Callable[[], Any],
    ) -> None:
        """Initialize one benchmark case.

        Args:
            case_id: Stable benchmark case identifier.
            scope_type: Whether the benchmark targets a tool or workflow.
            scope_id: Stable tool or workflow identifier.
            execute: Zero-argument callable that executes the benchmark target.

        Returns:
            None.

        Raises:
            None.
        """
        self.case_id = case_id
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.execute = execute


def run_benchmarks(cases: Sequence[BenchmarkCase]) -> BenchmarkSuiteResult:
    """Execute benchmark cases and normalize their metrics.

    Args:
        cases: Benchmark cases to execute sequentially.

    Returns:
        Aggregated benchmark results.

    Raises:
        Any: Re-raises any exception produced by a benchmarked callable.
    """
    results: list[BenchmarkResult] = []
    case: BenchmarkCase
    for case in cases:
        started = perf_counter()
        output = case.execute()
        elapsed_ms = int((perf_counter() - started) * 1000)
        results.append(
            BenchmarkResult(
                case_id=case.case_id,
                scope_type=case.scope_type,  # type: ignore[arg-type]
                scope_id=case.scope_id,
                latency_ms=elapsed_ms,
                **extract_runtime_metrics(output),
            )
        )
    return BenchmarkSuiteResult(results=results)


def extract_runtime_metrics(output: Any) -> dict[str, Any]:
    """Extract normalized runtime metrics from a tool or workflow result.

    Args:
        output: Tool or workflow result returned by a benchmarked callable.

    Returns:
        Dictionary of normalized runtime metric fields.

    Raises:
        None.
    """
    if isinstance(output, BaseResult):
        return {
            "model_used": output.model_used,
            "input_tokens": output.input_tokens,
            "output_tokens": output.output_tokens,
            "total_tokens": output.tokens_used,
            "estimated_cost_usd": output.estimated_cost_usd,
            "cache_hit": output.cache_hit,
        }
    workflow_state = getattr(output, "state", None)
    if isinstance(workflow_state, WorkflowState):
        return {
            "model_used": workflow_state.model_used,
            "input_tokens": workflow_state.input_tokens,
            "output_tokens": workflow_state.output_tokens,
            "total_tokens": workflow_state.tokens_used,
            "estimated_cost_usd": workflow_state.estimated_cost_usd,
            "cache_hit": workflow_state.cache_hit,
        }
    return {
        "model_used": None,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "estimated_cost_usd": None,
        "cache_hit": False,
    }
