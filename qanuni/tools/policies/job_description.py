"""Prompt-backed job description generator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.policies import JobDescriptionInput, JobDescriptionResult


class JobDescriptionGeneratorTool(BaseTool[JobDescriptionInput, JobDescriptionResult]):
    """Generate Arabic job descriptions fit for Saudi hiring workflows."""

    TOOL_ID = "policies.job_description"
    INPUT_MODEL = JobDescriptionInput
    OUTPUT_MODEL = JobDescriptionResult
    PROMPT_FILE = "policies/job_description.yaml"
    LEGAL_REFERENCE_FILE = "sa/policies/hr_baseline.yaml"

    def _run(
        self,
        input_data: JobDescriptionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> JobDescriptionResult:
        """Generate a job description synchronously."""
        response = self._call_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: JobDescriptionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> JobDescriptionResult:
        """Generate a job description asynchronously."""
        response = await self._acall_structured_model(input_data, runtime=runtime)
        return response.data.model_copy(
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
