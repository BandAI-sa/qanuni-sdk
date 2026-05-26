"""Shared legal-ontology models used across tools and future agents."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FindingSeverity(StrEnum):
    """Enumerate severity levels for normalized legal findings.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(StrEnum):
    """Enumerate normalized categories for cross-tool legal findings.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    AMBIGUITY = "ambiguity"
    AMOUNT_EXTRACTION = "amount_extraction"
    CLAUSE_EXTRACTION = "clause_extraction"
    COMPLIANCE_GAP = "compliance_gap"
    CONTRACT_RISK = "contract_risk"
    DATE_EXTRACTION = "date_extraction"
    DISPUTE_RESOLUTION = "dispute_resolution"
    DOCUMENT_CLASSIFICATION = "document_classification"
    DOCUMENT_SUMMARY = "document_summary"
    DRAFTING_IMPROVEMENT = "drafting_improvement"
    EMPLOYMENT_RIGHT = "employment_right"
    EMPLOYMENT_CONTRACT = "employment_contract"
    FINANCIAL_ENTITLEMENT = "financial_entitlement"
    HR_COMPLIANCE = "hr_compliance"
    JOB_POSTING_COMPLIANCE = "job_posting_compliance"
    NOTICE_ELEMENT = "notice_element"
    OBLIGATION_EXTRACTION = "obligation_extraction"
    PARTY_IDENTIFICATION = "party_identification"
    POLICY_REQUIREMENT = "policy_requirement"
    PRIVACY_OBLIGATION = "privacy_obligation"
    PROCEDURAL_RISK = "procedural_risk"
    TAX_COMPLIANCE = "tax_compliance"
    TERMINATION_TERM = "termination_term"


class EvidenceKind(StrEnum):
    """Enumerate evidence item types attached to normalized results.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    INPUT_EXCERPT = "input_excerpt"
    LEGAL_REFERENCE = "legal_reference"
    STRUCTURED_FIELD = "structured_field"


class ActionPriority(StrEnum):
    """Enumerate priority levels for reusable recommended actions.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PartyRole(StrEnum):
    """Enumerate canonical party roles shared across legal tools.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    BENEFICIARY = "beneficiary"
    CLIENT = "client"
    COMPANY = "company"
    CONTRACTOR = "contractor"
    CUSTOMER = "customer"
    DISCLOSING_PARTY = "disclosing_party"
    EMPLOYEE = "employee"
    EMPLOYER = "employer"
    LICENSEE = "licensee"
    LICENSOR = "licensor"
    OBLIGOR = "obligor"
    PARTY_A = "party_a"
    PARTY_B = "party_b"
    RECEIVING_PARTY = "receiving_party"
    RECIPIENT = "recipient"
    SENDER = "sender"
    UNKNOWN = "unknown"
    VENDOR = "vendor"


class TimelineEventType(StrEnum):
    """Enumerate normalized timeline event kinds.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    DEADLINE = "deadline"
    DURATION = "duration"
    KEY_DATE = "key_date"


class ClauseType(StrEnum):
    """Enumerate normalized clause families for composable contract workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    CONFIDENTIALITY = "confidentiality"
    DATA_PROTECTION = "data_protection"
    DELIVERABLES = "deliverables"
    DISPUTE_RESOLUTION = "dispute_resolution"
    GOVERNING_LAW = "governing_law"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    LIABILITY = "liability"
    NOTICE = "notice"
    PAYMENT = "payment"
    SCOPE = "scope"
    TERM_DURATION = "term_duration"
    TERMINATION = "termination"
    OTHER = "other"


class ObligationDirection(StrEnum):
    """Enumerate directional relationships for extracted obligations.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    MUTUAL = "mutual"
    OWED_BY = "owed_by"
    OWED_TO = "owed_to"
    UNSPECIFIED = "unspecified"


class DocumentDateType(StrEnum):
    """Enumerate normalized legal date categories for extraction workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    DEADLINE = "deadline"
    DELIVERY_DATE = "delivery_date"
    EFFECTIVE_DATE = "effective_date"
    EXPIRY_DATE = "expiry_date"
    NOTICE_DATE = "notice_date"
    OTHER = "other"
    PAYMENT_DATE = "payment_date"
    RENEWAL_DATE = "renewal_date"
    SIGNATURE_DATE = "signature_date"


