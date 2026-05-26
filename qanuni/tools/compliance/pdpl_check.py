"""Prompt-backed PDPL compliance checker."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.compliance import PDPLCheckInput, PDPLCheckResult
from qanuni.utils.documents import resolve_document_text


class PDPLCheckTool(BaseTool[PDPLCheckInput, PDPLCheckResult]):
    """Check Saudi PDPL-oriented compliance gaps in legal documents."""

    TOOL_ID = "compliance.pdpl_check"
    INPUT_MODEL = PDPLCheckInput
    OUTPUT_MODEL = PDPLCheckResult
    PROMPT_FILE = "compliance/pdpl_check.yaml"
    LEGAL_REFERENCE_FILE = "sa/compliance/pdpl_check_baseline.yaml"

    def _run(
        self,
        input_data: PDPLCheckInput,
        runtime: ToolRuntimeConfig | None,
    ) -> PDPLCheckResult:
        """Check PDPL compliance synchronously.

        Args:
            input_data: Parsed compliance-check input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured PDPL check result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        normalized = input_data.model_copy(
            update={
                "document_text": resolve_document_text(
                    text=input_data.document_text,
                    file_path=input_data.document_file,
                )
            }
        )
        response = self._call_structured_model(normalized, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: PDPLCheckInput,
        runtime: ToolRuntimeConfig | None,
    ) -> PDPLCheckResult:
        """Check PDPL compliance asynchronously.

        Args:
            input_data: Parsed compliance-check input for the current document.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured PDPL check result.

        Raises:
            QanuniValidationError: If the document source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        normalized = input_data.model_copy(
            update={
                "document_text": resolve_document_text(
                    text=input_data.document_text,
                    file_path=input_data.document_file,
                )
            }
        )
        response = await self._acall_structured_model(normalized, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
