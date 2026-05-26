"""Models for labor-law tools."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from qanuni.models.common import BaseResult, CalculationStep


class EndOfServiceInput(BaseModel):
    """Input payload for end-of-service award calculation."""

    monthly_salary: float = Field(gt=0)
    years_of_service: float = Field(ge=0)
    termination_reason: Literal[
        "resignation",
        "termination_by_employer",
        "contract_completion",
        "mutual_agreement",
    ]
    contract_type: Literal["definite", "indefinite"]


class EndOfServiceResult(BaseResult):
    """Structured result for end-of-service calculations."""

    total_amount: float
    calculation_breakdown: list[CalculationStep]
    legal_explanation: str
    applicable_articles: list[str]
    additional_entitlements: list[str]


class ProbationCheckInput(BaseModel):
    """Input payload for validating probation legality."""

    probation_duration_days: int = Field(
        ge=0,
        validation_alias=AliasChoices("probation_duration_days", "probation_days"),
    )
    contract_type: Literal["definite", "indefinite"] = "indefinite"
    written_extension: bool = Field(
        default=False,
        validation_alias=AliasChoices("written_extension", "extension_in_writing"),
    )
    contract_text_snippet: str | None = None


class ProbationCheckResult(BaseResult):
    """Structured result for probation legality review."""

    is_legal: bool
    max_allowed_days: int
    violations: list[str]
    employee_rights_during_probation: list[str]
    employer_rights_during_probation: list[str]
    legal_explanation: str


class EmploymentContractGenerationInput(BaseModel):
    """Input payload for generating a labor contract draft."""

    employer_name: str
    employee_name: str
    job_title: str
    monthly_salary: float = Field(gt=0)
    contract_type: Literal["definite", "indefinite"]
    work_location: str
    probation_days: int = Field(default=90, ge=0, le=180)
    working_hours_per_week: int = Field(default=48, ge=1, le=60)
    annual_leave_days: int = Field(default=21, ge=0, le=60)
    benefits: list[str] = Field(default_factory=list)


class EmploymentContractGenerationResult(BaseResult):
    """Structured response for labor contract generation."""

    contract_text: str
    included_clauses: list[str]
    compliance_notes: list[str]
    configurable_points: list[str]
