"""Run the external MCP smoke test as a human-facing example."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import ensure_project_root_on_path
from _common import emit_header, emit_json

ensure_project_root_on_path()

from qanuni.acceptance.mcp_smoke import run_mcp_smoke


def main() -> None:
    """Run the MCP smoke-test human example.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: If CLI parsing fails or optional MCP dependencies are unavailable.
    """
    parser = argparse.ArgumentParser(
        description="Exercise the curated MCP surface from a human-testing example."
    )
    parser.add_argument(
        "--mode",
        choices=("mocked", "live"),
        default="mocked",
        help="Whether to use deterministic mocked outputs or real OpenAI calls.",
    )
    parser.add_argument(
        "--working-dir",
        help="Optional working directory for cache, observability, and MCP audit artifacts.",
    )
    parser.add_argument(
        "--auth-token",
        default="human-example-token",
        help="Bearer token used by the temporary MCP server during the smoke run.",
    )
    args = parser.parse_args()

    emit_header("Example 09 - MCP External Smoke")
    report = run_mcp_smoke(
        mode=args.mode,
        auth_token=args.auth_token,
        working_dir=Path(args.working_dir) if args.working_dir else None,
        observability_persist=True,
    )
    emit_json("MCP smoke report", report)


if __name__ == "__main__":
    main()
