"""Run the full acceptance pack as one human-facing summary example."""
# ruff: noqa: E402

from __future__ import annotations

from pathlib import Path

from _bootstrap import ensure_project_root_on_path
from _common import emit_header, emit_json, parse_standard_args

ensure_project_root_on_path()

from qanuni.acceptance.runner import run_acceptance_scenarios


def main() -> None:
    """Run the full acceptance-report human example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run the shipped acceptance scenarios as one consolidated human-facing report."
    )

    emit_header("Example 10 - Full Acceptance Report")
    report = run_acceptance_scenarios(
        mode=args.mode,
        working_dir=Path(args.working_dir) if args.working_dir else None,
        observability_persist=True,
    )
    emit_json("Acceptance report", report)


if __name__ == "__main__":
    main()
