from __future__ import annotations

from qanuni import LegalClient
from qanuni.ontology.models import FindingCategory, PartyRole, TimelineEventType


def test_gap_analysis_result_exposes_agent_ready_ontology(provider_factory) -> None:
    """Gap analysis should expose normalized findings, evidence, and actions.

    Args:
        provider_factory: Test fixture returning a deterministic fake provider factory.

    Returns:
        None.

    Raises:
        None.
    """
    client = LegalClient(provider_factory=provider_factory)

    result = client.contracts.gap_analysis(
        contract_text="يلتزم الطرف الثاني بالتنفيذ ويتم السداد لاحقًا.",
        contract_type="service_agreement",
    )

    assert result.confidence_score == 0.84
    assert result.evidence_items
    assert result.evidence_items[0].source_field == "contract_text"
    assert result.findings
    assert any(finding.category == FindingCategory.COMPLIANCE_GAP for finding in result.findings)
    assert result.recommended_actions


def test_demand_letter_result_exposes_parties_and_deadline(provider_factory) -> None:
    """Demand letters should expose normalized parties and timeline events.

    Args:
        provider_factory: Test fixture returning a deterministic fake provider factory.

    Returns:
        None.

    Raises:
        None.
    """
    client = LegalClient(provider_factory=provider_factory)

    result = client.compliance.demand_letter(
        sender_name="شركة ألف",
        recipient_name="شركة باء",
        claim_type="مستحقات تعاقدية",
        claim_amount=15000.0,
        incident_description="تأخر في سداد مستحقات عقد خدمات.",
        deadline_days=10,
        threat_of_action="اتخاذ الإجراءات القانونية المناسبة.",
    )

    assert {party.role for party in result.affected_parties} == {
        PartyRole.SENDER,
        PartyRole.RECIPIENT,
    }
    assert any(
        event.event_type == TimelineEventType.DEADLINE and event.value == "10 يوم"
        for event in result.timeline_events
    )
    assert any(
        finding.category == FindingCategory.NOTICE_ELEMENT
        for finding in result.findings
    )
