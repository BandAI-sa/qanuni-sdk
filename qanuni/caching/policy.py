"""Selective caching policy for mature review-style surfaces."""

from __future__ import annotations

DEFAULT_CACHED_TOOL_IDS: frozenset[str] = frozenset(
    {
        "legal.extract_clauses",
        "legal.extract_parties",
        "legal.extract_dates",
        "legal.extract_amounts",
        "legal.extract_obligations",
        "legal.extract_termination_terms",
        "legal.extract_dispute_resolution",
        "legal.classify_document_type",
        "drafting.extract_clauses",
        "drafting.summarize",
        "drafting.simplify",
        "contracts.gap_analysis",
        "contracts.risk_score",
        "compliance.pdpl_check",
        "compliance.vat_check",
    }
)

DEFAULT_CACHED_WORKFLOW_IDS: frozenset[str] = frozenset(
    {
        "workflow.contract_review",
        "workflow.employment_review",
        "workflow.privacy_compliance_review",
    }
)


def should_cache_tool(tool_id: str) -> bool:
    """Return whether one tool is cache-eligible by policy.

    Args:
        tool_id: Stable tool identifier being evaluated.

    Returns:
        `True` when the tool is cache-eligible.

    Raises:
        None.
    """
    return tool_id in DEFAULT_CACHED_TOOL_IDS


def should_cache_workflow(workflow_id: str) -> bool:
    """Return whether one workflow is cache-eligible by policy.

    Args:
        workflow_id: Stable workflow identifier being evaluated.

    Returns:
        `True` when the workflow is cache-eligible.

    Raises:
        None.
    """
    return workflow_id in DEFAULT_CACHED_WORKFLOW_IDS
