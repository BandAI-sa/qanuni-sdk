from __future__ import annotations

import json
from pathlib import Path

from qanuni import LegalClient
from qanuni.agent.models import AgentRunStatus, AgentScenario


def test_agent_plan_respects_predecessors(provider_factory) -> None:
    """The planner should chain approved capabilities in the expected order."""
    client = LegalClient(provider_factory=provider_factory)

    plan = client.agent.plan(
        goal="راجع عقد الخدمات وحدد المخاطر ثم جهز خطاب مطالبة للمستحقات المتأخرة.",
        documents=[
            {
                "text": "يلتزم الطرف الثاني بتنفيذ الأعمال ويتم السداد خلال 15 يومًا.",
                "document_type": "service_agreement",
            }
        ],
        facts={
            "sender_name": "شركة ألف",
            "recipient_name": "شركة باء",
            "claim_type": "مستحقات تعاقدية",
            "incident_description": "تأخر السداد رغم حلول الأجل.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة.",
        },
    )

    assert plan.scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE
    assert [step.capability_id for step in plan.steps] == [
        "workflow.contract_review",
        "workflow.pre_litigation_notice",
    ]
    assert plan.steps[1].recommended_predecessors == ["workflow.contract_review"]


def test_agent_completes_contract_dispute_scenario(provider_factory) -> None:
    """The agent should finish a contract dispute scenario end to end."""
    client = LegalClient(provider_factory=provider_factory)

    result = client.agent.run(
        goal="راجع العقد ثم جهز خطاب مطالبة قبل النزاع للمبالغ المتأخرة.",
        documents=[
            {
                "text": (
                    "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية، "
                    "ويلتزم الطرف الأول بسداد 25,000 ريال خلال 15 يومًا."
                ),
                "document_type": "service_agreement",
            }
        ],
        facts={
            "contract_type": "service_agreement",
            "include_redlines": True,
            "sender_name": "شركة ألف",
            "recipient_name": "شركة باء",
            "claim_type": "مستحقات تعاقدية",
            "claim_amount": 85000.0,
            "incident_description": "تأخر في سداد مستحقات عقد خدمات تقنية.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
        },
    )

    assert result.status == AgentRunStatus.COMPLETED
    assert result.scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE
    assert result.state.completed_capabilities == [
        "workflow.contract_review",
        "workflow.pre_litigation_notice",
    ]
    assert "خطاب مطالبة" in result.answer_text
    assert "workflow.pre_litigation_notice" in result.state.capability_outputs


def test_agent_completes_employment_review_scenario(provider_factory) -> None:
    """The agent should finish a complex employment review scenario end to end."""
    client = LegalClient(provider_factory=provider_factory)

    result = client.agent.run(
        goal="راجع عقد العمل وحدد المخاطر واحسب نهاية الخدمة وفحص فترة التجربة.",
        documents=[
            {
                "text": "عقد عمل يحدد الراتب والمهام والإجازات وشرط الإنهاء.",
                "document_type": "employment_contract",
            }
        ],
        facts={
            "probation_days": 120,
            "extension_in_writing": False,
            "monthly_salary": 12000.0,
            "years_of_service": 3.5,
            "termination_reason": "contract_completion",
            "contract_type": "indefinite",
        },
    )

    assert result.status == AgentRunStatus.COMPLETED
    assert result.scenario == AgentScenario.EMPLOYMENT_RIGHTS_REVIEW
    assert result.state.completed_capabilities == ["workflow.employment_review"]
    assert "المراجعة العمالية" in result.answer_text


def test_agent_completes_privacy_remediation_scenario(provider_factory) -> None:
    """The agent should finish a privacy remediation scenario end to end."""
    client = LegalClient(provider_factory=provider_factory)

    result = client.agent.run(
        goal="راجع سياسة الخصوصية الحالية وحدد الفجوات واقترح مسودة علاجية.",
        documents=[
            {
                "text": "توضح السياسة أغراض المعالجة دون آلية واضحة لطلبات أصحاب البيانات.",
                "document_type": "privacy_policy",
            }
        ],
        facts={
            "processing_context": "منصة رقمية",
            "cross_border_transfers": False,
            "generate_policy_draft": True,
            "company_name": "شركة ألف",
            "service_type": "منصة تقنية",
        },
    )

    assert result.status == AgentRunStatus.COMPLETED
    assert result.scenario == AgentScenario.PRIVACY_REMEDIATION
    assert result.state.completed_capabilities == ["workflow.privacy_compliance_review"]
    assert "أولويات المعالجة" in result.answer_text
    assert "policy_draft" in result.state.generated_artifacts


