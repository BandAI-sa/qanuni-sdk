"""Prompt-backed legal text simplifier."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.drafting import SimplifyInput, SimplifyResult


class SimplifyLegalTextTool(BaseTool[SimplifyInput, SimplifyResult]):
    """Simplify Arabic legal text for non-lawyer readers."""

    TOOL_ID = "drafting.simplify"
    INPUT_MODEL = SimplifyInput
    OUTPUT_MODEL = SimplifyResult
    PROMPT_FILE = "drafting/simplify.yaml"
    LEGAL_REFERENCE_FILE = "sa/drafting/legal_language_baseline.yaml"

    def _run(self, input_data: SimplifyInput, runtime: ToolRuntimeConfig | None) -> SimplifyResult:
        """Simplify legal text synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: SimplifyInput,
        runtime: ToolRuntimeConfig | None,
    ) -> SimplifyResult:
        """Simplify legal text asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
