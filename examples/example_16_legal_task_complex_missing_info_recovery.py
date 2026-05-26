"""Human-test a complex legal task: the agent stops, asks, then recovers."""
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
    emit_json,
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
    """Run a complex two-pass legal task through the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run a complex legal task where the agent first stops for missing information, then completes after supplementation."
    )
    context = build_context(
        title="Example 16 - Legal Task Complex Missing Information Recovery",
        args=args,
    )

    base_documents = [
        {
            "name": "عقد الخدمات",
            "text": load_sample_document("scenario_complex_claim_contract_ar.md"),
            "document_type": "service_agreement",
            "role": "primary",
        },
        {
            "name": "مذكرة دعم مختصرة",
            "text": load_sample_document("scenario_complex_claim_partial_support_ar.md"),
            "document_type": "demand_support",
            "role": "supporting",
        },
    ]
    shared_runtime = ToolRuntimeConfig(
        model="gpt-5-mini",
        verbosity="high",
        max_output_tokens=3000,
        api_retries=0,
    )
    incomplete_request = {
        "goal": "أريد مطالبة عميل متعثر لكن المعلومات ما زالت غير مكتملة وأحتاج أن يوضح لي النظام ما المطلوب.",
        "scenario_hint": AgentScenario.CONTRACT_DISPUTE_NOTICE,
        "documents": base_documents,
        "facts": {},
        "shared_runtime": shared_runtime,
    }
    completed_request = {
        "goal": "أريد مطالبة عميل متعثر بعد استكمال بيانات الواقعة.",
        "scenario_hint": AgentScenario.CONTRACT_DISPUTE_NOTICE,
        "documents": base_documents,
        "facts": {
            "sender_name": "شركة ألف للحلول التقنية",
            "recipient_name": "شركة باء للتشغيل",
            "claim_type": "مستحقات تعاقدية غير مسددة",
            "claim_amount": 125000,
            "incident_description": "تم تنفيذ الأعمال وتسليمها، ثم مضت 45 يومًا دون سداد المبلغ المستحق.",
            "deadline_days": 5,
            "threat_of_action": "سيتم اللجوء إلى الإجراءات القانونية والمطالبة بالتعويض عند عدم السداد خلال المهلة.",
        },
        "shared_runtime": shared_runtime,
    }

    emit_environment(context)
    emit_legal_task_brief(
        difficulty="complex",
        legal_question="هل يتوقف الـ agent عند نقص البيانات الجوهرية ثم يطلب الاستكمال قبل أن ينجز المطالبة؟",
        scenario_hint=AgentScenario.CONTRACT_DISPUTE_NOTICE,
        documents=[
            {
                "name": "عقد الخدمات",
                "document_type": "service_agreement",
                "source": "scenario_complex_claim_contract_ar.md",
            },
            {
                "name": "مذكرة دعم مختصرة",
                "document_type": "demand_support",
                "source": "scenario_complex_claim_partial_support_ar.md",
            },
        ],
        facts={
            "المرحلة_الأولى": "بدون facts جوهرية للمطالبة",
            "المرحلة_الثانية": completed_request["facts"],
        },
        what_to_watch=[
            "هل تتحول الخطة أو التنفيذ إلى needs_more_information بدل القفز إلى استنتاج ناقص.",
            "هل يوضح الـ agent ما البيانات الناقصة أو السؤال التالي المطلوب.",
            "هل ينجح المسار نفسه بعد تزويد البيانات دون تغيير السيناريو العام.",
        ],
        acceptance_criteria=[
            "المرور الأول لا ينهي المطالبة النهائية ويظهر next_question أو missing_inputs.",
            "المرور الثاني يكتمل ويشغل workflow.contract_review ثم workflow.pre_litigation_notice.",
            "الفارق بين المرحلتين يكون واضحًا في state وanswer_text.",
        ],
    )
    emit_document_excerpt("scenario_complex_claim_contract_ar.md")
    emit_document_excerpt("scenario_complex_claim_partial_support_ar.md")

    incomplete_plan = context.client.agent.plan(incomplete_request)
    incomplete_result = context.client.agent.run(incomplete_request)

    emit_json("Phase 1 request facts", incomplete_request["facts"])
    emit_agent_plan(incomplete_plan)
    emit_agent_result_summary(incomplete_result)
    emit_model("Incomplete agent run result payload", incomplete_result)
    emit_agent_workflow_breakdown(incomplete_result.state)
    emit_agent_state(incomplete_result.state)

    completed_plan = context.client.agent.plan(completed_request)
    completed_result = context.client.agent.run(completed_request)

    emit_json("Phase 2 facts supplied", completed_request["facts"])
    emit_agent_plan(completed_plan)
    emit_agent_result_summary(completed_result)
    emit_model("Completed agent run result payload", completed_result)
    emit_agent_workflow_breakdown(completed_result.state)
    emit_agent_state(completed_result.state)
    emit_observability(context)


if __name__ == "__main__":
    main()