def test_agent_stops_with_follow_up_question_when_inputs_are_missing(provider_factory) -> None:
    """The agent should stop safely and ask for missing data instead of guessing."""
    client = LegalClient(provider_factory=provider_factory)

    result = client.agent.run(
        goal="راجع العقد ثم جهز خطاب مطالبة قبل النزاع.",
        documents=[
            {
                "text": "يلتزم الطرف الثاني بتنفيذ الأعمال ويتم السداد خلال 15 يومًا.",
                "document_type": "service_agreement",
            }
        ],
    )

    assert result.status == AgentRunStatus.NEEDS_MORE_INFORMATION
    assert result.state.completed_capabilities == ["workflow.contract_review"]
    assert result.next_question is not None
    assert "sender_name" in result.state.missing_inputs


def test_agent_run_writes_dated_log_file(
    provider_factory,
    tmp_path: Path,
) -> None:
    """The agent runtime should persist one dated JSONL log per run.

    Args:
        provider_factory: Test fixture returning the deterministic provider factory.
        tmp_path: Temporary directory used for agent log persistence.

    Returns:
        None.

    Raises:
        AssertionError: If the agent log file is missing or incomplete.
    """
    client = LegalClient(
        provider_factory=provider_factory,
        agent_logging_enabled=True,
        agent_log_dir=tmp_path / "logs" / "agent",
    )

    result = client.agent.run(
        goal="راجع العقد ثم جهز خطاب مطالبة قبل النزاع للمبالغ المتأخرة.",
        documents=[
            {
                "text": (
                    "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية، "
                    "ويلتزم الطرف الأول بسداد 25,000 ريال خلال 15 يومًا."
                ),
                "document_type": "service_agreement",
            }
        ],
        facts={
            "contract_type": "service_agreement",
            "sender_name": "شركة ألف",
            "recipient_name": "شركة باء",
            "claim_type": "مستحقات تعاقدية",
            "claim_amount": 85000.0,
            "incident_description": "تأخر في سداد مستحقات عقد خدمات تقنية.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
        },
    )

    assert result.run_id is not None
    assert result.log_path is not None

    log_path = Path(result.log_path)
    assert log_path.exists()
    assert log_path.parent.parent == tmp_path / "logs" / "agent"
    assert log_path.suffix == ".jsonl"

    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_names = [record["event"] for record in records]

    assert all(record["run_id"] == result.run_id for record in records)
    assert "request_received" in event_names
    assert "plan_selected" in event_names
    assert "step_started" in event_names
    assert "step_completed" in event_names
    assert "run_completed" in event_names


def test_agent_plan_writes_standalone_plan_log(
    provider_factory,
    tmp_path: Path,
) -> None:
    """Planning-only calls should still persist a dated plan log file.

    Args:
        provider_factory: Test fixture returning the deterministic provider factory.
        tmp_path: Temporary directory used for agent log persistence.

    Returns:
        None.

    Raises:
        AssertionError: If the plan log file is missing or malformed.
    """
    client = LegalClient(
        provider_factory=provider_factory,
        agent_logging_enabled=True,
        agent_log_dir=tmp_path / "logs" / "agent",
    )

    plan = client.agent.plan(
        goal="راجع عقد الخدمات وحدد المخاطر.",
        documents=[
            {
                "text": "يلتزم الطرف الثاني بالتنفيذ ويتم السداد خلال 15 يومًا.",
                "document_type": "service_agreement",
            }
        ],
    )

    assert plan.scenario == AgentScenario.CONTRACT_REVIEW_ONLY

    log_files = sorted((tmp_path / "logs" / "agent").glob("*/*.jsonl"))
    assert len(log_files) == 1

    records = [
        json.loads(line)
        for line in log_files[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records[0]["operation"] == "plan"
    assert records[0]["event"] == "request_received"
    assert records[1]["event"] == "plan_selected"
