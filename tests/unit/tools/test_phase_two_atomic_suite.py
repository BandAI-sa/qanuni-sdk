from __future__ import annotations

from pathlib import Path

from qanuni import LegalClient
from qanuni.ontology.models import DocumentType, FindingCategory


def test_drafting_extract_clauses_reads_document_file(
    tmp_path: Path,
    provider_factory,
) -> None:
    """Drafting clause extraction should reuse the shared document-loading flow."""
    document_file = tmp_path / "draft.txt"
    document_file.write_text(
        "يتضمن المستند بند السداد وبند الإنهاء بصورة موجزة.",
        encoding="utf-8",
    )

    client = LegalClient(provider_factory=provider_factory)
    result = client.drafting.extract_clauses(
        document_file=str(document_file),
        document_type="اتفاقية خدمات",
    )

    assert result.legal_reference_profile_id == "sa.drafting.clause_extraction_baseline"
    assert result.extracted_clause_types == ["payment", "termination"]


def test_legal_extract_amounts_returns_structured_amounts(provider_factory) -> None:
    """Amount extraction should expose normalized monetary records."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.extract_amounts(
        document_text="يلتزم الطرف الأول بسداد 25,000 ريال وتضاف ضريبة قيمة مضافة 3,750 ريال.",
        document_type="اتفاقية خدمات",
    )

    assert len(result.amounts) == 2
    assert result.amounts[0].numeric_value == 25000.0
    assert any(finding.category == FindingCategory.AMOUNT_EXTRACTION for finding in result.findings)


def test_legal_extract_termination_terms_returns_notice_period(provider_factory) -> None:
    """Termination-term extraction should surface notice periods and risks."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.extract_termination_terms(
        document_text="يجوز لأي طرف إنهاء العقد عند الإخلال الجوهري بعد إشعار مدته 30 يومًا.",
        document_type="اتفاقية خدمات",
    )

    assert result.termination_terms[0].notice_period == "30 يومًا"
    assert result.timeline_events[0].event_type.value == "deadline"


def test_legal_extract_dispute_resolution_returns_structured_path(provider_factory) -> None:
    """Dispute-resolution extraction should identify the mechanism and venue."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.extract_dispute_resolution(
        document_text="تحال النزاعات بعد التفاوض إلى التحكيم في الرياض وفق النظام السعودي.",
        document_type="اتفاقية خدمات",
    )

    assert result.dispute_resolution_terms[0].resolution_type.value == "arbitration"
    assert result.dispute_resolution_terms[0].venue == "الرياض"


def test_legal_classify_document_type_returns_primary_type(provider_factory) -> None:
    """Document classification should expose a normalized primary document type."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.legal.classify_document_type(
        document_text="يتناول هذا المستند تقديم خدمات تقنية مقابل رسوم شهرية مع آلية إنهاء.",
        document_type="مستند غير مصنف",
    )

    assert result.primary_document_type == DocumentType.SERVICE_AGREEMENT
    assert result.confidence_score == 0.92


def test_contracts_risk_score_returns_prioritized_mitigations(provider_factory) -> None:
    """Contract risk scoring should produce practical mitigation priorities."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.contracts.risk_score(
        contract_text="يتم السداد لاحقًا ويجوز الإنهاء عند الحاجة.",
        contract_type="service_agreement",
    )

    assert result.risk_level == "high"
    assert result.mitigation_priorities
    assert any(
        action.title == "أولوية معالجة تعاقدية" for action in result.recommended_actions
    )


def test_compliance_pdpl_check_returns_required_actions(provider_factory) -> None:
    """PDPL check should expose actionable remediation steps."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.compliance.pdpl_check(
        document_text="توضح السياسة أغراض المعالجة دون تفصيل مدد الاحتفاظ أو حقوق أصحاب البيانات.",
        processing_context="منصة خدمات رقمية",
    )

    assert result.required_actions
    assert any(
        finding.category == FindingCategory.PRIVACY_OBLIGATION for finding in result.findings
    )


def test_compliance_vat_check_returns_treatment_and_gaps(provider_factory) -> None:
    """VAT check should expose treatment guidance and drafting gaps."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.compliance.vat_check(
        document_text=(
            "المقابل 25,000 ريال مع إضافة ضريبة القيمة المضافة دون بيان ما إذا "
            "كانت شاملة."
        ),
        transaction_type="service_fee",
        vat_rate=15.0,
    )

    assert result.vat_treatment
    assert result.gaps
    assert any(finding.category == FindingCategory.TAX_COMPLIANCE for finding in result.findings)


def test_labor_generate_contract_returns_configurable_points(provider_factory) -> None:
    """Labor contract generation should produce a draft plus configurable checkpoints."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.labor.generate_contract(
        employer_name="شركة ألف",
        employee_name="محمد أحمد",
        job_title="محلل أعمال",
        monthly_salary=12000.0,
        contract_type="indefinite",
        work_location="الرياض",
    )

    assert result.contract_text
    assert result.configurable_points
    assert {party.name for party in result.affected_parties} == {"شركة ألف", "محمد أحمد"}
