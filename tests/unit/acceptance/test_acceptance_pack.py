"""Acceptance-pack tests for the free edition."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from qanuni.acceptance.documents import (
    list_sample_documents,
    load_sample_document,
    sample_document_path,
)
from qanuni.acceptance.mcp_smoke import run_mcp_smoke
from qanuni.acceptance.runner import build_acceptance_client, run_acceptance_scenarios


def test_packaged_sample_documents_are_available() -> None:
    """Validate that the packaged acceptance documents are discoverable.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If one of the expected packaged documents is missing.
    """
    documents = list_sample_documents()

    assert "service_agreement_ar.md" in documents
    assert "employment_contract_ar.md" in documents
    assert "privacy_notice_ar.md" in documents
    assert "prelitigation_support_ar.md" in documents

    for name in documents:
        document_path = sample_document_path(name)
        assert document_path.exists()
        assert load_sample_document(name).strip()


def test_mocked_acceptance_runner_returns_structured_report(tmp_path: Path) -> None:
    """Run the mocked acceptance scenarios and assert the report contract.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If the acceptance report loses required structure.
    """
    report = run_acceptance_scenarios(
        mode="mocked",
        scenario_names=[
            "atomic_extraction",
            "contract_review",
            "employment_review",
            "cache_observability",
            "faulty_input",
        ],
        working_dir=tmp_path,
        observability_persist=True,
    )

    assert report["mode"] == "mocked"
    assert report["artifact_paths"]["root_dir"] == str(tmp_path.resolve())

    scenarios = report["scenarios"]
    assert scenarios["atomic_extraction"]["classification"]["confidence_band"] == "high"
    assert scenarios["contract_review"]["risk_level"] in {"medium", "high", "critical"}
    assert scenarios["employment_review"]["employment_risks"]
    assert scenarios["faulty_input"]["error_code"].startswith("QANUNI_")

    cache_report = scenarios["cache_observability"]
    assert cache_report["event_count"] >= 2
    assert "miss" in cache_report["cache_statuses"]
    assert "hit" in cache_report["cache_statuses"]

    observability_log_path = Path(report["artifact_paths"]["observability_log_path"])
    assert observability_log_path.exists()
    assert observability_log_path.read_text(encoding="utf-8").strip()


def test_live_acceptance_requires_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Reject live acceptance runs when no OpenAI key is configured.

    Args:
        monkeypatch: Pytest environment monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If the live client is built without a provider key.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_acceptance_client(mode="live", working_dir=tmp_path)


def test_live_acceptance_loads_openai_api_key_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Allow live acceptance runs to resolve the key from a local `.env` file.

    Args:
        monkeypatch: Pytest environment monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If the live acceptance client ignores the `.env` file.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-from-dotenv\n", encoding="utf-8")

    captured_kwargs: dict[str, object] = {}

    class FakeLegalClient:
        """Capture construction kwargs without touching the real OpenAI client.

        Args:
            **kwargs: Arbitrary client construction kwargs.

        Returns:
            None.

        Raises:
            None.
        """

        def __init__(self, **kwargs: object) -> None:
            """Store constructor kwargs for the assertion phase.

            Args:
                **kwargs: Arbitrary client construction kwargs.

            Returns:
                None.

            Raises:
                None.
            """
            captured_kwargs.update(kwargs)

    monkeypatch.setattr("qanuni.acceptance.runner.LegalClient", FakeLegalClient)

    client = build_acceptance_client(mode="live", working_dir=tmp_path / "artifacts")

    assert isinstance(client, FakeLegalClient)
    assert os.environ["OPENAI_API_KEY"] == "sk-from-dotenv"
    assert captured_kwargs["cache_dir"] == (tmp_path / "artifacts" / ".qanuni_cache").resolve()


def test_mocked_mcp_smoke_returns_curated_surface(tmp_path: Path) -> None:
    """Exercise the mocked external MCP smoke test end to end.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If the MCP smoke result loses the curated contract.
    """
    report = run_mcp_smoke(
        mode="mocked",
        working_dir=tmp_path,
        observability_persist=True,
    )

    assert report["mode"] == "mocked"
    tool_names = report["mcp"]["tool_names"]
    assert "workflow_contract_review" in tool_names
    assert "workflow_pre_litigation_notice" in tool_names
    assert "workflow.contract_review" in report["mcp"]["contract_review_state_excerpt"]

    audit_log_path = Path(report["artifact_paths"]["mcp_audit_log_path"])
    observability_log_path = Path(report["artifact_paths"]["observability_log_path"])
    assert audit_log_path.exists()
    assert audit_log_path.read_text(encoding="utf-8").strip()
    assert observability_log_path.exists()
    assert observability_log_path.read_text(encoding="utf-8").strip()


def test_acceptance_notebook_is_present_and_references_cli() -> None:
    """Validate that the clean acceptance notebook is packaged as a stable guide.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If the notebook disappears or loses key guidance.
    """
    notebook_path = Path(__file__).resolve().parents[3] / "AcceptancePack.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    joined_sources = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
    )

    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 10
    assert "build_acceptance_client" in joined_sources
    assert "qanuni-mcp-smoke" in joined_sources
    assert "QanuniError" in joined_sources
