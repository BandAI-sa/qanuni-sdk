"""Trigger representative failure modes and print their structured error payloads."""
# ruff: noqa: E402

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_environment,
    emit_json,
    emit_observability,
    parse_standard_args,
)

ensure_project_root_on_path()

from qanuni.core.exceptions import QanuniError


def main() -> None:
    """Run the faulty-inputs human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Show how tools, workflows, and the agent expose structured failure metadata."
    )
    context = build_context(title="Example 08 - Faulty Inputs and Error Codes", args=args)
    failures: list[dict[str, object]] = []

    emit_environment(context)

    try:
        context.client.contracts.gap_analysis(contract_type="service_agreement")
    except QanuniError as error:
        failures.append(
            {
                "surface": "contracts.gap_analysis",
                "error_type": type(error).__name__,
                "error_code": str(error.error_code),
                "message": str(error),
                "details": error.details,
            }
        )

    try:
        context.client.workflow.employment_review(
            document_text="عقد عمل مختصر",
            probation_days=120,
            termination_reason="bad_literal_value",
        )
    except QanuniError as error:
        failures.append(
            {
                "surface": "workflow.employment_review",
                "error_type": type(error).__name__,
                "error_code": str(error.error_code),
                "message": str(error),
                "details": error.details,
            }
        )

    try:
        context.client.agent.run(goal="   ")
    except QanuniError as error:
        failures.append(
            {
                "surface": "agent.run",
                "error_type": type(error).__name__,
                "error_code": str(error.error_code),
                "message": str(error),
                "details": error.details,
            }
        )

    emit_json("Captured failures", failures)
    emit_observability(context)


if __name__ == "__main__":
    main()
