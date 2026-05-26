"""Models for commercial and contract tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from qanuni.models.common import AmbiguousClause, BaseResult, ContractGap


class GapAnalysisInput(BaseModel):
    """Input for contract gap analysis."""

    contract_text: str | None = None
    contract_file: str | None = None
    contract_type: str

    @model_validator(mode="after")
    def validate_source(self) -> GapAnalysisInput:
        """Require at least one contract source.

        Args:
            None.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If neither `contract_text` nor `contract_file` is provided.
        """
        if not self.contract_text and not self.contract_file:
            raise ValueError("Provide either contract_text or contract_file.")
        return self


class GapAnalysisResult(BaseResult):
    """Structured contract-gap analysis response."""

    gaps: list[ContractGap]
    overall_risk_level: Literal["low", "medium", "high", "critical"]
    missing_mandatory_clauses: list[str]
    ambiguous_clauses: list[AmbiguousClause]
    compliance_score: float
    summary: str


class NDAGenerationInput(BaseModel):
    """Input for generating a non-disclosure agreement."""

    nda_type: Literal["unilateral", "mutual"]
    disclosing_party: str
    receiving_party: str
    purpose: str
    confidentiality_period_years: int
    jurisdiction: str = "Riyadh, Saudi Arabia"
    governing_law: str = "Saudi law"


class NDAResult(BaseResult):
    """Structured NDA generation response."""

    nda_text: str
    key_clauses_summary: list[str]
    legal_notes: list[str]


class MOUGenerationInput(BaseModel):
    """Input for generating a memorandum of understanding."""

    party_a: str
    party_b: str
    objectives: list[str]
    responsibilities: list[str]
    duration_months: int | None = None
    binding_sections: list[str] | None = None
    non_binding_statement: bool = True


class MOUResult(BaseResult):
    """Structured MOU generation response."""

    mou_text: str
    binding_clauses: list[str]
    caution_notes: list[str]


class ContractRiskScoreInput(BaseModel):
    """Input for contract risk scoring."""

    contract_text: str | None = None
    contract_file: str | None = None
    contract_type: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> ContractRiskScoreInput:
        """Require at least one contract source.

        Args:
            None.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If neither `contract_text` nor `contract_file` is provided.
        """
        if not self.contract_text and not self.contract_file:
            raise ValueError("Provide either contract_text or contract_file.")
        return self


class ContractRiskScoreResult(BaseResult):
    """Structured risk-score response for contract review."""

    risk_score: float
    risk_level: Literal["low", "medium", "high", "critical"]
    primary_risk_drivers: list[str]
    missing_safeguards: list[str]
    mitigation_priorities: list[str]
    summary: str
