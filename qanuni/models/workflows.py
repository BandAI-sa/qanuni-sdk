"""Models for multi-step legal workflows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from qanuni.models.common import ToolRuntimeConfig
from qanuni.ontology.models import (
    AmountRecord,
    ClauseRecord,
    DisputeResolutionRecord,
    DocumentDateRecord,
    DocumentType,
    EvidenceItem,
    LegalFinding,
    LegalReferenceRecord,
    ObligationRecord,
    PartyRecord,
    RecommendedAction,
    TerminationTermRecord,
    TimelineEvent,
)


class WorkflowExecutionOptions(BaseModel):
    """Shared execution options for orchestrated workflows."""

    shared_runtime: ToolRuntimeConfig | None = None
    step_runtime_overrides: dict[str, ToolRuntimeConfig] = Field(default_factory=dict)


class DocumentWorkflowInput(WorkflowExecutionOptions):
    """Base input shared by document-centric workflows."""

    document_text: str | None = None
    document_file: str | None = None
    document_type: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> DocumentWorkflowInput:
        """Require at least one document source.

        Args:
            None.

        Returns:
            The validated workflow input instance.

        Raises:
            ValueError: If neither `document_text` nor `document_file` is supplied.
        """
        if not self.document_text and not self.document_file:
            raise ValueError("Provide either document_text or document_file.")
        return self


class ContractReviewWorkflowInput(DocumentWorkflowInput):
    """Input payload for the contract-review workflow."""

    contract_type: str | None = None
    include_redlines: bool = False


class EmploymentReviewWorkflowInput(DocumentWorkflowInput):
    """Input payload for the employment-review workflow."""

    contract_type: Literal["definite", "indefinite"] = "indefinite"
    probation_days: int | None = Field(default=None, ge=0, le=180)
    extension_in_writing: bool = False
    monthly_salary: float | None = Field(default=None, gt=0)
    years_of_service: float | None = Field(default=None, ge=0)
    termination_reason: Literal[
        "resignation",
        "termination_by_employer",
        "contract_completion",
        "mutual_agreement",
    ] | None = None


class PrivacyComplianceReviewInput(DocumentWorkflowInput):
    """Input payload for the privacy-compliance review workflow."""

    processing_context: str | None = None
    cross_border_transfers: bool | None = None
    generate_policy_draft: bool = False
    company_name: str | None = None
    service_type: str | None = None
    data_collected: list[str] = Field(default_factory=list)
    data_purposes: list[str] = Field(default_factory=list)
    third_party_sharing: bool = False
    international_transfers: bool = False
    dpo_contact: str | None = None

    @model_validator(mode="after")
    def validate_generation_context(self) -> PrivacyComplianceReviewInput:
        """Require enough context when a remediation policy draft is requested.

        Args:
            None.

        Returns:
            The validated workflow input instance.

        Raises:
            ValueError: If `generate_policy_draft` is enabled without core policy fields.
        """
        if self.generate_policy_draft and (not self.company_name or not self.service_type):
            raise ValueError(
                "Provide company_name and service_type when generate_policy_draft is enabled."
            )
        return self


class PreLitigationNoticeWorkflowInput(WorkflowExecutionOptions):
    """Input payload for the pre-litigation notice workflow."""

    support_document_text: str | None = None
    support_document_file: str | None = None
    support_document_type: str | None = None
    contract_type: str | None = None
    sender_name: str
    recipient_name: str
    claim_type: str
    claim_amount: float | None = None
    incident_description: str
    deadline_days: int = Field(gt=0)
    threat_of_action: str


class PolicyGenerationReviewInput(WorkflowExecutionOptions):
    """Input payload for the policy-generation review workflow."""

    policy_kind: Literal["hr_policy", "job_description", "privacy_policy"]
    policy_type: str | None = None
    company_name: str | None = None
    industry: str | None = None
    employee_count: int | None = Field(default=None, gt=0)
    custom_requirements: list[str] = Field(default_factory=list)
    job_title: str | None = None
    department: str | None = None
    required_experience_years: int | None = Field(default=None, ge=0)
    required_education: str | None = None
    key_responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    saudization_preferred: bool = False
    salary_range: str | None = None
    service_type: str | None = None
    data_collected: list[str] = Field(default_factory=list)
    data_purposes: list[str] = Field(default_factory=list)
    third_party_sharing: bool = False
    international_transfers: bool = False
    dpo_contact: str | None = None

    @model_validator(mode="after")
    def validate_policy_kind_requirements(self) -> PolicyGenerationReviewInput:
        """Require the right field set for the selected policy workflow.

        Args:
            None.

        Returns:
            The validated workflow input instance.

        Raises:
            ValueError: If required fields for the selected policy kind are missing.
        """
        if self.policy_kind == "hr_policy":
            if not self.policy_type or not self.company_name or not self.industry:
                raise ValueError(
                    "Provide policy_type, company_name, and industry for hr_policy."
                )
            if self.employee_count is None:
                raise ValueError("Provide employee_count for hr_policy.")
        if self.policy_kind == "job_description":
            missing = [
                field_name
                for field_name, value in (
                    ("job_title", self.job_title),
                    ("department", self.department),
                    ("required_education", self.required_education),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    f"Missing required job-description fields: {', '.join(missing)}."
                )
            if self.required_experience_years is None:
                raise ValueError("Provide required_experience_years for job_description.")
        if self.policy_kind == "privacy_policy":
            if not self.company_name or not self.service_type:
                raise ValueError(
                    "Provide company_name and service_type for privacy_policy."
                )
        return self


class WorkflowStep(BaseModel):
    """One executed or skipped workflow step within a shared orchestration state."""

    step_id: str
    title: str
    tool_id: str | None = None
    status: Literal["completed", "skipped"]
    summary: str
    output_model: str | None = None
    output_payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """Store unified cross-step state shared by all legal workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    workflow_id: str
    execution_time_ms: int = 0
    tokens_used: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    model_used: str | None = None
    cache_hit: bool = False
    cache_key: str | None = None
    logic_asset_hash: str | None = None
    primary_document_type: DocumentType | None = None
    alternative_document_types: list[DocumentType] = Field(default_factory=list)
    classification_confidence_band: Literal["low", "medium", "high"] | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
    step_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    legal_reference_profile_ids: list[str] = Field(default_factory=list)
    legal_reference_source_ids: list[str] = Field(default_factory=list)
    legal_reference_rule_ids: list[str] = Field(default_factory=list)
    legal_references: list[LegalReferenceRecord] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    findings: list[LegalFinding] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    affected_parties: list[PartyRecord] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)
    extracted_clauses: list[ClauseRecord] = Field(default_factory=list)
    extracted_dates: list[DocumentDateRecord] = Field(default_factory=list)
    extracted_amounts: list[AmountRecord] = Field(default_factory=list)
    extracted_obligations: list[ObligationRecord] = Field(default_factory=list)
    extracted_termination_terms: list[TerminationTermRecord] = Field(default_factory=list)
    extracted_dispute_resolution_terms: list[DisputeResolutionRecord] = Field(
        default_factory=list
    )
    generated_artifacts: dict[str, str] = Field(default_factory=dict)


