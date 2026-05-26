"""Prompt-backed Saudi employment contract generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.labor import (
    EmploymentContractGenerationInput,
    EmploymentContractGenerationResult,
)


class EmploymentContractGenerationTool(
    BaseTool[EmploymentContractGenerationInput, EmploymentContractGenerationResult]
):
    """Generate Arabic employment contracts aligned with Saudi labor context."""

    TOOL_ID = "labor.generate_contract"
    INPUT_MODEL = EmploymentContractGenerationInput
    OUTPUT_MODEL = EmploymentContractGenerationResult
    PROMPT_FILE = "labor/generate_contract.yaml"
    LEGAL_REFERENCE_FILE = "sa/labor/contract_generation_baseline.yaml"

    def _run(
        self,
        input_data: EmploymentContractGenerationInput,
        runtime: ToolRuntimeConfig | None,
    ) -> EmploymentContractGenerationResult:
        """Generate an employment contract synchronously.

        Args:
            input_data: Parsed contract-generation input.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured employment-contract generation result.

        Raises:
            QanuniValidationError: If the input payload is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: EmploymentContractGenerationInput,
        runtime: ToolRuntimeConfig | None,
    ) -> EmploymentContractGenerationResult:
        """Generate an employment contract asynchronously.

        Args:
            input_data: Parsed contract-generation input.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured employment-contract generation result.

        Raises:
            QanuniValidationError: If the input payload is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
