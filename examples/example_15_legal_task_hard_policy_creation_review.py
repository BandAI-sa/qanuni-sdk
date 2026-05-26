"""Human-test a hard legal task for the agent: policy generation and review."""
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
    """Run a policy-creation legal task through the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run a hard legal task where the agent generates and reviews an HR policy."
    )
    context = build_context(
        title="Example 15 - Legal Task Hard Policy Creation Review",
        args=args,
    )

    request = {
        "goal": "أنشئ سياسة حضور وانصراف باللغة العربية لشركة تقنية سعودية ثم راجعها وحدد الملاحظات والإجراءات اللاحقة.",
        "scenario_hint": AgentScenario.POLICY_CREATION_REVIEW,
        "documents": [
            {
                "name": "مذكرة متطلبات السياسة",
                "text": load_sample_document("scenario_hard_policy_requirements_ar.md"),
                "document_type": "policy_requirements_memo",
                "role": "supporting",
            }
        ],
        "facts": {
            "policy_kind": "hr_policy",
            "policy_type": "الحضور والانصراف والعمل المرن",
            "company_name": "شركة المسار الرقمي",
            "industry": "تقنية المعلومات",
            "employee_count": 140,
            "custom_requirements": [
                "توضيح آلية البصمة أو التسجيل الإلكتروني",
                "معالجة العمل الهجين والعمل عن بعد",
                "ربط التأخير والغياب بالإجراءات التدريجية",
                "ذكر الاعتبارات الخاصة بالدوام في شهر رمضان",
            ],
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
        legal_question="هل يستطيع الـ agent توليد سياسة تشغيلية ثم مراجعتها كمسار واحد متكامل بدل مجرد توليد نص؟",
        scenario_hint=AgentScenario.POLICY_CREATION_REVIEW,
        documents=[
            {
                "name": "مذكرة متطلبات السياسة",
                "document_type": "policy_requirements_memo",
                "source": "scenario_hard_policy_requirements_ar.md",
            }
        ],
        facts=request["facts"],
        what_to_watch=[
            "هل يلتزم الـ planner بمسار policy_generation_review فقط.",
            "هل تظهر review_notes و follow_up_actions بجانب النص المولد.",
            "هل تكون الإجابة النهائية قابلة للاستخدام من صاحب الشركة مباشرة.",
        ],
        acceptance_criteria=[
            "الخطة تحتوي workflow.policy_generation_review.",
            "الناتج يحتوي generated_text إضافة إلى review_notes أو follow_up_actions.",
            "الجواب النهائي يشرح النتيجة بالعربية بدل الاكتفاء بإرجاع payload خام.",
        ],
    )
    emit_document_excerpt("scenario_hard_policy_requirements_ar.md")

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
