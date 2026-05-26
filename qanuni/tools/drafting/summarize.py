"""Prompt-backed legal document summarizer."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.drafting import SummaryInput, SummaryResult
from qanuni.utils.documents import resolve_document_text


class SummarizeLegalDocumentTool(BaseTool[SummaryInput, SummaryResult]):
    """Summarize Arabic legal documents into structured insights."""

    TOOL_ID = "drafting.summarize"
    INPUT_MODEL = SummaryInput
    OUTPUT_MODEL = SummaryResult
    PROMPT_FILE = "drafting/summarize.yaml"
    LEGAL_REFERENCE_FILE = "sa/drafting/legal_language_baseline.yaml"

    def _run(self, input_data: SummaryInput, runtime: ToolRuntimeConfig | None) -> SummaryResult:
        """Summarize a legal document synchronously."""
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
        input_data: SummaryInput,
        runtime: ToolRuntimeConfig | None,
    ) -> SummaryResult:
        """Summarize a legal document asynchronously."""
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
