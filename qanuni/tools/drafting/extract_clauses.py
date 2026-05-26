"""Prompt-backed drafting clause extraction."""

from __future__ import annotations

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.legal import ClauseExtractionResult, LegalExtractionInput
from qanuni.tools.legal._base import LegalDocumentExtractionTool


class DraftingClauseExtractionTool(LegalDocumentExtractionTool[ClauseExtractionResult]):
    """Extract clause structure from Arabic legal drafting for downstream use."""

    TOOL_ID = "drafting.extract_clauses"
    INPUT_MODEL = LegalExtractionInput
    OUTPUT_MODEL = ClauseExtractionResult
    PROMPT_FILE = "drafting/extract_clauses.yaml"
    LEGAL_REFERENCE_FILE = "sa/drafting/clause_extraction_baseline.yaml"

    def _run(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ClauseExtractionResult:
        """Extract drafting clauses synchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured clause-extraction result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        return self._execute_sync(input_data, runtime)

    async def _arun(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ClauseExtractionResult:
        """Extract drafting clauses asynchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured clause-extraction result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        return await self._execute_async(input_data, runtime)
