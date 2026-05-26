"""Run the deterministic labor tools with fully verbose structured output."""

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_environment,
    emit_model,
    emit_observability,
    emit_tool_catalog,
    parse_standard_args,
)

ensure_project_root_on_path()


def main() -> None:
    """Run the labor-focused human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Exercise the deterministic Saudi labor tools without any prompt-backed dependency."
    )
    context = build_context(title="Example 01 - Deterministic Labor Tools", args=args)

    emit_environment(context)
    emit_tool_catalog(context.client, namespace="labor")

    end_of_service = context.client.labor.end_of_service(
        monthly_salary=12000,
        years_of_service=7.5,
        termination_reason="resignation",
        contract_type="indefinite",
    )
    probation = context.client.labor.probation_check(
        probation_days=120,
        extension_in_writing=False,
        contract_type="indefinite",
    )

    emit_model("End-of-service result", end_of_service)
    emit_model("Probation-check result", probation)
    emit_observability(context)


if __name__ == "__main__":
    main()
