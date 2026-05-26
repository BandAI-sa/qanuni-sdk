"""Models for compliance tools."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from qanuni.models.common import BaseResult


class PrivacyPolicyInput(BaseModel):
    """Input for generating an Arabic privacy policy."""

    company_name: str
    service_type: str
    data_collected: list[str] = Field(default_factory=list)
    data_purposes: list[str] = Field(default_factory=list)
    third_party_sharing: bool
    international_transfers: bool
    dpo_contact: str | None = None


class PrivacyPolicyResult(BaseResult):
    """Structured privacy-policy generation response."""

    policy_text: str
    pdpl_compliance_score: float
    sections_included: list[str]
    legal_notes: list[str]


class DemandLetterInput(BaseModel):
    """Input for generating a legal demand letter."""

    sender_name: str
    recipient_name: str
    claim_type: str
    claim_amount: float | None = None
    incident_description: str
    deadline_days: int
    threat_of_action: str


class DemandLetterResult(BaseResult):
    """Structured legal demand-letter response."""

    letter_text: str
    legal_notice_elements: list[str]
    strategic_notes: list[str]


class PDPLCheckInput(BaseModel):
    """Input for PDPL-focused compliance checking."""

    document_text: str | None = None
    document_file: str | None = None
    processing_context: str | None = None
    cross_border_transfers: bool | None = None

    @model_validator(mode="after")
    def validate_source(self) -> PDPLCheckInput:
        """Require either a raw compliance document or a file path.

        Args:
            None.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If neither `document_text` nor `document_file` is provided.
        """
        if not self.document_text and not self.document_file:
            raise ValueError("Provide either document_text or document_file.")
        return self


class PDPLCheckResult(BaseResult):
    """Structured response for PDPL compliance checking."""

    compliance_score: float
    compliant_items: list[str]
    gaps: list[str]
    required_actions: list[str]
    summary: str


class VATCheckInput(BaseModel):
    """Input for VAT-focused compliance checking."""

    document_text: str | None = None
    document_file: str | None = None
    transaction_type: str | None = None
    vat_rate: float | None = None

    @model_validator(mode="after")
    def validate_source(self) -> VATCheckInput:
        """Require either a raw document or a file path.

        Args:
            None.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If neither `document_text` nor `document_file` is provided.
        """
        if not self.document_text and not self.document_file:
            raise ValueError("Provide either document_text or document_file.")
        return self


class VATCheckResult(BaseResult):
    """Structured response for VAT compliance checking."""

    compliance_score: float
    vat_treatment: str
    detected_amounts: list[str]
    gaps: list[str]
    required_actions: list[str]
    summary: str
