"""Models for legal drafting tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from qanuni.models.common import BaseResult, KeyDate, TextChange


class TextImprovementInput(BaseModel):
    """Input payload for legal text improvement."""

    original_text: str
    improvement_goals: list[Literal["clarity", "formality", "precision", "brevity", "completeness"]]
    context: str | None = None


class TextImprovementResult(BaseResult):
    """Structured result for text improvement."""

    improved_text: str
    changes: list[TextChange]
    overall_assessment: str
    improvement_score: float


class SummaryInput(BaseModel):
    """Input payload for legal document summarization."""

    document_text: str | None = None
    document_file: str | None = None
    summary_length: Literal["brief", "detailed", "executive"]
    focus_on: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self) -> SummaryInput:
        """Require either raw text or a file path.

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


class SummaryResult(BaseResult):
    """Structured summary of a legal document."""

    summary: str
    key_obligations: list[str]
    key_rights: list[str]
    key_dates: list[KeyDate]
    financial_terms: list[str]
    risk_highlights: list[str]


class SimplifyInput(BaseModel):
    """Input payload for legal text simplification."""

    legal_text: str
    target_audience: str = "general_public"


class SimplifyResult(BaseResult):
    """Structured result for simplified legal text."""

    simplified_text: str
    preserved_terms: list[str]
    reader_warnings: list[str]
