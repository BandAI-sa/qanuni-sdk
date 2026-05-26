"""Shared helpers for legal eval suites."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel

from qanuni.agent.metadata import AgentCapabilityRegistry
from qanuni.catalog import list_tools
from qanuni.client import LegalClient


def load_cases(path: Path) -> list[dict[str, Any]]:
    """Load eval cases from YAML.

    Args:
        path: File-system path to the YAML case file.

    Returns:
        Parsed list of case dictionaries.

    Raises:
        OSError: If the file cannot be read.
        yaml.YAMLError: If the YAML file is malformed.
    """
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(payload.get("cases", []))


def invoke_public_surface(
    *,
    client: LegalClient,
    surface_id: str,
    payload: dict[str, Any],
) -> Any:
    """Invoke one public tool or workflow surface by stable identifier.

    Args:
        client: Shared SDK client used for eval execution.
        surface_id: Stable tool or workflow identifier such as `contracts.gap_analysis`.
        payload: Keyword payload forwarded to the selected surface.

    Returns:
        Structured tool or workflow result.

    Raises:
        AttributeError: If the public surface does not exist.
    """
    namespace_name, method_name = surface_id.split(".", maxsplit=1)
    namespace = getattr(client, namespace_name)
    method = getattr(namespace, method_name)
    return method(**payload)


def normalize_output(output: Any) -> Any:
    """Normalize SDK outputs into JSON-like data for assertions.

    Args:
        output: Tool or workflow result object.

    Returns:
        JSON-like nested structure suitable for path-based assertions.

    Raises:
        None.
    """
    if isinstance(output, BaseModel):
        return output.model_dump(mode="json")
    return output


def resolve_path(payload: Any, dotted_path: str) -> Any:
    """Resolve a dotted path inside a JSON-like nested structure.

    Args:
        payload: JSON-like nested structure.
        dotted_path: Dotted path such as `state.steps.0.status`.

    Returns:
        The value located at the requested path.

    Raises:
        KeyError: If the path does not exist.
        IndexError: If a list index is out of range.
    """
    current = payload
    segment: str
    for segment in dotted_path.split("."):
        if isinstance(current, list):
            current = current[int(segment)]
            continue
        current = current[segment]
    return current


def assert_case_expectations(output: Any, expected: dict[str, Any]) -> None:
    """Assert all expectations declared by one eval case.

    Args:
        output: Tool or workflow result object produced by the SDK.
        expected: Structured expectation dictionary from the eval case.

    Returns:
        None.

    Raises:
        AssertionError: If any expectation is violated.
    """
    normalized = normalize_output(output)

    path_equals: dict[str, Any] = expected.get("path_equals", {})
    path: str
    for path, value in path_equals.items():
        assert resolve_path(normalized, path) == value

    path_not_empty: list[str] = list(expected.get("path_not_empty", []))
    for path in path_not_empty:
        resolved = resolve_path(normalized, path)
        assert resolved not in ("", None, [], {})

    list_length_at_least: dict[str, int] = expected.get("list_length_at_least", {})
    for path, minimum_length in list_length_at_least.items():
        resolved = resolve_path(normalized, path)
        assert isinstance(resolved, list)
        assert len(resolved) >= minimum_length

    list_contains: dict[str, list[Any]] = expected.get("list_contains", {})
    for path, expected_values in list_contains.items():
        resolved = resolve_path(normalized, path)
        assert isinstance(resolved, list)
        for expected_value in expected_values:
            assert expected_value in resolved

    number_at_least: dict[str, float] = expected.get("number_at_least", {})
    for path, minimum_value in number_at_least.items():
        resolved = resolve_path(normalized, path)
        assert resolved >= minimum_value


def catalog_tool_ids() -> set[str]:
    """Return the stable identifiers of all catalogued tools.

    Args:
        None.

    Returns:
        Set of catalogued tool identifiers.

    Raises:
        None.
    """
    return {item.tool_id for item in list_tools()}


def workflow_ids() -> set[str]:
    """Return the stable identifiers of all published workflows.

    Args:
        None.

    Returns:
        Set of workflow capability identifiers.

    Raises:
        None.
    """
    registry = AgentCapabilityRegistry()
    return {item.capability_id for item in registry.list_capabilities()}
