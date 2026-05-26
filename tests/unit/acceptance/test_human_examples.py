"""Human-example-suite tests for the free edition."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "examples"
EXAMPLE_README = EXAMPLES_ROOT / "README.md"
EXAMPLE_SCRIPTS = sorted(EXAMPLES_ROOT.glob("example_*.py"))


def test_examples_readme_references_all_scripts() -> None:
    """Ensure the human-testing README lists every shipped example script.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If one of the shipped example scripts is undocumented.
    """
    readme_text = EXAMPLE_README.read_text(encoding="utf-8")

    assert EXAMPLE_SCRIPTS
    for script_path in EXAMPLE_SCRIPTS:
        assert script_path.name in readme_text


@pytest.mark.parametrize("script_path", EXAMPLE_SCRIPTS, ids=lambda path: path.name)
def test_examples_execute_in_mocked_mode(script_path: Path, tmp_path: Path) -> None:
    """Execute each human-testing script in mocked mode.

    Args:
        script_path: One shipped example script.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If any example script fails in mocked mode.
    """
    if (
        script_path.name == "example_09_mcp_external_smoke.py"
        and importlib.util.find_spec("mcp") is None
    ):
        pytest.skip("The optional MCP dependency is not installed in this environment.")

    working_dir = tmp_path / script_path.stem
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--mode",
            "mocked",
            "--working-dir",
            str(working_dir),
        ],
        cwd=EXAMPLES_ROOT.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, (
        f"{script_path.name} failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert working_dir.exists()
    assert result.stdout.strip()
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    assert report["mode"] == "mocked"
    assert report["cli_verbosity"] == "simple"
    assert isinstance(report["sections"], list)


def test_legal_report_profile_is_concise_and_lawyer_friendly(tmp_path: Path) -> None:
    """Verify that the legal report profile emits a concise non-technical JSON.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If the legal report profile does not match the expected
            concise shape.
    """
    script_path = EXAMPLES_ROOT / "example_12_legal_task_medium_commercial_claim.py"
    working_dir = tmp_path / "example_12_legal_profile"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--mode",
            "mocked",
            "--working-dir",
            str(working_dir),
            "--report-profile",
            "legal",
        ],
        cwd=EXAMPLES_ROOT.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, (
        f"{script_path.name} failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    report = json.loads(result.stdout)
    assert report["report_profile"] == "legal"
    assert report["audience"] == "legal_non_technical"
    assert "sections" not in report
    assert isinstance(report["matter"], dict)
    assert isinstance(report["result"], dict)
    assert isinstance(report["what_agent_did"], list)
    assert isinstance(report["key_findings"], list)
    assert isinstance(report["recommended_actions"], list)
    assert report["result"]["status"] in {"completed", "needs_input", "blocked"}
