"""Prompt-backed legal text improver."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.drafting import TextImprovementInput, TextImprovementResult


class ImproveTextTool(BaseTool[TextImprovementInput, TextImprovementResult]):
    """Improve Arabic legal drafting with stronger wording."""

    TOOL_ID = "drafting.improve"
    INPUT_MODEL = TextImprovementInput
    OUTPUT_MODEL = TextImprovementResult
    PROMPT_FILE = "drafting/improve.yaml"
    LEGAL_REFERENCE_FILE = "sa/drafting/legal_language_baseline.yaml"

    def _run(
        self,
        input_data: TextImprovementInput,
        runtime: ToolRuntimeConfig | None,
    ) -> TextImprovementResult:
        """Improve legal text synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: TextImprovementInput,
        runtime: ToolRuntimeConfig | None,
    ) -> TextImprovementResult:
        """Improve legal text asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
