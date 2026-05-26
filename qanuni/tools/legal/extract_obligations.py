"""Prompt-backed atomic obligation extraction."""

from __future__ import annotations

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.legal import LegalExtractionInput, ObligationExtractionResult
from qanuni.tools.legal._base import LegalDocumentExtractionTool


class ObligationExtractionTool(LegalDocumentExtractionTool[ObligationExtractionResult]):
    """Extract obligation records from Arabic legal documents."""

    TOOL_ID = "legal.extract_obligations"
    INPUT_MODEL = LegalExtractionInput
    OUTPUT_MODEL = ObligationExtractionResult
    PROMPT_FILE = "legal/extract_obligations.yaml"
    LEGAL_REFERENCE_FILE = "sa/legal/extraction_baseline.yaml"

    def _run(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ObligationExtractionResult:
        """Extract obligations synchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured obligation-extraction result.

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
    ) -> ObligationExtractionResult:
        """Extract obligations asynchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured obligation-extraction result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        return await self._execute_async(input_data, runtime)
