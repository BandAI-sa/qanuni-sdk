"""Human-test a medium legal task for the agent: commercial claim notice."""
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
    """Run a commercial-claim legal task through the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run a medium legal task where the agent reviews a contract and prepares a pre-litigation notice."
    )
    context = build_context(
        title="Example 12 - Legal Task Medium Commercial Claim",
        args=args,
    )

    request = {
        "goal": "أريد مراجعة العقد ثم تجهيز مسودة مطالبة نظامية بسبب تأخر السداد.",
        "scenario_hint": AgentScenario.CONTRACT_DISPUTE_NOTICE,
        "documents": [
            {
                "name": "عقد الخدمات",
                "text": load_sample_document("scenario_medium_claim_contract_ar.md"),
                "document_type": "service_agreement",
                "role": "primary",
            },
            {
                "name": "مذكرة دعم للمطالبة",
                "text": load_sample_document("scenario_medium_claim_support_ar.md"),
                "document_type": "demand_support",
                "role": "supporting",
            },
        ],
        "facts": {
            "sender_name": "شركة ألف للحلول التقنية",
            "recipient_name": "شركة باء للتشغيل",
            "claim_type": "مستحقات تعاقدية غير مسددة",
            "claim_amount": 85000,
            "incident_description": "العميل تأخر في سداد مستحقات مرحلة التسليم النهائي رغم استلام الخدمة.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد خلال المهلة المحددة.",
        },
        "shared_runtime": ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            max_output_tokens=3000,
            api_retries=0,
        ),
    }

    emit_environment(context)
    emit_legal_task_brief(
        difficulty="medium",
        legal_question="كيف يراجع الـ agent العقد ثم يحوّل المخرجات إلى خطاب مطالبة قبل النزاع؟",
        scenario_hint=AgentScenario.CONTRACT_DISPUTE_NOTICE,
        documents=[
            {
                "name": "عقد الخدمات",
                "document_type": "service_agreement",
                "source": "scenario_medium_claim_contract_ar.md",
            },
            {
                "name": "مذكرة دعم للمطالبة",
                "document_type": "demand_support",
                "source": "scenario_medium_claim_support_ar.md",
            },
        ],
        facts=request["facts"],
        what_to_watch=[
            "هل يلتزم المخطط بترتيب predecessor الصحيح: مراجعة العقد أولًا ثم المطالبة قبل النزاع.",
            "هل تظهر آثار مخرجات workflow.contract_review داخل workflow.pre_litigation_notice.",
            "هل تكون الإجابة النهائية أقرب إلى ملف عمل قانوني متكامل لا مجرد فقرة عامة.",
        ],
        acceptance_criteria=[
            "الخطة تحتوي workflow.contract_review ثم workflow.pre_litigation_notice بالترتيب.",
            "النتيجة النهائية تعرض ملخص النزاع وخطاب المطالبة أو ناتجًا يدل عليه.",
            "حالة الـ agent تحتوي completed_capabilities بعدد 2 أو ما يعادله.",
        ],
    )
    emit_document_excerpt("scenario_medium_claim_contract_ar.md")
    emit_document_excerpt("scenario_medium_claim_support_ar.md")

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
