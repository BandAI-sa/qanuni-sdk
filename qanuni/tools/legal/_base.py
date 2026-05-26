"""Shared helpers for atomic legal extraction tools."""

from __future__ import annotations

from typing import ClassVar, Generic, Literal, TypeVar

from qanuni.core.base_tool import BaseTool
from qanuni.models.common import BaseResult, ToolRuntimeConfig
from qanuni.models.legal import LegalExtractionInput
from qanuni.utils.documents import resolve_document_text

OutputResultT = TypeVar("OutputResultT", bound=BaseResult)


class LegalDocumentExtractionTool(
    BaseTool[LegalExtractionInput, OutputResultT],
    Generic[OutputResultT],
):
    """Provide a normalized document-loading flow for atomic extraction tools.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    SAFE_MIN_OUTPUT_TOKENS: ClassVar[int] = 1800
    SAFE_REASONING_EFFORT: ClassVar[Literal["low", "medium", "high"]] = "low"
    SAFE_VERBOSITY: ClassVar[Literal["low", "medium", "high"]] = "low"

    def _execute_sync(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> OutputResultT:
        """Resolve document text and execute the structured provider call.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional provider overrides for this call.

        Returns:
            The structured tool result with provider usage metadata attached.

        Raises:
            QanuniValidationError: If document resolution fails.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider output does not satisfy the schema.
        """
        normalized = input_data.model_copy(
            update={
                "document_text": resolve_document_text(
                    text=input_data.document_text,
                    file_path=input_data.document_file,
                )
            }
        )
        response = self._call_structured_model(
            normalized,
            runtime=self._stabilize_runtime(runtime),
        )
        return response.data.model_copy(
            update={
                "tokens_used": response.usage.total_tokens,
                "model_used": response.model,
            }
        )

    async def _execute_async(
        self,
        input_data: LegalExtractionInput,
        runtime: ToolRuntimeConfig | None,
    ) -> OutputResultT:
        """Resolve document text and execute the structured provider call asynchronously.

        Args:
            input_data: Parsed extraction input for the current document.
            runtime: Optional provider overrides for this call.

        Returns:
            The structured tool result with provider usage metadata attached.

        Raises:
            QanuniValidationError: If document resolution fails.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider output does not satisfy the schema.
        """
        normalized = input_data.model_copy(
            update={
                "document_text": resolve_document_text(
                    text=input_data.document_text,
                    file_path=input_data.document_file,
                )
            }
        )
        response = await self._acall_structured_model(
            normalized,
            runtime=self._stabilize_runtime(runtime),
        )
        return response.data.model_copy(
            update={
                "tokens_used": response.usage.total_tokens,
                "model_used": response.model,
            }
        )

    def _stabilize_runtime(self, runtime: ToolRuntimeConfig | None) -> ToolRuntimeConfig:
        """Clamp extraction calls to compact structured-output settings.

        Args:
            runtime: Optional provider overrides requested by the caller.

        Returns:
            A runtime configuration that preserves transport/model settings while
            forcing compact structured extraction behavior.

        Raises:
            None.
        """
        baseline = runtime or ToolRuntimeConfig()
        configured_max_output_tokens = baseline.max_output_tokens or 0
        return baseline.model_copy(
            update={
                "verbosity": self.SAFE_VERBOSITY,
                "reasoning_effort": self.SAFE_REASONING_EFFORT,
                "max_output_tokens": max(
                    configured_max_output_tokens,
                    self.SAFE_MIN_OUTPUT_TOKENS,
                ),
            }
        )
