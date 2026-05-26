"""Prompt-backed contract risk scoring."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.contracts import ContractRiskScoreInput, ContractRiskScoreResult
from qanuni.utils.documents import resolve_document_text


class ContractRiskScoreTool(BaseTool[ContractRiskScoreInput, ContractRiskScoreResult]):
    """Score contract risk for downstream routing and review."""

    TOOL_ID = "contracts.risk_score"
    INPUT_MODEL = ContractRiskScoreInput
    OUTPUT_MODEL = ContractRiskScoreResult
    PROMPT_FILE = "contracts/risk_score.yaml"
    LEGAL_REFERENCE_FILE = "sa/contracts/risk_scoring_baseline.yaml"

    def _run(
        self,
        input_data: ContractRiskScoreInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ContractRiskScoreResult:
        """Score contract risk synchronously.

        Args:
            input_data: Parsed risk-score input for the current contract.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured contract risk-score result.

        Raises:
            QanuniValidationError: If the contract source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
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
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )

    async def _arun(
        self,
        input_data: ContractRiskScoreInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ContractRiskScoreResult:
        """Score contract risk asynchronously.

        Args:
            input_data: Parsed risk-score input for the current contract.
            runtime: Optional per-call runtime overrides.

        Returns:
            A structured contract risk-score result.

        Raises:
            QanuniValidationError: If the contract source is invalid.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider response is malformed.
        """
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
            update={"tokens_used": response.usage.total_tokens, "model_used": response.model}
        )