class ContractReviewWorkflowResult(BaseModel):
    """Structured result for the contract-review workflow."""

    state: WorkflowState
    executive_summary: str
    risk_score: float | None = None
    risk_level: Literal["low", "medium", "high", "critical"] | None = None
    missing_mandatory_clauses: list[str] = Field(default_factory=list)
    amendment_recommendations: list[str] = Field(default_factory=list)
    optional_redlines: list[str] = Field(default_factory=list)


class EmploymentReviewWorkflowResult(BaseModel):
    """Structured result for the employment-review workflow."""

    state: WorkflowState
    executive_summary: str
    probation_status: Literal["not_run", "legal", "violation"]
    end_of_service_amount: float | None = None
    employment_risks: list[str] = Field(default_factory=list)
    recommended_follow_ups: list[str] = Field(default_factory=list)


class PrivacyComplianceReviewWorkflowResult(BaseModel):
    """Structured result for the privacy-compliance review workflow."""

    state: WorkflowState
    executive_summary: str
    compliance_score: float | None = None
    key_gaps: list[str] = Field(default_factory=list)
    remediation_priorities: list[str] = Field(default_factory=list)
    policy_draft_text: str | None = None


class PreLitigationNoticeWorkflowResult(BaseModel):
    """Structured result for the pre-litigation notice workflow."""

    state: WorkflowState
    executive_summary: str
    demand_letter_text: str
    claim_support_summary: list[str] = Field(default_factory=list)
    negotiation_points: list[str] = Field(default_factory=list)


class PolicyGenerationReviewWorkflowResult(BaseModel):
    """Structured result for the policy-generation review workflow."""

    state: WorkflowState
    policy_kind: Literal["hr_policy", "job_description", "privacy_policy"]
    executive_summary: str
    generated_text: str
    review_notes: list[str] = Field(default_factory=list)
    follow_up_actions: list[str] = Field(default_factory=list)
