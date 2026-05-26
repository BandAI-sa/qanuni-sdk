"""Prompt-backed MOU generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.contracts import MOUGenerationInput, MOUResult


class MOUGeneratorTool(BaseTool[MOUGenerationInput, MOUResult]):
    """Generate Arabic memoranda of understanding."""

    TOOL_ID = "contracts.generate_mou"
    INPUT_MODEL = MOUGenerationInput
    OUTPUT_MODEL = MOUResult
    PROMPT_FILE = "contracts/generate_mou.yaml"
    LEGAL_REFERENCE_FILE = "sa/contracts/generation_baseline.yaml"

    def _run(self, input_data: MOUGenerationInput, runtime: ToolRuntimeConfig | None) -> MOUResult:
        """Generate an MOU synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: MOUGenerationInput,
        runtime: ToolRuntimeConfig | None,
    ) -> MOUResult:
        """Generate an MOU asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
