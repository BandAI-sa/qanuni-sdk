"""Acceptance-pack helpers for user-facing black-box validation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from qanuni.acceptance.documents import (
    list_sample_documents,
    load_sample_document,
    sample_document_path,
)
from qanuni.acceptance.mock_provider import build_acceptance_provider

if TYPE_CHECKING:
    from qanuni import LegalClient
    from qanuni.acceptance.runner import AcceptanceArtifactPaths


def build_acceptance_client(
    *,
    mode: Literal["mocked", "live"] = "mocked",
    cache_enabled: bool = True,
    observability_persist: bool = False,
    working_dir: Path | None = None,
) -> LegalClient:
    """Build a client suited to user-acceptance experiments.

    Args:
        mode: Whether to use the offline mocked provider or the live OpenAI provider.
        cache_enabled: Whether selective caching should be enabled during the run.
        observability_persist: Whether observability events should be written to disk.
        working_dir: Optional directory for cache and observability artifacts.

    Returns:
        Configured acceptance client.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    from qanuni.acceptance.runner import build_acceptance_client as _build_acceptance_client

    return _build_acceptance_client(
        mode=mode,
        cache_enabled=cache_enabled,
        observability_persist=observability_persist,
        working_dir=working_dir,
    )


def resolve_acceptance_artifact_paths(
    working_dir: Path | None = None,
) -> AcceptanceArtifactPaths:
    """Resolve the directory layout used by the acceptance pack.

    Args:
        working_dir: Optional root directory for acceptance artifacts.

    Returns:
        Fully resolved artifact paths.

    Raises:
        OSError: If the selected working directory cannot be created.
    """
    from qanuni.acceptance.runner import (
        resolve_acceptance_artifact_paths as _resolve_acceptance_artifact_paths,
    )

    return _resolve_acceptance_artifact_paths(working_dir)


def run_acceptance_scenarios(
    *,
    mode: Literal["mocked", "live"] = "mocked",
    scenario_names: list[str] | None = None,
    working_dir: Path | None = None,
    cache_enabled: bool = True,
    observability_persist: bool = False,
) -> dict[str, Any]:
    """Run one or more acceptance scenarios and return a structured report.

    Args:
        mode: Whether to use the offline mocked provider or the live OpenAI provider.
        scenario_names: Optional subset of scenario names. Defaults to all scenarios.
        working_dir: Optional root directory for acceptance artifacts.
        cache_enabled: Whether selective caching should be enabled during the run.
        observability_persist: Whether observability events should be written to disk.

    Returns:
        Structured acceptance report with artifacts and scenario outputs.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
        ValueError: If one of the requested scenarios does not exist.
    """
    from qanuni.acceptance.runner import run_acceptance_scenarios as _run_acceptance_scenarios

    return _run_acceptance_scenarios(
        mode=mode,
        scenario_names=scenario_names,
        working_dir=working_dir,
        cache_enabled=cache_enabled,
        observability_persist=observability_persist,
    )


__all__ = [
    "build_acceptance_client",
    "build_acceptance_provider",
    "list_sample_documents",
    "load_sample_document",
    "resolve_acceptance_artifact_paths",
    "run_acceptance_scenarios",
    "sample_document_path",
]
