from __future__ import annotations

from qanuni import LegalClient
from qanuni.ontology.models import FindingCategory, PartyRole


def test_amount_extraction_feeds_evidence_and_findings(provider_factory) -> None:
    """Amount extraction should populate reusable evidence and finding records."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.extract_amounts(
        document_text="يلتزم الطرف الأول بسداد 25,000 ريال وتضاف ضريبة 3,750 ريال.",
        document_type="اتفاقية خدمات",
    )

    assert any(item.source_field == "amounts" for item in result.evidence_items)
    assert any(finding.category == FindingCategory.AMOUNT_EXTRACTION for finding in result.findings)


def test_dispute_resolution_feeds_coherent_ontology(provider_factory) -> None:
    """Dispute-resolution extraction should surface evidence and normalized findings."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.extract_dispute_resolution(
        document_text="تحال النزاعات بعد التفاوض إلى التحكيم في الرياض وفق النظام السعودي.",
        document_type="اتفاقية خدمات",
    )

    assert any(
        item.source_field == "dispute_resolution_terms" for item in result.evidence_items
    )
    assert any(
        finding.category == FindingCategory.DISPUTE_RESOLUTION for finding in result.findings
    )


def test_contract_risk_score_generates_agent_ready_actions(provider_factory) -> None:
    """Risk scoring should create actionable priorities for later workflows."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.contracts.risk_score(
        contract_text="يتم السداد لاحقًا ويجوز الإنهاء عند الحاجة.",
        contract_type="service_agreement",
    )

    assert result.recommended_actions
    assert any(
        finding.category == FindingCategory.CONTRACT_RISK for finding in result.findings
    )


def test_pdpl_and_vat_checks_use_compliance_categories(provider_factory) -> None:
    """Compliance checks should map into shared privacy and tax categories."""
    client = LegalClient(provider_factory=provider_factory)

    pdpl_result = client.compliance.pdpl_check(
        document_text="توضح السياسة أغراض المعالجة دون آلية لطلبات أصحاب البيانات.",
    )
    vat_result = client.compliance.vat_check(
        document_text="المقابل 25,000 ريال مع ضريبة دون بيان ما إذا كانت الأسعار شاملة.",
    )

    assert any(
        finding.category == FindingCategory.PRIVACY_OBLIGATION
        for finding in pdpl_result.findings
    )
    assert any(
        finding.category == FindingCategory.TAX_COMPLIANCE for finding in vat_result.findings
    )


def test_employment_contract_generation_reuses_shared_party_ontology(provider_factory) -> None:
    """Employment contract generation should feed party records for later workflows."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.labor.generate_contract(
        employer_name="شركة ألف",
        employee_name="محمد أحمد",
        job_title="محلل أعمال",
        monthly_salary=12000.0,
        contract_type="indefinite",
        work_location="الرياض",
    )

    assert {party.role for party in result.affected_parties} == {
        PartyRole.EMPLOYER,
        PartyRole.EMPLOYEE,
    }
    assert any(
        finding.category == FindingCategory.EMPLOYMENT_CONTRACT
        for finding in result.findings
    )
