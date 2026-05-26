"""Adapters that normalize current tool outputs into a shared legal ontology."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from qanuni.legal_references.models import LegalReferenceProfile
from qanuni.models.common import BaseResult
from qanuni.models.compliance import (
    DemandLetterResult,
    PDPLCheckResult,
    PrivacyPolicyResult,
    VATCheckResult,
)
from qanuni.models.contracts import (
    ContractRiskScoreResult,
    GapAnalysisResult,
    MOUResult,
    NDAResult,
)
from qanuni.models.drafting import SimplifyResult, SummaryResult, TextImprovementResult
from qanuni.models.labor import (
    EmploymentContractGenerationResult,
    EndOfServiceResult,
    ProbationCheckResult,
)
from qanuni.models.legal import (
    AmountExtractionResult,
    ClauseExtractionResult,
    DateExtractionResult,
    DisputeResolutionExtractionResult,
    DocumentTypeClassificationResult,
    ObligationExtractionResult,
    PartyExtractionResult,
    TerminationTermExtractionResult,
)
from qanuni.models.policies import HRPolicyResult, JobDescriptionResult
from qanuni.ontology.models import (
    ActionPriority,
    DocumentDateType,
    EvidenceItem,
    EvidenceKind,
    FindingCategory,
    FindingSeverity,
    LegalFinding,
    LegalReferenceRecord,
    ObligationDirection,
    PartyRecord,
    PartyRole,
    RecommendedAction,
    TimelineEvent,
    TimelineEventType,
)


def build_ontology_payload(
    *,
    tool_id: str,
    input_data: BaseModel,
    result: BaseResult,
    legal_reference_profile: LegalReferenceProfile | None,
) -> dict[str, Any]:
    """Normalize a tool run into reusable ontology fields for future agents.

    Args:
        tool_id: Stable tool identifier that produced the result.
        input_data: Parsed tool input model used for the execution.
        result: Structured public SDK result returned by the tool.
        legal_reference_profile: Optional legal-reference packet attached to the tool.

    Returns:
        A dictionary of ontology fields ready to merge into `BaseResult`.

    Raises:
        None.
    """
    evidence_items = _build_evidence_items(input_data=input_data, result=result)
    legal_references = _build_legal_reference_records(legal_reference_profile)
    findings = _build_findings(
        tool_id=tool_id,
        result=result,
        legal_reference_profile=legal_reference_profile,
        evidence_items=evidence_items,
    )
    recommended_actions = _build_recommended_actions(
        findings=findings,
        result=result,
        legal_reference_profile=legal_reference_profile,
    )
    return {
        "confidence_score": _build_confidence_score(result),
        "legal_references": legal_references,
        "evidence_items": evidence_items,
        "findings": findings,
        "recommended_actions": recommended_actions,
        "affected_parties": _build_party_records(input_data=input_data, result=result),
        "timeline_events": _build_timeline_events(input_data=input_data, result=result),
    }


def _build_confidence_score(result: BaseResult) -> float:
    """Return a pragmatic confidence baseline for the current result.

    Args:
        result: Structured result returned by the tool.

    Returns:
        A normalized confidence score between `0.0` and `1.0`.

    Raises:
        None.
    """
    if isinstance(result, DocumentTypeClassificationResult):
        if result.confidence_band == "high":
            return 0.92
        if result.confidence_band == "medium":
            return 0.8
        return 0.68
    return 0.98 if result.tokens_used is None else 0.84


def _build_legal_reference_records(
    legal_reference_profile: LegalReferenceProfile | None,
) -> list[LegalReferenceRecord]:
    """Convert a profile packet into workflow-friendly legal-reference records.

    Args:
        legal_reference_profile: Optional legal-reference packet attached to the tool.

    Returns:
        A list of normalized legal-reference records.

    Raises:
        None.
    """
    if legal_reference_profile is None:
        return []

    records: list[LegalReferenceRecord] = []
    for source in legal_reference_profile.sources:
        if source.rules:
            for rule in source.rules:
                records.append(
                    LegalReferenceRecord(
                        source_id=source.source_id,
                        source_title=source.title,
                        authority=source.authority,
                        citation=source.citation,
                        rule_id=rule.rule_id,
                        rule_priority=rule.priority.value,
                        directive=rule.directive,
                    )
                )
            continue

        records.append(
            LegalReferenceRecord(
                source_id=source.source_id,
                source_title=source.title,
                authority=source.authority,
                citation=source.citation,
            )
        )
    return records


def _build_evidence_items(*, input_data: BaseModel, result: BaseResult) -> list[EvidenceItem]:
    """Extract concise evidence snippets from inputs and structured extraction outputs.

    Args:
        input_data: Parsed tool input model used for the execution.
        result: Structured result returned by the tool.

    Returns:
        A list of normalized evidence items.

    Raises:
        None.
    """
    evidence_items: list[EvidenceItem] = []
    payload = input_data.model_dump(mode="json")
    candidate_fields: tuple[tuple[str, str], ...] = (
        ("contract_text", "نص العقد"),
        ("document_text", "نص المستند"),
        ("legal_text", "النص القانوني"),
        ("original_text", "النص الأصلي"),
        ("incident_description", "وصف الواقعة"),
        ("contract_text_snippet", "مقتطف العقد"),
    )
    for field_name, label in candidate_fields:
        raw_value = payload.get(field_name)
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"{field_name}_evidence",
                kind=EvidenceKind.INPUT_EXCERPT,
                label=label,
                excerpt=_truncate_text(raw_value),
                source_field=field_name,
            )
        )
    evidence_items.extend(_build_structured_excerpt_evidence(result))
    return evidence_items


def _build_structured_excerpt_evidence(result: BaseResult) -> list[EvidenceItem]:
    """Normalize source excerpts from atomic extraction results into evidence items.

    Args:
        result: Structured result returned by the tool.

    Returns:
        A list of evidence items derived from structured extraction outputs.

    Raises:
        None.
    """
    evidence_items: list[EvidenceItem] = []

    if isinstance(result, ClauseExtractionResult):
        for clause in result.clauses:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{clause.clause_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=clause.heading or clause.summary,
                    excerpt=_truncate_text(clause.excerpt, limit=200),
                    source_field="clauses",
                )
            )
        return evidence_items

    if isinstance(result, PartyExtractionResult):
        for party in result.parties:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{party.party_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=party.name,
                    excerpt=_truncate_text(party.source_excerpt, limit=160),
                    source_field="parties",
                )
            )
        return evidence_items

    if isinstance(result, DateExtractionResult):
        for date_record in result.dates:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{date_record.date_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=date_record.label,
                    excerpt=_truncate_text(date_record.source_excerpt, limit=160),
                    source_field="dates",
                )
            )
        return evidence_items

    if isinstance(result, ObligationExtractionResult):
        for obligation in result.obligations:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{obligation.obligation_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=obligation.action,
                    excerpt=_truncate_text(obligation.source_excerpt, limit=180),
                    source_field="obligations",
                )
            )
        return evidence_items

    if isinstance(result, AmountExtractionResult):
        for amount in result.amounts:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{amount.amount_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=amount.raw_amount,
                    excerpt=_truncate_text(amount.source_excerpt, limit=160),
                    source_field="amounts",
                    note=amount.note,
                )
            )
        return evidence_items

    if isinstance(result, TerminationTermExtractionResult):
        for term in result.termination_terms:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{term.term_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=term.trigger,
                    excerpt=_truncate_text(term.source_excerpt, limit=180),
                    source_field="termination_terms",
                    note=term.risk_note,
                )
            )
        return evidence_items

    if isinstance(result, DisputeResolutionExtractionResult):
        for resolution in result.dispute_resolution_terms:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"{resolution.resolution_id}_excerpt",
                    kind=EvidenceKind.STRUCTURED_FIELD,
                    label=resolution.resolution_type.value,
                    excerpt=_truncate_text(resolution.source_excerpt, limit=180),
                    source_field="dispute_resolution_terms",
                    note=resolution.note,
                )
            )
        return evidence_items

    return evidence_items


def _build_party_records(*, input_data: BaseModel, result: BaseResult) -> list[PartyRecord]:
    """Normalize known party names from input payloads and extraction outputs.

    Args:
        input_data: Parsed tool input model used for the execution.
        result: Structured result returned by the tool.

    Returns:
        A list of normalized party records.

    Raises:
        None.
    """
    payload = input_data.model_dump(mode="json")
    field_to_role: tuple[tuple[str, PartyRole], ...] = (
        ("company_name", PartyRole.COMPANY),
        ("client_name", PartyRole.CLIENT),
        ("contractor_name", PartyRole.CONTRACTOR),
        ("disclosing_party", PartyRole.DISCLOSING_PARTY),
        ("employer_name", PartyRole.EMPLOYER),
        ("employee_name", PartyRole.EMPLOYEE),
        ("party_a", PartyRole.PARTY_A),
        ("party_b", PartyRole.PARTY_B),
        ("receiving_party", PartyRole.RECEIVING_PARTY),
        ("recipient_name", PartyRole.RECIPIENT),
        ("sender_name", PartyRole.SENDER),
    )
    parties: list[PartyRecord] = []
    for field_name, role in field_to_role:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            parties.append(PartyRecord(name=value.strip(), role=role))

    if isinstance(result, PartyExtractionResult):
        parties.extend(
            PartyRecord(
                name=party.name,
                role=party.normalized_role,
                note=party.role_label or party.note,
            )
            for party in result.parties
        )

    if isinstance(result, ObligationExtractionResult):
        for obligation in result.obligations:
            if obligation.obligated_party:
                parties.append(
                    PartyRecord(
                        name=obligation.obligated_party,
                        role=_party_role_from_obligation(
                            direction=obligation.direction,
                            is_beneficiary=False,
                        ),
                    )
                )
            if obligation.beneficiary_party:
                parties.append(
                    PartyRecord(
                        name=obligation.beneficiary_party,
                        role=_party_role_from_obligation(
                            direction=obligation.direction,
                            is_beneficiary=True,
                        ),
                    )
                )
    return _deduplicate_party_records(parties)


def _build_timeline_events(*, input_data: BaseModel, result: BaseResult) -> list[TimelineEvent]:
    """Normalize simple deadline and duration signals from inputs and results.

    Args:
        input_data: Parsed tool input model used for the execution.
        result: Structured result returned by the tool.

    Returns:
        A list of normalized timeline events.

    Raises:
        None.
    """
    payload = input_data.model_dump(mode="json")
    events: list[TimelineEvent] = []

    deadline_days = payload.get("deadline_days")
    if isinstance(deadline_days, int):
        events.append(
            TimelineEvent(
                label="مهلة المعالجة",
                event_type=TimelineEventType.DEADLINE,
                value=f"{deadline_days} يوم",
            )
        )

    duration_months = payload.get("duration_months")
    if isinstance(duration_months, int):
        events.append(
            TimelineEvent(
                label="مدة الوثيقة",
                event_type=TimelineEventType.DURATION,
                value=f"{duration_months} شهر",
            )
        )

    confidentiality_period_years = payload.get("confidentiality_period_years")
    if isinstance(confidentiality_period_years, int):
        events.append(
            TimelineEvent(
                label="مدة السرية",
                event_type=TimelineEventType.DURATION,
                value=f"{confidentiality_period_years} سنة",
            )
        )

    if isinstance(result, SummaryResult):
        for index, key_date in enumerate(result.key_dates, start=1):
            events.append(
                TimelineEvent(
                    label=key_date.label or f"تاريخ {index}",
                    event_type=TimelineEventType.KEY_DATE,
                    value=key_date.value,
                )
            )

    if isinstance(result, DateExtractionResult):
        for date_record in result.dates:
            events.append(
                TimelineEvent(
                    label=date_record.label,
                    event_type=_timeline_event_type_from_date_type(date_record.date_type),
                    value=date_record.normalized_value or date_record.raw_value,
                    note=date_record.note,
                )
            )

    if isinstance(result, TerminationTermExtractionResult):
        for term in result.termination_terms:
            if not term.notice_period:
                continue
            events.append(
                TimelineEvent(
                    label=f"إشعار الإنهاء: {term.trigger}",
                    event_type=TimelineEventType.DEADLINE,
                    value=term.notice_period,
                    note=term.consequence,
                )
            )

    return events


def _build_findings(
    *,
    tool_id: str,
    result: BaseResult,
    legal_reference_profile: LegalReferenceProfile | None,
    evidence_items: list[EvidenceItem],
) -> list[LegalFinding]:
    """Map tool-specific outputs into normalized findings.

    Args:
        tool_id: Stable tool identifier that produced the result.
        result: Structured public SDK result returned by the tool.
        legal_reference_profile: Optional legal-reference packet attached to the tool.
        evidence_items: Evidence items already normalized from the tool input.

    Returns:
        A list of normalized legal findings.

    Raises:
        None.
    """
    evidence_ids = [item.evidence_id for item in evidence_items]
    mandatory_rule_ids = (
        list(legal_reference_profile.mandatory_rule_ids())
        if legal_reference_profile is not None
        else []
    )

    if isinstance(result, ClauseExtractionResult):
        return [
            LegalFinding(
                finding_id=clause.clause_id,
                category=FindingCategory.CLAUSE_EXTRACTION,
                severity=clause.importance,
                title=clause.heading or clause.summary,
                summary=clause.summary,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{clause.clause_id}_excerpt"],
            )
            for clause in result.clauses
        ]

    if isinstance(result, PartyExtractionResult):
        return [
            LegalFinding(
                finding_id=party.party_id,
                category=FindingCategory.PARTY_IDENTIFICATION,
                severity=FindingSeverity.LOW,
                title=f"طرف مستخرج: {party.name}",
                summary=(
                    f"تم تحديد الطرف '{party.name}' بدور "
                    f"{party.role_label or party.normalized_role.value}."
                ),
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{party.party_id}_excerpt"],
            )
            for party in result.parties
        ]

    if isinstance(result, DateExtractionResult):
        return [
            LegalFinding(
                finding_id=date_record.date_id,
                category=FindingCategory.DATE_EXTRACTION,
                severity=FindingSeverity.LOW,
                title=date_record.label,
                summary=(
                    f"تم استخراج {date_record.raw_value} كعنصر زمني من نوع "
                    f"{date_record.date_type.value}."
                ),
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{date_record.date_id}_excerpt"],
            )
            for date_record in result.dates
        ]

    if isinstance(result, ObligationExtractionResult):
        return [
            LegalFinding(
                finding_id=obligation.obligation_id,
                category=FindingCategory.OBLIGATION_EXTRACTION,
                severity=FindingSeverity.MEDIUM,
                title=obligation.action,
                summary=_build_obligation_summary(obligation),
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{obligation.obligation_id}_excerpt"],
            )
            for obligation in result.obligations
        ]

    if isinstance(result, AmountExtractionResult):
        return [
            LegalFinding(
                finding_id=amount.amount_id,
                category=FindingCategory.AMOUNT_EXTRACTION,
                severity=FindingSeverity.LOW,
                title=f"مبلغ مستخرج: {amount.raw_amount}",
                summary=_build_amount_summary(amount),
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{amount.amount_id}_excerpt"],
            )
            for amount in result.amounts
        ]

    if isinstance(result, TerminationTermExtractionResult):
        return [
            LegalFinding(
                finding_id=term.term_id,
                category=FindingCategory.TERMINATION_TERM,
                severity=FindingSeverity.MEDIUM if term.risk_note else FindingSeverity.LOW,
                title=f"شرط إنهاء: {term.trigger}",
                summary=_build_termination_term_summary(term),
                recommendation=term.risk_note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{term.term_id}_excerpt"],
            )
            for term in result.termination_terms
        ]

    if isinstance(result, DisputeResolutionExtractionResult):
        return [
            LegalFinding(
                finding_id=resolution.resolution_id,
                category=FindingCategory.DISPUTE_RESOLUTION,
                severity=FindingSeverity.MEDIUM,
                title=f"آلية نزاع: {resolution.resolution_type.value}",
                summary=_build_dispute_resolution_summary(resolution),
                recommendation=resolution.note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=[f"{resolution.resolution_id}_excerpt"],
            )
            for resolution in result.dispute_resolution_terms
        ]

    if isinstance(result, DocumentTypeClassificationResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_document_type",
                category=FindingCategory.DOCUMENT_CLASSIFICATION,
                severity=FindingSeverity.LOW,
                title=f"تصنيف المستند: {result.primary_document_type.value}",
                summary=result.rationale,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
        ]

    if isinstance(result, GapAnalysisResult):
        findings: list[LegalFinding] = []
        for index, gap in enumerate(result.gaps, start=1):
            findings.append(
                LegalFinding(
                    finding_id=f"{tool_id}_gap_{index}",
                    category=FindingCategory.COMPLIANCE_GAP,
                    severity=FindingSeverity(gap.severity),
                    title=gap.clause,
                    summary=gap.clause,
                    recommendation=gap.recommendation,
                    related_rule_ids=mandatory_rule_ids,
                    evidence_ids=evidence_ids,
                )
            )
        for index, clause_name in enumerate(result.missing_mandatory_clauses, start=1):
            findings.append(
                LegalFinding(
                    finding_id=f"{tool_id}_missing_clause_{index}",
                    category=FindingCategory.COMPLIANCE_GAP,
                    severity=FindingSeverity.HIGH,
                    title=f"بند مفقود: {clause_name}",
                    summary=f"العقد يفتقد بندًا جوهريًا يتعلق بـ {clause_name}.",
                    recommendation=f"أضف بندًا صريحًا ومنضبطًا حول {clause_name}.",
                    related_rule_ids=mandatory_rule_ids,
                    evidence_ids=evidence_ids,
                )
            )
        for index, ambiguous_clause in enumerate(result.ambiguous_clauses, start=1):
            findings.append(
                LegalFinding(
                    finding_id=f"{tool_id}_ambiguity_{index}",
                    category=FindingCategory.AMBIGUITY,
                    severity=FindingSeverity.MEDIUM,
                    title="صياغة غامضة",
                    summary=ambiguous_clause.reason,
                    recommendation=ambiguous_clause.suggested_rewrite,
                    related_rule_ids=mandatory_rule_ids,
                    evidence_ids=evidence_ids,
                )
            )
        return findings

    if isinstance(result, ContractRiskScoreResult):
        findings = [
            LegalFinding(
                finding_id=f"{tool_id}_risk_score",
                category=FindingCategory.CONTRACT_RISK,
                severity=_finding_severity_from_level(result.risk_level),
                title=f"درجة المخاطر التعاقدية: {result.risk_score:.0f}/100",
                summary=result.summary,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
        ]
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_risk_driver_{index}",
                category=FindingCategory.CONTRACT_RISK,
                severity=_finding_severity_from_level(result.risk_level),
                title="سبب رئيسي للمخاطر",
                summary=driver,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, driver in enumerate(result.primary_risk_drivers, start=1)
        )
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_missing_safeguard_{index}",
                category=FindingCategory.CONTRACT_RISK,
                severity=FindingSeverity.HIGH,
                title=f"حماية مفقودة: {safeguard}",
                summary=f"المستند يفتقد حماية تعاقدية مهمة تتعلق بـ {safeguard}.",
                recommendation=f"أضف بندًا صريحًا ومنضبطًا حول {safeguard}.",
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, safeguard in enumerate(result.missing_safeguards, start=1)
        )
        return findings

    if isinstance(result, ProbationCheckResult):
        if not result.violations:
            return [
                LegalFinding(
                    finding_id=f"{tool_id}_status",
                    category=FindingCategory.EMPLOYMENT_RIGHT,
                    severity=FindingSeverity.LOW,
                    title="فترة التجربة تبدو منضبطة",
                    summary=result.legal_explanation,
                    related_rule_ids=mandatory_rule_ids,
                    evidence_ids=evidence_ids,
                )
            ]
        return [
            LegalFinding(
                finding_id=f"{tool_id}_violation_{index}",
                category=FindingCategory.EMPLOYMENT_RIGHT,
                severity=FindingSeverity.HIGH,
                title="مخالفة في فترة التجربة",
                summary=violation,
                recommendation="راجع مدة التجربة أو مبررات التمديد الكتابي قبل اعتماد النص.",
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, violation in enumerate(result.violations, start=1)
        ]

    if isinstance(result, EndOfServiceResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_financial_entitlement",
                category=FindingCategory.FINANCIAL_ENTITLEMENT,
                severity=FindingSeverity.LOW,
                title="استحقاق مالي محسوب",
                summary=result.legal_explanation,
                recommendation=(
                    "راجع الاستحقاقات الإضافية قبل إقفال المخالصة النهائية."
                    if result.additional_entitlements
                    else None
                ),
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
        ]

    if isinstance(result, TextImprovementResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_change_{index}",
                category=FindingCategory.DRAFTING_IMPROVEMENT,
                severity=FindingSeverity.MEDIUM,
                title="تحسين صياغي",
                summary=change.reason,
                recommendation=change.improved,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, change in enumerate(result.changes, start=1)
        ]

    if isinstance(result, SummaryResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_risk_{index}",
                category=FindingCategory.DOCUMENT_SUMMARY,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة مخاطر",
                summary=risk,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, risk in enumerate(result.risk_highlights, start=1)
        ]

    if isinstance(result, SimplifyResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_reader_warning_{index}",
                category=FindingCategory.DRAFTING_IMPROVEMENT,
                severity=FindingSeverity.MEDIUM,
                title="تنبيه للقارئ",
                summary=warning,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, warning in enumerate(result.reader_warnings, start=1)
        ]

    if isinstance(result, PDPLCheckResult):
        findings = [
            LegalFinding(
                finding_id=f"{tool_id}_pdpl_status",
                category=FindingCategory.PRIVACY_OBLIGATION,
                severity=_finding_severity_from_score(result.compliance_score),
                title=f"تقييم امتثال PDPL: {result.compliance_score:.0f}/100",
                summary=result.summary,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
        ]
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_pdpl_gap_{index}",
                category=FindingCategory.PRIVACY_OBLIGATION,
                severity=FindingSeverity.HIGH,
                title="فجوة خصوصية",
                summary=gap,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, gap in enumerate(result.gaps, start=1)
        )
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_pdpl_item_{index}",
                category=FindingCategory.PRIVACY_OBLIGATION,
                severity=FindingSeverity.LOW,
                title="عنصر امتثال متحقق",
                summary=item,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, item in enumerate(result.compliant_items, start=1)
        )
        return findings

    if isinstance(result, VATCheckResult):
        findings = [
            LegalFinding(
                finding_id=f"{tool_id}_vat_status",
                category=FindingCategory.TAX_COMPLIANCE,
                severity=_finding_severity_from_score(result.compliance_score),
                title=f"تقييم امتثال ضريبة القيمة المضافة: {result.compliance_score:.0f}/100",
                summary=result.summary,
                recommendation=result.vat_treatment,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
        ]
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_vat_gap_{index}",
                category=FindingCategory.TAX_COMPLIANCE,
                severity=FindingSeverity.HIGH,
                title="فجوة ضريبية",
                summary=gap,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, gap in enumerate(result.gaps, start=1)
        )
        return findings

    if isinstance(result, PrivacyPolicyResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_privacy_note_{index}",
                category=FindingCategory.PRIVACY_OBLIGATION,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة امتثال خصوصية",
                summary=note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, note in enumerate(result.legal_notes, start=1)
        ]

    if isinstance(result, EmploymentContractGenerationResult):
        findings = [
            LegalFinding(
                finding_id=f"{tool_id}_contract_generation",
                category=FindingCategory.EMPLOYMENT_CONTRACT,
                severity=FindingSeverity.LOW,
                title="تم توليد مسودة عقد عمل",
                summary="المسودة صيغت على ضوء الحقول المدخلة والقواعد المرجعية المعتمدة.",
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
        ]
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_contract_note_{index}",
                category=FindingCategory.EMPLOYMENT_CONTRACT,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة امتثال في العقد",
                summary=note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, note in enumerate(result.compliance_notes, start=1)
        )
        return findings

    if isinstance(result, DemandLetterResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_notice_element_{index}",
                category=FindingCategory.NOTICE_ELEMENT,
                severity=FindingSeverity.LOW,
                title="عنصر إشعار مضمن",
                summary=element,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, element in enumerate(result.legal_notice_elements, start=1)
        ]

    if isinstance(result, NDAResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_nda_note_{index}",
                category=FindingCategory.PROCEDURAL_RISK,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة على اتفاقية السرية",
                summary=note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, note in enumerate(result.legal_notes, start=1)
        ]

    if isinstance(result, MOUResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_mou_note_{index}",
                category=FindingCategory.PROCEDURAL_RISK,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة على مذكرة التفاهم",
                summary=note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, note in enumerate(result.caution_notes, start=1)
        ]

    if isinstance(result, HRPolicyResult):
        return [
            LegalFinding(
                finding_id=f"{tool_id}_hr_note_{index}",
                category=FindingCategory.HR_COMPLIANCE,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة امتثال موارد بشرية",
                summary=note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, note in enumerate(result.saudi_law_compliance_notes, start=1)
        ]

    if isinstance(result, JobDescriptionResult):
        findings = [
            LegalFinding(
                finding_id=f"{tool_id}_job_flag_{index}",
                category=FindingCategory.JOB_POSTING_COMPLIANCE,
                severity=FindingSeverity.HIGH,
                title="لغة تمييزية محتملة",
                summary=flag,
                recommendation="راجع الصياغة واحذف أي وصف قد يُفهم كتقييد غير مشروع.",
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, flag in enumerate(result.discriminatory_language_flags, start=1)
        ]
        findings.extend(
            LegalFinding(
                finding_id=f"{tool_id}_job_note_{index}",
                category=FindingCategory.JOB_POSTING_COMPLIANCE,
                severity=FindingSeverity.MEDIUM,
                title="ملاحظة امتثال وظيفي",
                summary=note,
                related_rule_ids=mandatory_rule_ids,
                evidence_ids=evidence_ids,
            )
            for index, note in enumerate(result.legal_compliance_notes, start=1)
        )
        return findings

    return []


def _build_recommended_actions(
    *,
    findings: list[LegalFinding],
    result: BaseResult,
    legal_reference_profile: LegalReferenceProfile | None,
) -> list[RecommendedAction]:
    """Derive a shared action list from findings and high-signal result fields.

    Args:
        findings: Normalized findings built from the result.
        result: Structured public SDK result returned by the tool.
        legal_reference_profile: Optional legal-reference packet attached to the tool.

    Returns:
        A list of normalized recommended actions.

    Raises:
        None.
    """
    actions: list[RecommendedAction] = []
    for index, finding in enumerate(findings, start=1):
        if not finding.recommendation:
            continue
        actions.append(
            RecommendedAction(
                action_id=f"action_{index}",
                priority=_priority_for_severity(finding.severity),
                title=f"إجراء مرتبط بـ {finding.title}",
                description=finding.recommendation,
                linked_finding_ids=[finding.finding_id],
            )
        )

    if isinstance(result, DemandLetterResult):
        for note_index, note in enumerate(result.strategic_notes, start=1):
            actions.append(
                RecommendedAction(
                    action_id=f"demand_letter_strategy_{note_index}",
                    priority=ActionPriority.MEDIUM,
                    title="مراجعة استراتيجية قبل الإرسال",
                    description=note,
                    linked_finding_ids=[],
                )
            )

    if isinstance(result, EndOfServiceResult) and result.additional_entitlements:
        actions.append(
            RecommendedAction(
                action_id="end_of_service_additional_review",
                priority=ActionPriority.MEDIUM,
                title="مراجعة الاستحقاقات الإضافية",
                description="تحقق من الاستحقاقات الإضافية قبل اعتماد التسوية النهائية.",
                linked_finding_ids=[],
            )
        )

    if isinstance(result, ContractRiskScoreResult):
        for index, priority in enumerate(result.mitigation_priorities, start=1):
            actions.append(
                RecommendedAction(
                    action_id=f"contract_risk_mitigation_{index}",
                    priority=ActionPriority.HIGH,
                    title="أولوية معالجة تعاقدية",
                    description=priority,
                    linked_finding_ids=[],
                )
            )

    if isinstance(result, PDPLCheckResult):
        for index, action in enumerate(result.required_actions, start=1):
            actions.append(
                RecommendedAction(
                    action_id=f"pdpl_required_action_{index}",
                    priority=ActionPriority.HIGH,
                    title="إجراء امتثال PDPL",
                    description=action,
                    linked_finding_ids=[],
                )
            )

    if isinstance(result, VATCheckResult):
        for index, action in enumerate(result.required_actions, start=1):
            actions.append(
                RecommendedAction(
                    action_id=f"vat_required_action_{index}",
                    priority=ActionPriority.HIGH,
                    title="إجراء امتثال ضريبي",
                    description=action,
                    linked_finding_ids=[],
                )
            )

    if isinstance(result, EmploymentContractGenerationResult):
        for index, point in enumerate(result.configurable_points, start=1):
            actions.append(
                RecommendedAction(
                    action_id=f"employment_contract_configurable_{index}",
                    priority=ActionPriority.MEDIUM,
                    title="نقطة تخصيص في عقد العمل",
                    description=point,
                    linked_finding_ids=[],
                )
            )

    if legal_reference_profile is not None and not actions:
        actions.append(
            RecommendedAction(
                action_id="legal_reference_review",
                priority=ActionPriority.LOW,
                title="مراجعة الحزمة المرجعية",
                description=(
                    "راجع القواعد المرجعية المرتبطة بهذه النتيجة قبل استخدامها في "
                    "workflow أكبر أو مستند نهائي."
                ),
                linked_finding_ids=[],
            )
        )
    return actions


def _build_obligation_summary(obligation: Any) -> str:
    """Compose a readable summary for one extracted obligation record.

    Args:
        obligation: Structured obligation record returned by the extraction tool.

    Returns:
        A concise Arabic summary suitable for normalized findings.

    Raises:
        None.
    """
    obligated_party = obligation.obligated_party or "طرف غير محدد"
    beneficiary_party = obligation.beneficiary_party or "طرف غير محدد"
    parts: list[str] = [f"يلتزم {obligated_party} بـ{obligation.action}"]
    if obligation.beneficiary_party:
        parts.append(f"لصالح {beneficiary_party}")
    if obligation.condition:
        parts.append(f"عند {obligation.condition}")
    if obligation.due_trigger:
        parts.append(f"ومحفزه {obligation.due_trigger}")
    return " ".join(parts).strip()


def _build_amount_summary(amount: Any) -> str:
    """Compose a readable summary for one extracted monetary amount.

    Args:
        amount: Structured amount record returned by the extraction tool.

    Returns:
        A concise Arabic summary suitable for normalized findings.

    Raises:
        None.
    """
    value = amount.raw_amount
    if amount.currency:
        value = f"{value} ({amount.currency})"
    if amount.numeric_value is not None:
        value = f"{value} بقيمة عددية تقريبية {amount.numeric_value:.2f}"
    return f"تم استخراج مبلغ من نوع {amount.amount_type.value}: {value}."


def _build_termination_term_summary(term: Any) -> str:
    """Compose a readable summary for one extracted termination term.

    Args:
        term: Structured termination-term record returned by the extraction tool.

    Returns:
        A concise Arabic summary suitable for normalized findings.

    Raises:
        None.
    """
    parts = [f"تم رصد سبب أو آلية إنهاء تتعلق بـ {term.trigger}."]
    if term.notice_period:
        parts.append(f"مدة الإشعار المذكورة: {term.notice_period}.")
    if term.consequence:
        parts.append(f"الأثر المترتب: {term.consequence}.")
    return " ".join(parts)


def _build_dispute_resolution_summary(resolution: Any) -> str:
    """Compose a readable summary for one extracted dispute-resolution record.

    Args:
        resolution: Structured dispute-resolution record returned by the extraction tool.

    Returns:
        A concise Arabic summary suitable for normalized findings.

    Raises:
        None.
    """
    parts = [f"تم تحديد آلية فض نزاع من نوع {resolution.resolution_type.value}."]
    if resolution.venue:
        parts.append(f"المكان أو الجهة: {resolution.venue}.")
    if resolution.governing_law_reference:
        parts.append(f"مرجع القانون الحاكم: {resolution.governing_law_reference}.")
    if resolution.escalation_steps:
        parts.append(f"مراحل التدرج: {'، '.join(resolution.escalation_steps)}.")
    return " ".join(parts)


def _finding_severity_from_level(level: str) -> FindingSeverity:
    """Map textual risk levels to normalized finding severities.

    Args:
        level: Risk-level label emitted by a tool result.

    Returns:
        The normalized severity corresponding to the provided level.

    Raises:
        None.
    """
    mapping = {
        "low": FindingSeverity.LOW,
        "medium": FindingSeverity.MEDIUM,
        "high": FindingSeverity.HIGH,
        "critical": FindingSeverity.CRITICAL,
    }
    return mapping.get(level, FindingSeverity.MEDIUM)


def _finding_severity_from_score(score: float) -> FindingSeverity:
    """Map numeric compliance scores to normalized finding severities.

    Args:
        score: Numeric score between 0 and 100.

    Returns:
        The normalized severity implied by the score.

    Raises:
        None.
    """
    if score >= 85:
        return FindingSeverity.LOW
    if score >= 70:
        return FindingSeverity.MEDIUM
    if score >= 50:
        return FindingSeverity.HIGH
    return FindingSeverity.CRITICAL


def _priority_for_severity(severity: FindingSeverity) -> ActionPriority:
    """Map finding severity to an execution priority.

    Args:
        severity: Normalized severity attached to the finding.

    Returns:
        The corresponding action priority.

    Raises:
        None.
    """
    if severity in {FindingSeverity.HIGH, FindingSeverity.CRITICAL}:
        return ActionPriority.HIGH
    if severity == FindingSeverity.MEDIUM:
        return ActionPriority.MEDIUM
    return ActionPriority.LOW


def _deduplicate_party_records(parties: list[PartyRecord]) -> list[PartyRecord]:
    """Collapse duplicate normalized party records while preserving input order.

    Args:
        parties: Raw normalized party records collected from inputs and results.

    Returns:
        A de-duplicated list of party records.

    Raises:
        None.
    """
    deduplicated: list[PartyRecord] = []
    seen: set[tuple[str, str]] = set()
    for party in parties:
        key = (party.name.strip(), party.role.value)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(party)
    return deduplicated


def _party_role_from_obligation(
    *,
    direction: ObligationDirection,
    is_beneficiary: bool,
) -> PartyRole:
    """Infer a normalized party role from an extracted obligation direction.

    Args:
        direction: Directional relationship attached to the obligation.
        is_beneficiary: Whether the mapped party is the beneficiary side.

    Returns:
        A normalized party role suited for downstream workflows.

    Raises:
        None.
    """
    if direction == ObligationDirection.OWED_BY:
        return PartyRole.BENEFICIARY if is_beneficiary else PartyRole.OBLIGOR
    if direction == ObligationDirection.OWED_TO:
        return PartyRole.OBLIGOR if is_beneficiary else PartyRole.BENEFICIARY
    return PartyRole.UNKNOWN


def _timeline_event_type_from_date_type(date_type: DocumentDateType) -> TimelineEventType:
    """Map extracted legal date categories to the shared timeline event vocabulary.

    Args:
        date_type: Structured date category returned by the atomic extraction tool.

    Returns:
        The normalized timeline event type.

    Raises:
        None.
    """
    if date_type == DocumentDateType.DEADLINE:
        return TimelineEventType.DEADLINE
    if date_type in {
        DocumentDateType.EXPIRY_DATE,
        DocumentDateType.RENEWAL_DATE,
        DocumentDateType.EFFECTIVE_DATE,
        DocumentDateType.SIGNATURE_DATE,
        DocumentDateType.PAYMENT_DATE,
        DocumentDateType.DELIVERY_DATE,
        DocumentDateType.NOTICE_DATE,
    }:
        return TimelineEventType.KEY_DATE
    return TimelineEventType.KEY_DATE


def _truncate_text(text: str, *, limit: int = 280) -> str:
    """Return a compact excerpt suitable for ontology evidence fields.

    Args:
        text: Raw text to truncate into an excerpt.
        limit: Maximum character count before ellipsis is appended.

    Returns:
        A normalized excerpt suitable for audit and downstream routing.

    Raises:
        None.
    """
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."
