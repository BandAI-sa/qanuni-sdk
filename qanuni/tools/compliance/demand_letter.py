"""Prompt-backed demand letter generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.compliance import DemandLetterInput, DemandLetterResult


class DemandLetterTool(BaseTool[DemandLetterInput, DemandLetterResult]):
    """Generate Arabic legal demand letters."""

    TOOL_ID = "compliance.demand_letter"
    INPUT_MODEL = DemandLetterInput
    OUTPUT_MODEL = DemandLetterResult
    PROMPT_FILE = "compliance/demand_letter.yaml"
    LEGAL_REFERENCE_FILE = "sa/compliance/legal_notice_baseline.yaml"

    def _run(
        self,
        input_data: DemandLetterInput,
        runtime: ToolRuntimeConfig | None,
    ) -> DemandLetterResult:
        """Generate a legal demand letter synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: DemandLetterInput,
        runtime: ToolRuntimeConfig | None,
    ) -> DemandLetterResult:
        """Generate a legal demand letter asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
