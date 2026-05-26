"""Prompt-backed NDA generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.contracts import NDAGenerationInput, NDAResult


class NDAGeneratorTool(BaseTool[NDAGenerationInput, NDAResult]):
    """Generate Arabic non-disclosure agreements."""

    TOOL_ID = "contracts.generate_nda"
    INPUT_MODEL = NDAGenerationInput
    OUTPUT_MODEL = NDAResult
    PROMPT_FILE = "contracts/generate_nda.yaml"
    LEGAL_REFERENCE_FILE = "sa/contracts/generation_baseline.yaml"

    def _run(self, input_data: NDAGenerationInput, runtime: ToolRuntimeConfig | None) -> NDAResult:
        """Generate an NDA synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: NDAGenerationInput,
        runtime: ToolRuntimeConfig | None,
    ) -> NDAResult:
        """Generate an NDA asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