class AmountType(StrEnum):
    """Enumerate normalized monetary categories extracted from legal documents.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    DEPOSIT = "deposit"
    FEE = "fee"
    INSTALLMENT = "installment"
    INVOICE = "invoice"
    OTHER = "other"
    PENALTY = "penalty"
    SALARY = "salary"
    TAX = "tax"
    TOTAL = "total"


class DisputeResolutionType(StrEnum):
    """Enumerate normalized dispute-resolution mechanisms.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    ARBITRATION = "arbitration"
    ESCALATION = "escalation"
    LITIGATION = "litigation"
    MEDIATION = "mediation"
    NEGOTIATION = "negotiation"
    OTHER = "other"


class DocumentType(StrEnum):
    """Enumerate common legal document types used by downstream workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    DEMAND_LETTER = "demand_letter"
    EMPLOYMENT_CONTRACT = "employment_contract"
    MOU = "mou"
    NDA = "nda"
    POLICY = "policy"
    PRIVACY_POLICY = "privacy_policy"
    SERVICE_AGREEMENT = "service_agreement"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    """Represent one reusable evidence snippet extracted from tool inputs or references.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    evidence_id: str
    kind: EvidenceKind
    label: str
    excerpt: str
    source_field: str | None = None
    note: str | None = None


class LegalReferenceRecord(BaseModel):
    """Represent one legal-reference anchor normalized for downstream workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    source_id: str
    source_title: str
    authority: str
    citation: str
    rule_id: str | None = None
    rule_priority: str | None = None
    directive: str | None = None


class LegalFinding(BaseModel):
    """Represent one normalized legal finding consumable by future agents.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    finding_id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    summary: str
    recommendation: str | None = None
    related_rule_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    """Represent one normalized follow-up action linked to one or more findings.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    action_id: str
    priority: ActionPriority
    title: str
    description: str
    linked_finding_ids: list[str] = Field(default_factory=list)


class PartyRecord(BaseModel):
    """Represent one party normalized from the tool input payload.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    name: str
    role: PartyRole
    note: str | None = None


class TimelineEvent(BaseModel):
    """Represent one normalized timeline or deadline event.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    label: str
    event_type: TimelineEventType
    value: str
    note: str | None = None


class ClauseRecord(BaseModel):
    """Represent one clause-like unit extracted from a legal document.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    clause_id: str
    clause_type: ClauseType
    heading: str | None = None
    summary: str
    excerpt: str
    importance: FindingSeverity = FindingSeverity.MEDIUM
    is_mandatory_context: bool | None = None


class ExtractedParty(BaseModel):
    """Represent one party extracted from a legal document with source evidence.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    party_id: str
    name: str
    normalized_role: PartyRole = PartyRole.UNKNOWN
    role_label: str | None = None
    source_excerpt: str
    note: str | None = None


class DocumentDateRecord(BaseModel):
    """Represent one extracted date together with its legal meaning.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    date_id: str
    date_type: DocumentDateType
    label: str
    raw_value: str
    normalized_value: str | None = None
    source_excerpt: str
    note: str | None = None


class ObligationRecord(BaseModel):
    """Represent one extracted obligation that can feed later workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    obligation_id: str
    direction: ObligationDirection = ObligationDirection.UNSPECIFIED
    obligated_party: str | None = None
    beneficiary_party: str | None = None
    action: str
    condition: str | None = None
    due_trigger: str | None = None
    source_excerpt: str


class AmountRecord(BaseModel):
    """Represent one monetary amount extracted from a legal document.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    amount_id: str
    amount_type: AmountType
    raw_amount: str
    numeric_value: float | None = None
    currency: str | None = None
    source_excerpt: str
    note: str | None = None


class TerminationTermRecord(BaseModel):
    """Represent one extracted termination term or exit condition.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    term_id: str
    trigger: str
    notice_period: str | None = None
    consequence: str | None = None
    source_excerpt: str
    risk_note: str | None = None


class DisputeResolutionRecord(BaseModel):
    """Represent one extracted dispute-resolution mechanism or pathway.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    resolution_id: str
    resolution_type: DisputeResolutionType
    venue: str | None = None
    governing_law_reference: str | None = None
    escalation_steps: list[str] = Field(default_factory=list)
    source_excerpt: str
    note: str | None = None
