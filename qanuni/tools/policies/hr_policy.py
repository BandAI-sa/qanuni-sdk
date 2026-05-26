"""Prompt-backed HR policy generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.policies import HRPolicyInput, HRPolicyResult


class HRPolicyGeneratorTool(BaseTool[HRPolicyInput, HRPolicyResult]):
    """Generate Arabic HR policy documents."""

    TOOL_ID = "policies.generate_hr_policy"
    INPUT_MODEL = HRPolicyInput
    OUTPUT_MODEL = HRPolicyResult
    PROMPT_FILE = "policies/hr_policy.yaml"
    LEGAL_REFERENCE_FILE = "sa/policies/hr_baseline.yaml"

    def _run(self, input_data: HRPolicyInput, runtime: ToolRuntimeConfig | None) -> HRPolicyResult:
        """Generate an HR policy synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: HRPolicyInput,
        runtime: ToolRuntimeConfig | None,
    ) -> HRPolicyResult:
        """Generate an HR policy asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
