from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from qanuni import LegalClient

CASE_FILE = Path(__file__).with_name("cases") / "phase_two_atomic_tools.yaml"


def test_phase_two_atomic_eval_cases_are_complete(provider_factory) -> None:
    """Phase 2 eval cases should cover the complete required atomic-tool roadmap."""
    client = LegalClient(provider_factory=provider_factory)
    cases = yaml.safe_load(CASE_FILE.read_text(encoding="utf-8"))

    assert isinstance(cases, list)
    assert len(cases) == 13

    for case in cases:
        _run_eval_case(client=client, case=case)


def _run_eval_case(*, client: LegalClient, case: dict[str, Any]) -> None:
    """Execute one YAML-backed eval case and assert its core expectations.

    Args:
        client: SDK client configured with the deterministic fake provider.
        case: Parsed eval-case dictionary loaded from YAML.

    Returns:
        None.

    Raises:
        AssertionError: If the case is malformed or the result violates expectations.
    """
    tool_id = case["tool_id"]
    legal_basis = case.get("legal_basis", [])

    assert legal_basis
    assert all(isinstance(item, str) and item for item in legal_basis)

    result = _invoke_tool(client=client, tool_id=tool_id, payload=case["input"])
    expected = case["expected"]

    for path, expected_value in expected.get("path_equals", {}).items():
        assert _normalize_value(_get_path_value(result, path)) == expected_value

    for path, minimum_length in expected.get("list_length_at_least", {}).items():
        actual_value = _get_path_value(result, path)
        assert isinstance(actual_value, list)
        assert len(actual_value) >= minimum_length

    for path, expected_members in expected.get("list_contains", {}).items():
        actual_members = _normalize_list(_get_path_value(result, path))
        for member in expected_members:
            assert member in actual_members

    finding_categories = [
        _normalize_value(finding.category) for finding in getattr(result, "findings", [])
    ]
    for category in expected.get("finding_categories_contains", []):
        assert category in finding_categories


def _invoke_tool(*, client: LegalClient, tool_id: str, payload: dict[str, Any]) -> Any:
    """Dispatch one eval case to the correct namespace method.

    Args:
        client: SDK client configured with the deterministic fake provider.
        tool_id: Stable fully qualified tool identifier.
        payload: Input payload for the tool call.

    Returns:
        The structured tool result returned by the SDK.

    Raises:
        AssertionError: If the requested tool is not part of the Phase 2 eval suite.
    """
    dispatch_map = {
        "drafting.extract_clauses": client.drafting.extract_clauses,
        "legal.extract_clauses": client.legal.extract_clauses,
        "legal.extract_parties": client.legal.extract_parties,
        "legal.extract_dates": client.legal.extract_dates,
        "legal.extract_amounts": client.legal.extract_amounts,
        "legal.extract_obligations": client.legal.extract_obligations,
        "legal.extract_termination_terms": client.legal.extract_termination_terms,
        "legal.extract_dispute_resolution": client.legal.extract_dispute_resolution,
        "legal.classify_document_type": client.legal.classify_document_type,
        "contracts.risk_score": client.contracts.risk_score,
        "compliance.pdpl_check": client.compliance.pdpl_check,
        "compliance.vat_check": client.compliance.vat_check,
        "labor.generate_contract": client.labor.generate_contract,
    }

    if tool_id not in dispatch_map:
        raise AssertionError(f"Unsupported eval tool: {tool_id}")
    return dispatch_map[tool_id](**payload)


def _get_path_value(target: Any, path: str) -> Any:
    """Resolve a dotted attribute path from a structured SDK result.

    Args:
        target: Structured result object produced by the SDK.
        path: Dotted attribute path to resolve.

    Returns:
        The resolved value at the requested path.

    Raises:
        AttributeError: If the requested path cannot be resolved.
    """
    current = target
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current[segment]
            continue
        current = getattr(current, segment)
    return current


def _normalize_list(value: Any) -> list[Any]:
    """Normalize list-like values into scalar-friendly lists for assertions.

    Args:
        value: Raw value extracted from a structured SDK result.

    Returns:
        A list of normalized scalar values.

    Raises:
        AssertionError: If the supplied value is not iterable in the expected sense.
    """
    assert isinstance(value, Iterable) and not isinstance(value, (str, bytes))
    return [_normalize_value(item) for item in value]


def _normalize_value(value: Any) -> Any:
    """Normalize enums and rich values into assertion-friendly scalars.

    Args:
        value: Raw value extracted from a structured SDK result.

    Returns:
        A scalar or normalized list representation suited for deterministic assertions.

    Raises:
        None.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value
