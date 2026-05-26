"""Prompt-backed PDPL privacy policy generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.compliance import PrivacyPolicyInput, PrivacyPolicyResult


class PrivacyPolicyGeneratorTool(BaseTool[PrivacyPolicyInput, PrivacyPolicyResult]):
    """Generate Arabic privacy policies with Saudi PDPL orientation."""

    TOOL_ID = "compliance.generate_privacy_policy"
    INPUT_MODEL = PrivacyPolicyInput
    OUTPUT_MODEL = PrivacyPolicyResult
    PROMPT_FILE = "compliance/privacy_policy.yaml"
    LEGAL_REFERENCE_FILE = "sa/compliance/pdpl_baseline.yaml"

    def _run(
        self,
        input_data: PrivacyPolicyInput,
        runtime: ToolRuntimeConfig | None,
    ) -> PrivacyPolicyResult:
        """Generate a privacy policy synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: PrivacyPolicyInput,
        runtime: ToolRuntimeConfig | None,
    ) -> PrivacyPolicyResult:
        """Generate a privacy policy asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
