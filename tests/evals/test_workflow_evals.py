"""Full legal eval suite for every published workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from qanuni.client import LegalClient
from tests.evals.helpers import (
    assert_case_expectations,
    invoke_public_surface,
    load_cases,
    workflow_ids,
)

WORKFLOW_CASES = load_cases(Path(__file__).with_name("cases") / "workflow_suite.yaml")


def test_every_published_workflow_has_an_eval_case() -> None:
    """Ensure every published workflow is covered by the legal eval suite.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If any workflow lacks an eval case.
    """
    covered_ids = {case["surface_id"] for case in WORKFLOW_CASES}
    assert covered_ids == workflow_ids()


@pytest.mark.parametrize("case", WORKFLOW_CASES, ids=lambda item: str(item["case_id"]))
def test_workflow_eval_cases(case: dict[str, object], provider_factory: object) -> None:
    """Run one legal eval case against the public workflow surface.

    Args:
        case: Eval case definition loaded from YAML.
        provider_factory: Pytest fixture that creates the deterministic fake provider.

    Returns:
        None.

    Raises:
        AssertionError: If the workflow result violates the case expectations.
    """
    assert case["legal_basis"]
    client = LegalClient(provider_factory=provider_factory, asset_manifest_enforced=False)
    result = invoke_public_surface(
        client=client,
        surface_id=str(case["surface_id"]),
        payload=dict(case["payload"]),
    )
    assert_case_expectations(result, dict(case["expected"]))
