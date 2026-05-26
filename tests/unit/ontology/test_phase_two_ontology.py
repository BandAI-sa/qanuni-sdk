from __future__ import annotations

from qanuni import LegalClient
from qanuni.ontology.models import FindingCategory, PartyRole, TimelineEventType


def test_clause_extraction_exposes_atomic_findings(provider_factory) -> None:
    """Clause extraction should surface normalized findings and evidence.

    Args:
        provider_factory: Test fixture returning a deterministic fake provider factory.

    Returns:
        None.

    Raises:
        None.
    """
    client = LegalClient(provider_factory=provider_factory)

    result = client.legal.extract_clauses(
        document_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        document_type="اتفاقية خدمات",
    )

    assert result.evidence_items
    assert any(item.source_field == "clauses" for item in result.evidence_items)
    assert any(
        finding.category == FindingCategory.CLAUSE_EXTRACTION for finding in result.findings
    )


def test_party_extraction_populates_affected_parties(provider_factory) -> None:
    """Party extraction should feed the shared affected-parties ontology field.

    Args:
        provider_factory: Test fixture returning a deterministic fake provider factory.

    Returns:
        None.

    Raises:
        None.
    """
    client = LegalClient(provider_factory=provider_factory)

    result = client.legal.extract_parties(
        document_text="اتفق الطرف الأول شركة ألف مع الطرف الثاني شركة باء.",
        document_type="اتفاقية خدمات",
    )

    assert {party.role for party in result.affected_parties} == {
        PartyRole.PARTY_A,
        PartyRole.PARTY_B,
    }


def test_date_extraction_populates_timeline_events(provider_factory) -> None:
    """Date extraction should bridge into the shared timeline-event vocabulary.

    Args:
        provider_factory: Test fixture returning a deterministic fake provider factory.

    Returns:
        None.

    Raises:
        None.
    """
    client = LegalClient(provider_factory=provider_factory)

    result = client.legal.extract_dates(
        document_text="يبدأ نفاذ الاتفاقية في 1 يناير 2026 ويتم السداد خلال 15 يومًا من الفاتورة.",
        document_type="اتفاقية خدمات",
    )

    assert any(event.event_type == TimelineEventType.KEY_DATE for event in result.timeline_events)
    assert any(event.event_type == TimelineEventType.DEADLINE for event in result.timeline_events)


def test_obligation_extraction_surfaces_parties_and_actions(provider_factory) -> None:
    """Obligation extraction should produce reusable findings and party records.

    Args:
        provider_factory: Test fixture returning a deterministic fake provider factory.

    Returns:
        None.

    Raises:
        None.
    """
    client = LegalClient(provider_factory=provider_factory)

    result = client.legal.extract_obligations(
        document_text=(
            "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية وفق الجدول الزمني المعتمد. "
            "ويلتزم الطرف الأول بسداد المقابل خلال 15 يومًا بعد استلام الفاتورة."
        ),
        document_type="اتفاقية خدمات",
    )

    assert any(
        finding.category == FindingCategory.OBLIGATION_EXTRACTION for finding in result.findings
    )
    assert {party.name for party in result.affected_parties} >= {"شركة ألف", "شركة باء"}
