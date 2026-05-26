"""Models for atomic legal extraction tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from qanuni.models.common import BaseResult
from qanuni.ontology.models import (
    AmountRecord,
    ClauseRecord,
    ClauseType,
    DisputeResolutionRecord,
    DocumentDateRecord,
    DocumentType,
    ExtractedParty,
    ObligationRecord,
    TerminationTermRecord,
)


class LegalExtractionInput(BaseModel):
    """Input shared by atomic legal extraction tools."""

    document_text: str | None = None
    document_file: str | None = None
    document_type: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> LegalExtractionInput:
        """Require at least one legal-document source.

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


class ClauseExtractionResult(BaseResult):
    """Structured response for clause extraction."""

    clauses: list[ClauseRecord]
    extracted_clause_types: list[ClauseType]
    summary: str


class PartyExtractionResult(BaseResult):
    """Structured response for party extraction."""

    parties: list[ExtractedParty]
    summary: str


class DateExtractionResult(BaseResult):
    """Structured response for legal date extraction."""

    dates: list[DocumentDateRecord]
    summary: str


class ObligationExtractionResult(BaseResult):
    """Structured response for obligation extraction."""

    obligations: list[ObligationRecord]
    summary: str


class AmountExtractionResult(BaseResult):
    """Structured response for monetary amount extraction."""

    amounts: list[AmountRecord]
    summary: str


class TerminationTermExtractionResult(BaseResult):
    """Structured response for termination-term extraction."""

    termination_terms: list[TerminationTermRecord]
    summary: str


class DisputeResolutionExtractionResult(BaseResult):
    """Structured response for dispute-resolution extraction."""

    dispute_resolution_terms: list[DisputeResolutionRecord]
    summary: str


class DocumentTypeClassificationResult(BaseResult):
    """Structured response for document-type classification."""

    primary_document_type: DocumentType
    alternative_document_types: list[DocumentType]
    rationale: str
    confidence_band: Literal["low", "medium", "high"]
    summary: str
