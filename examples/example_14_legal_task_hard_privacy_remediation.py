"""Human-test a hard legal task for the agent: PDPL remediation planning."""
# ruff: noqa: E402, E501

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_agent_plan,
    emit_agent_result_summary,
    emit_agent_state,
    emit_agent_workflow_breakdown,
    emit_document_excerpt,
    emit_environment,
    emit_legal_task_brief,
    emit_model,
    emit_observability,
    load_sample_document,
    parse_standard_args,
)

ensure_project_root_on_path()

from qanuni.agent.models import AgentScenario
from qanuni.models.common import ToolRuntimeConfig


def main() -> None:
    """Run a privacy-remediation legal task through the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run a hard legal task where the agent audits a privacy notice and proposes remediation."
    )
    context = build_context(
        title="Example 14 - Legal Task Hard Privacy Remediation",
        args=args,
    )

    request = {
        "goal": "افحص إشعار الخصوصية الحالي وحدد فجوات الامتثال ثم اقترح أولويات معالجة وسياسة علاجية أولية.",
        "scenario_hint": AgentScenario.PRIVACY_REMEDIATION,
        "documents": [
            {
                "name": "إشعار خصوصية حالي",
                "text": load_sample_document("scenario_hard_privacy_notice_ar.md"),
                "document_type": "privacy_notice",
                "role": "primary",
            },
            {
                "name": "مذكرة داخلية لمعالجة البيانات",
                "text": load_sample_document("scenario_hard_privacy_data_map_ar.md"),
                "document_type": "privacy_processing_memo",
                "role": "supporting",
            },
        ],
        "facts": {
            "processing_context": "منصة سعودية تقدم خدمات اشتراك وتطبيق جوال وتجمع بيانات المستخدمين لأغراض التشغيل والتحليلات.",
            "cross_border_transfers": True,
            "generate_policy_draft": True,
            "company_name": "شركة نبض البيانات",
            "service_type": "منصة اشتراكات رقمية",
            "data_collected": [
                "الاسم",
                "البريد الإلكتروني",
                "رقم الجوال",
                "بيانات الاستخدام",
                "بيانات الدفع الجزئية",
            ],
            "data_purposes": [
                "إنشاء الحساب",
                "تشغيل الخدمة",
                "الدعم الفني",
                "تحليل الاستخدام",
                "التسويق المصرح به",
            ],
            "third_party_sharing": True,
            "international_transfers": True,
            "dpo_contact": "privacy@nabd.example",
        },
        "shared_runtime": ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            max_output_tokens=3200,
            api_retries=0,
        ),
    }

    emit_environment(context)
    emit_legal_task_brief(
        difficulty="hard",
        legal_question="كيف يحول الـ agent إشعار خصوصية ناقصًا إلى تقييم امتثال وخطة معالجة وسياسة علاجية أولية؟",
        scenario_hint=AgentScenario.PRIVACY_REMEDIATION,
        documents=[
            {
                "name": "إشعار خصوصية حالي",
                "document_type": "privacy_notice",
                "source": "scenario_hard_privacy_notice_ar.md",
            },
            {
                "name": "مذكرة داخلية لمعالجة البيانات",
                "document_type": "privacy_processing_memo",
                "source": "scenario_hard_privacy_data_map_ar.md",
            },
        ],
        facts=request["facts"],
        what_to_watch=[
            "هل يستخرج الـ workflow الثغرات الفعلية في الإشعار بدل الاكتفاء بإعادة صياغة عامة.",
            "هل تظهر remediation priorities مرتبة بوضوح.",
            "هل يستخدم الـ agent المخرجات ليصيغ إجابة عربية عملية يمكن لصاحب المنتج العمل بها.",
        ],
        acceptance_criteria=[
            "الخطة تحتوي workflow.privacy_compliance_review.",
            "النتيجة تتضمن compliance_score أو فجوات و remediation_priorities واضحة.",
            "إذا تم توليد policy draft فيجب أن يكون ظاهرًا في payload أو generated artifacts.",
        ],
    )
    emit_document_excerpt("scenario_hard_privacy_notice_ar.md")
    emit_document_excerpt("scenario_hard_privacy_data_map_ar.md")

    plan = context.client.agent.plan(request)
    result = context.client.agent.run(request)

    emit_agent_plan(plan)
    emit_agent_result_summary(result)
    emit_model("Agent run result payload", result)
    emit_agent_workflow_breakdown(result.state)
    emit_agent_state(result.state)
    emit_observability(context)


if __name__ == "__main__":
    main()
