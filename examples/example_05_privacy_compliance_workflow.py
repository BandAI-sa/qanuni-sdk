"""Run the privacy-compliance workflow with policy generation enabled."""

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
    """Run the privacy-compliance workflow human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Exercise the privacy-compliance workflow with PDPL checks and policy drafting."
    )
    context = build_context(title="Example 05 - Privacy Compliance Workflow", args=args)
    document_text = load_sample_document("privacy_notice_ar.md")

    emit_environment(context)
    emit_tool_catalog(context.client, namespace="compliance")
    emit_tool_catalog(context.client, namespace="drafting")
    emit_document_excerpt("privacy_notice_ar.md")

    result = context.client.workflow.privacy_compliance_review(
        document_text=document_text,
        processing_context="تطبيق توصيل",
        cross_border_transfers=True,
        generate_policy_draft=True,
        company_name="شركة ألف",
        service_type="منصة تقنية",
        data_collected=["الاسم", "رقم الجوال", "البريد الإلكتروني"],
        data_purposes=["تقديم الخدمة", "التواصل", "الدعم الفني"],
        third_party_sharing=True,
        international_transfers=True,
    )

    emit_model("Privacy-compliance workflow result", result)
    emit_workflow_state(result.state)
    emit_observability(context)


if __name__ == "__main__":
    main()
