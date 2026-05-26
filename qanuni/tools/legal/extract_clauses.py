"""Prompt-backed atomic clause extraction."""

from __future__ import annotations

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.legal import ClauseExtractionResult, LegalExtractionInput
from qanuni.tools.legal._base import LegalDocumentExtractionTool


class ClauseExtractionTool(LegalDocumentExtractionTool[ClauseExtractionResult]):
    """Extract clause-like units from Arabic legal documents."""

    TOOL_ID = "legal.extract_clauses"
    INPUT_MODEL = LegalExtractionInput
    OUTPUT_MODEL = ClauseExtractionResult
    PROMPT_FILE = "legal/extract_clauses.yaml"
    LEGAL_REFERENCE_FILE = "sa/legal/extraction_baseline.yaml"

    def _run(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ClauseExtractionResult:
        """Extract clauses synchronously.

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
        """Extract clauses asynchronously.

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
