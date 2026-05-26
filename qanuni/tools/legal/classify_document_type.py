"""Prompt-backed legal document classification."""

from __future__ import annotations

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.legal import DocumentTypeClassificationResult, LegalExtractionInput
from qanuni.tools.legal._base import LegalDocumentExtractionTool


class DocumentTypeClassificationTool(
    LegalDocumentExtractionTool[DocumentTypeClassificationResult]
):
    """Classify Arabic legal documents into normalized workflow-ready types."""

    TOOL_ID = "legal.classify_document_type"
    INPUT_MODEL = LegalExtractionInput
    OUTPUT_MODEL = DocumentTypeClassificationResult
    PROMPT_FILE = "legal/classify_document_type.yaml"
    LEGAL_REFERENCE_FILE = "sa/legal/extraction_baseline.yaml"

    def _run(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> DocumentTypeClassificationResult:
        """Classify document type synchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured document-type classification result.

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
    ) -> DocumentTypeClassificationResult:
        """Classify document type asynchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured document-type classification result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        return await self._execute_async(input_data, runtime)
