"""Prompt-backed contract gap analysis."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.contracts import GapAnalysisInput, GapAnalysisResult
from qanuni.utils.documents import resolve_document_text


class ContractGapAnalysisTool(BaseTool[GapAnalysisInput, GapAnalysisResult]):
    """Analyze Arabic contracts for omissions, ambiguity, and risk."""

    TOOL_ID = "contracts.gap_analysis"
    INPUT_MODEL = GapAnalysisInput
    OUTPUT_MODEL = GapAnalysisResult
    PROMPT_FILE = "contracts/gap_analysis.yaml"
    LEGAL_REFERENCE_FILE = "sa/contracts/review_baseline.yaml"

    def _run(
        self,
        input_data: GapAnalysisInput,
        runtime: ToolRuntimeConfig | None,
    ) -> GapAnalysisResult:
        """Analyze a contract synchronously."""
        normalized = input_data.model_copy(
            update={
                "contract_text": resolve_document_text(
                    text=input_data.contract_text,
                    file_path=input_data.contract_file,
                )
            }
        )
        response = self._call_structured_model(normalized, runtime=runtime)
        return response.data.model_copy(
            update={
                "tokens_used": response.usage.total_tokens,
                "model_used": response.model,
            }
        )

    async def _arun(
        self,
        input_data: GapAnalysisInput,
        runtime: ToolRuntimeConfig | None,
    ) -> GapAnalysisResult:
        """Analyze a contract asynchronously."""
        normalized = input_data.model_copy(
            update={
                "contract_text": resolve_document_text(
                    text=input_data.contract_text,
                    file_path=input_data.contract_file,
                )
            }
        )
        response = await self._acall_structured_model(normalized, runtime=runtime)
        return response.data.model_copy(
            update={
                "tokens_used": response.usage.total_tokens,
                "model_used": response.model,
            }
        )
