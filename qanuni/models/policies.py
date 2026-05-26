"""Models for policy and HR document tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from qanuni.models.common import BaseResult


class HRPolicyInput(BaseModel):
    """Input payload for HR policy generation."""

    policy_type: str
    company_name: str
    industry: str
    employee_count: int = Field(gt=0)
    custom_requirements: list[str] = Field(default_factory=list)


class HRPolicyResult(BaseResult):
    """Structured result for HR policy generation."""

    policy_text: str
    saudi_law_compliance_notes: list[str]
    mandatory_inclusions_met: bool
    recommended_additions: list[str]


class JobDescriptionInput(BaseModel):
    """Input payload for job description generation."""

    job_title: str
    department: str
    required_experience_years: int = Field(ge=0)
    required_education: str
    key_responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    saudization_preferred: bool
    salary_range: str | None = None


class JobDescriptionResult(BaseResult):
    """Structured result for job description generation."""

    job_description_text: str
    discriminatory_language_flags: list[str]
    saudization_statement: str | None = None
    legal_compliance_notes: list[str]
