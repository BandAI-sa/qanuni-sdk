"""Run the agent planner and executor for a contract-dispute notice scenario."""
# ruff: noqa: E402

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_agent_plan,
    emit_agent_state,
    emit_environment,
    emit_model,
    emit_observability,
    emit_sample_document_index,
    load_sample_document,
    parse_standard_args,
)

ensure_project_root_on_path()

from qanuni.agent.models import AgentScenario


def main() -> None:
    """Run the end-to-end deterministic agent human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Inspect the legal agent plan and final answer for a pre-litigation notice path."
    )
    context = build_context(title="Example 06 - Agent Contract Dispute Notice", args=args)

    emit_environment(context)
    emit_sample_document_index()

    plan = context.client.agent.plan(
        goal="أريد مراجعة العقد ثم تجهيز مسودة مطالبة قبل النزاع.",
        scenario_hint=AgentScenario.CONTRACT_DISPUTE_NOTICE,
        documents=[
            {
                "name": "عقد خدمات",
                "text": load_sample_document("service_agreement_ar.md"),
                "document_type": "service_agreement",
                "role": "primary",
            },
            {
                "name": "مستند داعم للمطالبة",
                "text": load_sample_document("prelitigation_support_ar.md"),
                "document_type": "demand_support",
                "role": "supporting",
            },
        ],
        facts={
            "sender_name": "شركة ألف",
            "recipient_name": "شركة باء",
            "claim_type": "مستحقات تعاقدية",
            "claim_amount": 85000,
            "incident_description": "تأخر في سداد مستحقات عقد خدمات تقنية.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
        },
    )
    result = context.client.agent.run(
        goal="أريد مراجعة العقد ثم تجهيز مسودة مطالبة قبل النزاع.",
        scenario_hint=AgentScenario.CONTRACT_DISPUTE_NOTICE,
        documents=[
            {
                "name": "عقد خدمات",
                "text": load_sample_document("service_agreement_ar.md"),
                "document_type": "service_agreement",
                "role": "primary",
            },
            {
                "name": "مستند داعم للمطالبة",
                "text": load_sample_document("prelitigation_support_ar.md"),
                "document_type": "demand_support",
                "role": "supporting",
            },
        ],
        facts={
            "sender_name": "شركة ألف",
            "recipient_name": "شركة باء",
            "claim_type": "مستحقات تعاقدية",
            "claim_amount": 85000,
            "incident_description": "تأخر في سداد مستحقات عقد خدمات تقنية.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
        },
    )

    emit_agent_plan(plan)
    emit_model("Agent run result", result)
    emit_agent_state(result.state)
    emit_observability(context)


if __name__ == "__main__":
    main()
