"""Run the contract-review workflow with full state and observability output."""

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_document_excerpt,
    emit_environment,
    emit_model,
    emit_observability,
    emit_tool_catalog,
    emit_workflow_state,
    load_sample_document,
    parse_standard_args,
)

ensure_project_root_on_path()


def main() -> None:
    """Run the contract-review workflow human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Exercise the multi-step contract-review workflow and inspect every stage."
    )
    context = build_context(title="Example 03 - Contract Review Workflow", args=args)
    document_text = load_sample_document("service_agreement_ar.md")

    emit_environment(context)
    emit_tool_catalog(context.client, namespace="legal")
    emit_tool_catalog(context.client, namespace="contracts")
    emit_document_excerpt("service_agreement_ar.md")

    result = context.client.workflow.contract_review(
        document_text=document_text,
        contract_type="service_agreement",
        include_redlines=True,
    )

    emit_model("Contract-review workflow result", result)
    emit_workflow_state(result.state)
    emit_observability(context)


if __name__ == "__main__":
    main()
