"""Prompt-backed atomic dispute-resolution extraction."""

from __future__ import annotations

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.legal import DisputeResolutionExtractionResult, LegalExtractionInput
from qanuni.tools.legal._base import LegalDocumentExtractionTool


class DisputeResolutionExtractionTool(
    LegalDocumentExtractionTool[DisputeResolutionExtractionResult]
):
    """Extract dispute-resolution terms from Arabic legal documents."""

    TOOL_ID = "legal.extract_dispute_resolution"
    INPUT_MODEL = LegalExtractionInput
    OUTPUT_MODEL = DisputeResolutionExtractionResult
    PROMPT_FILE = "legal/extract_dispute_resolution.yaml"
    LEGAL_REFERENCE_FILE = "sa/legal/extraction_baseline.yaml"

    def _run(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> DisputeResolutionExtractionResult:
        """Extract dispute-resolution terms synchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured dispute-resolution extraction result.

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
    ) -> DisputeResolutionExtractionResult:
        """Extract dispute-resolution terms asynchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured dispute-resolution extraction result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        return await self._execute_async(input_data, runtime)
