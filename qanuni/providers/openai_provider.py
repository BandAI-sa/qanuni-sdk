"""OpenAI-backed provider implementation."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from openai import APIError as OpenAIAPIError
from openai import APITimeoutError, AsyncOpenAI, OpenAI
from openai.lib._parsing._responses import type_to_text_format_param
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, ValidationError

from qanuni.core.config import QanuniConfig
from qanuni.core.exceptions import (
    ErrorCode,
    QanuniAPIError,
    QanuniConfigError,
    QanuniOutputError,
    QanuniParseError,
)
from qanuni.core.output_parser import OutputParser
from qanuni.models.common import ToolRuntimeConfig
from qanuni.providers.base_provider import BaseProvider, ProviderResponse, ProviderUsage


class OpenAIProvider(BaseProvider):
    """Implement the provider interface using the OpenAI Responses API.

    Args:
        config: Resolved SDK configuration used to initialize OpenAI clients.

    Returns:
        None.

    Raises:
        QanuniConfigError: If the configuration does not include a usable API key.
    """

    def __init__(self, config: QanuniConfig) -> None:
        """Create sync and async OpenAI clients from the resolved SDK configuration.

        Args:
            config: Resolved SDK configuration used to initialize OpenAI clients.

        Returns:
            None.

        Raises:
            QanuniConfigError: If the configuration does not include a usable API key.
        """
        api_key: str | None = config.api_key_value()
        if api_key is None:
            raise QanuniConfigError(
                "OpenAIProvider requires an API key.",
                error_code=ErrorCode.CONFIG_API_KEY_MISSING,
                details={"provider": "openai"},
            )
        self._config = config
        self._client = OpenAI(
            api_key=api_key,
            timeout=config.timeout,
            max_retries=0,
        )
        self._aclient = AsyncOpenAI(
            api_key=api_key,
            timeout=config.timeout,
            max_retries=0,
        )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Generate structured output using the sync OpenAI client.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniAPIError: If the upstream OpenAI call fails.
            QanuniOutputError: If the provider returns unusable structured output.
        """
        attempt_count: int = self._api_attempt_count(runtime)
        attempt_index: int
        for attempt_index in range(1, attempt_count + 1):
            try:
                if hasattr(self._client.responses, "create"):
                    return self._generate_via_native_structured_output(
                        client=self._client,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_model=response_model,
                        runtime=runtime,
                    )

                return self._generate_via_json_fallback(
                    client=self._client,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                    runtime=runtime,
                )
            except OpenAIAPIError as exc:
                if self._should_retry_api_error(
                    error=exc,
                    attempt_index=attempt_index,
                    total_attempts=attempt_count,
                ):
                    continue
                raise self._wrap_api_error(
                    error=exc,
                    operation="generate_structured",
                    runtime=runtime,
                    attempt_index=attempt_index,
                    total_attempts=attempt_count,
                ) from exc

        raise QanuniAPIError(
            "Structured generation exhausted retry attempts unexpectedly.",
            error_code=ErrorCode.API_PROVIDER_FAILURE,
            details={"provider": "openai", "operation": "generate_structured"},
        )

    async def agenerate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Generate structured output using the async OpenAI client.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniAPIError: If the upstream OpenAI call fails.
            QanuniOutputError: If the provider returns unusable structured output.
        """
        attempt_count: int = self._api_attempt_count(runtime)
        attempt_index: int
        for attempt_index in range(1, attempt_count + 1):
            try:
                if hasattr(self._aclient.responses, "create"):
                    return await self._agenerate_via_native_structured_output(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_model=response_model,
                        runtime=runtime,
                    )

                return await self._agenerate_via_json_fallback(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                    runtime=runtime,
                )
            except OpenAIAPIError as exc:
                if self._should_retry_api_error(
                    error=exc,
                    attempt_index=attempt_index,
                    total_attempts=attempt_count,
                ):
                    await asyncio.sleep(0.5 * attempt_index)
                    continue
                raise self._wrap_api_error(
                    error=exc,
                    operation="agenerate_structured",
                    runtime=runtime,
                    attempt_index=attempt_index,
                    total_attempts=attempt_count,
                ) from exc

        raise QanuniAPIError(
            "Structured generation exhausted retry attempts unexpectedly.",
            error_code=ErrorCode.API_PROVIDER_FAILURE,
            details={"provider": "openai", "operation": "agenerate_structured"},
        )

    def _generate_via_native_structured_output(
        self,
        *,
        client: OpenAI,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Call `responses.create` once using strict function-call structured output.

        Args:
            client: Sync OpenAI client used for the request.
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniAPIError: If the provider refuses or truncates the structured call.
            QanuniOutputError: If the returned function arguments do not match the schema.
        """
        response = client.responses.create(
            **self._function_call_request_kwargs(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                runtime=runtime,
            )
        )
        salvaged = self._try_extract_salvaged_function_call_result(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )
        if salvaged is not None:
            data, raw_text = salvaged
            return ProviderResponse(
                data=data,
                model=runtime.model or self._config.model,
                usage=self._usage_from_response(response),
                raw_text=raw_text,
            )
        self._raise_for_refusal_response(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )
        self._raise_for_incomplete_response(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )
        data, raw_text = self._extract_function_call_result(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )

        return ProviderResponse(
            data=data,
            model=runtime.model or self._config.model,
            usage=self._usage_from_response(response),
            raw_text=raw_text,
        )

    async def _agenerate_via_native_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Call `responses.create` once with strict function-call output asynchronously.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniAPIError: If the provider refuses or truncates the structured call.
            QanuniOutputError: If the returned function arguments do not match the schema.
        """
        response = await self._aclient.responses.create(
            **self._function_call_request_kwargs(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                runtime=runtime,
            )
        )
        salvaged = self._try_extract_salvaged_function_call_result(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )
        if salvaged is not None:
            data, raw_text = salvaged
            return ProviderResponse(
                data=data,
                model=runtime.model or self._config.model,
                usage=self._usage_from_response(response),
                raw_text=raw_text,
            )
        self._raise_for_refusal_response(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )
        self._raise_for_incomplete_response(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )
        data, raw_text = self._extract_function_call_result(
            response=response,
            response_model=response_model,
            runtime=runtime,
        )

        return ProviderResponse(
            data=data,
            model=runtime.model or self._config.model,
            usage=self._usage_from_response(response),
            raw_text=raw_text,
        )

    def _function_call_request_kwargs(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> dict[str, Any]:
        """Build request kwargs for strict structured output via forced function calling.

        Args:
            system_prompt: Rendered system prompt content.
            user_prompt: Rendered user prompt content.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A dictionary ready to pass into `responses.create`.

        Raises:
            None.
        """
        tool_name: str = self._function_tool_name(response_model)
        request_kwargs: dict[str, Any] = {
            "model": runtime.model or self._config.model,
            "input": cast(Any, self._input_messages(system_prompt, user_prompt)),
            "max_output_tokens": runtime.max_output_tokens or self._config.max_output_tokens,
            "timeout": runtime.timeout_seconds or self._config.timeout,
            "parallel_tool_calls": False,
            "tool_choice": {"type": "function", "name": tool_name},
            "tools": [self._response_function_tool(response_model)],
            "text": {"verbosity": runtime.verbosity or self._config.verbosity},
        }
        if runtime.temperature is not None:
            request_kwargs["temperature"] = runtime.temperature
        if runtime.reasoning_effort is not None:
            request_kwargs["reasoning"] = {"effort": runtime.reasoning_effort}
        return request_kwargs

    def _generate_via_json_fallback(
        self,
        *,
        client: OpenAI,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Fallback to JSON-schema prompting when direct parsing helpers are unavailable.

        Args:
            client: Sync OpenAI client used for the fallback request.
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniOutputError: If fallback output text is missing or invalid.
        """
        schema: str = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        response = client.responses.create(
            model=runtime.model or self._config.model,
            input=cast(
                Any,
                self._input_messages(
                    (
                        f"{system_prompt}\n\n"
                        "Return valid JSON only. It must match this schema exactly:\n"
                        f"{schema}"
                    ),
                    user_prompt,
                ),
            ),
            max_output_tokens=runtime.max_output_tokens or self._config.max_output_tokens,
            timeout=runtime.timeout_seconds or self._config.timeout,
            text={"verbosity": runtime.verbosity or self._config.verbosity},
            temperature=runtime.temperature,
            reasoning=(
                {"effort": runtime.reasoning_effort}
                if runtime.reasoning_effort is not None
                else None
            ),
        )
        raw_text: str | None = getattr(response, "output_text", None)
        if raw_text is None:
            raise QanuniOutputError(
                "OpenAI fallback response did not include output_text.",
                error_code=ErrorCode.API_OUTPUT_TEXT_MISSING,
                details={"provider": "openai", "model": runtime.model or self._config.model},
            )
        data = OutputParser.parse(raw_text, response_model)
        return ProviderResponse(
            data=data,
            model=runtime.model or self._config.model,
            usage=self._usage_from_response(response),
            raw_text=raw_text,
        )

    async def _agenerate_via_json_fallback(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Async fallback to JSON-schema prompting when direct parsing helpers are unavailable.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniOutputError: If fallback output text is missing or invalid.
        """
        schema: str = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        response = await self._aclient.responses.create(
            model=runtime.model or self._config.model,
            input=cast(
                Any,
                self._input_messages(
                    (
                        f"{system_prompt}\n\n"
                        "Return valid JSON only. It must match this schema exactly:\n"
                        f"{schema}"
                    ),
                    user_prompt,
                ),
            ),
            max_output_tokens=runtime.max_output_tokens or self._config.max_output_tokens,
            timeout=runtime.timeout_seconds or self._config.timeout,
            text={"verbosity": runtime.verbosity or self._config.verbosity},
            temperature=runtime.temperature,
            reasoning=(
                {"effort": runtime.reasoning_effort}
                if runtime.reasoning_effort is not None
                else None
            ),
        )
        raw_text: str | None = getattr(response, "output_text", None)
        if raw_text is None:
            raise QanuniOutputError(
                "OpenAI fallback response did not include output_text.",
                error_code=ErrorCode.API_OUTPUT_TEXT_MISSING,
                details={"provider": "openai", "model": runtime.model or self._config.model},
            )
        data = OutputParser.parse(raw_text, response_model)
        return ProviderResponse(
            data=data,
            model=runtime.model or self._config.model,
            usage=self._usage_from_response(response),
            raw_text=raw_text,
        )

    def _structured_request_kwargs(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> dict[str, Any]:
        """Build request kwargs for strict structured output generation.

        Args:
            system_prompt: Rendered system prompt content.
            user_prompt: Rendered user prompt content.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A dictionary ready to pass into `responses.create`.

        Raises:
            None.
        """
        request_kwargs: dict[str, Any] = {
            "model": runtime.model or self._config.model,
            "input": cast(Any, self._input_messages(system_prompt, user_prompt)),
            "max_output_tokens": runtime.max_output_tokens or self._config.max_output_tokens,
            "timeout": runtime.timeout_seconds or self._config.timeout,
            "text": {
                "format": type_to_text_format_param(response_model),
                "verbosity": runtime.verbosity or self._config.verbosity,
            },
        }
        if runtime.temperature is not None:
            request_kwargs["temperature"] = runtime.temperature
        if runtime.reasoning_effort is not None:
            request_kwargs["reasoning"] = {"effort": runtime.reasoning_effort}
        return request_kwargs

    @staticmethod
    def _function_tool_name(response_model: type[BaseModel]) -> str:
        """Resolve a stable function name used for strict structured tool calls.

        Args:
            response_model: Structured response model expected from the provider.

        Returns:
            A valid function name for the strict tool schema.

        Raises:
            None.
        """
        return response_model.__name__

    def _response_function_tool(self, response_model: type[BaseModel]) -> dict[str, Any]:
        """Build a Responses API function tool with a strict JSON schema.

        Args:
            response_model: Structured response model expected from the provider.

        Returns:
            A Responses API function tool definition.

        Raises:
            None.
        """
        description: str | None = response_model.__doc__
        tool: dict[str, Any] = {
            "type": "function",
            "name": self._function_tool_name(response_model),
            "parameters": to_strict_json_schema(response_model),
            "strict": True,
        }
        if description is not None:
            tool["description"] = description
        return tool

    @staticmethod
    def _api_attempt_count(runtime: ToolRuntimeConfig) -> int:
        """Resolve the total number of provider attempts for a single call.

        Args:
            runtime: Runtime provider overrides for the current call.

        Returns:
            The total number of API attempts, including the first request.

        Raises:
            None.
        """
        retries: int = runtime.api_retries or 0
        return max(1, retries + 1)

    @staticmethod
    def _should_retry_api_error(
        *,
        error: OpenAIAPIError,
        attempt_index: int,
        total_attempts: int,
    ) -> bool:
        """Retry only fast transient API failures, never a plain timeout.

        Args:
            error: OpenAI API exception raised by the current request.
            attempt_index: One-based attempt number currently being processed.
            total_attempts: Total number of allowed API attempts.

        Returns:
            `True` when the provider should retry the upstream request.

        Raises:
            None.
        """
        if attempt_index >= total_attempts:
            return False
        if isinstance(error, APITimeoutError):
            return False
        status_code: int | None = getattr(error, "status_code", None)
        if status_code in {408, 409, 429, 500, 502, 503, 504}:
            return True
        return error.__class__.__name__ == "APIConnectionError"

    def _enrich_structured_error(
        self,
        *,
        error: QanuniParseError | QanuniOutputError,
        raw_text: str,
        response: Any,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> QanuniParseError | QanuniOutputError:
        """Attach provider context to structured-output failures.

        Args:
            error: Original parse or schema error raised by the parser.
            raw_text: Raw text returned by the provider.
            response: Raw OpenAI response object.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides used for the failing request.

        Returns:
            An enriched Qanuni parse or output error.

        Raises:
            None.
        """
        details: dict[str, Any] = {
            **error.details,
            "provider": "openai",
            "model": runtime.model or self._config.model,
            "response_model": response_model.__name__,
            "response_status": getattr(response, "status", None),
            "incomplete_reason": self._incomplete_reason(
                getattr(response, "incomplete_details", None)
            ),
            "max_output_tokens": runtime.max_output_tokens or self._config.max_output_tokens,
            "suggestion": (
                "Reduce output size, lower verbosity, or switch to a faster "
                "model for large responses."
            ),
        }
        if isinstance(error, QanuniParseError):
            return QanuniParseError(
                "OpenAI returned invalid structured JSON for the requested schema.",
                raw_response=raw_text,
                error_code=error.error_code,
                details=details,
            )
        return QanuniOutputError(
            "OpenAI returned structured output that did not satisfy the requested schema.",
            error_code=error.error_code,
            details=details,
        )

    def _raise_for_incomplete_response(
        self,
        *,
        response: Any,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> None:
        """Raise a dedicated SDK error when OpenAI ends the response early.

        Args:
            response: Raw OpenAI response object.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides used for the request.

        Returns:
            None.

        Raises:
            QanuniAPIError: If the response finished in an incomplete state.
        """
        response_status: str | None = getattr(response, "status", None)
        incomplete_reason: str | None = self._incomplete_reason(
            getattr(response, "incomplete_details", None)
        )
        if response_status != "incomplete":
            return
        raise QanuniAPIError(
            "OpenAI returned an incomplete structured response before the schema finished.",
            error_code=ErrorCode.API_RESPONSE_INCOMPLETE,
            details={
                "provider": "openai",
                "model": runtime.model or self._config.model,
                "response_model": response_model.__name__,
                "response_status": response_status,
                "incomplete_reason": incomplete_reason,
                "max_output_tokens": runtime.max_output_tokens or self._config.max_output_tokens,
                "suggestion": (
                    "Raise max_output_tokens for long-form generators or reduce the "
                    "requested output size."
                ),
            },
        )

    def _raise_for_refusal_response(
        self,
        *,
        response: Any,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> None:
        """Raise a dedicated SDK error when the model returns a refusal item.

        Args:
            response: Raw OpenAI response object.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides used for the request.

        Returns:
            None.

        Raises:
            QanuniAPIError: If the model returns a refusal instead of structured data.
        """
        refusal_text: str | None = self._extract_refusal_text(response)
        if refusal_text is None:
            return
        raise QanuniAPIError(
            "OpenAI refused to produce the requested structured output.",
            error_code=ErrorCode.API_RESPONSE_REFUSAL,
            details={
                "provider": "openai",
                "model": runtime.model or self._config.model,
                "response_model": response_model.__name__,
                "refusal": refusal_text,
            },
        )

    def _extract_function_call_result(
        self,
        *,
        response: Any,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> tuple[BaseModel, str]:
        """Extract and validate the forced function-call arguments payload.

        Args:
            response: Raw OpenAI response object.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides used for the request.

        Returns:
            The validated model payload and the raw JSON arguments string.

        Raises:
            QanuniOutputError: If the response does not contain a valid function call.
        """
        tool_name: str = self._function_tool_name(response_model)
        output_item: Any
        for output_item in getattr(response, "output", []):
            if getattr(output_item, "type", None) != "function_call":
                continue
            if getattr(output_item, "name", None) != tool_name:
                continue
            raw_arguments: str = getattr(output_item, "arguments", "")
            try:
                return response_model.model_validate_json(raw_arguments), raw_arguments
            except ValidationError as exc:
                raise QanuniOutputError(
                    "OpenAI returned function-call arguments that did not match the schema.",
                    error_code=ErrorCode.OUTPUT_SCHEMA_MISMATCH,
                    details={
                        "provider": "openai",
                        "model": runtime.model or self._config.model,
                        "response_model": response_model.__name__,
                        "errors": exc.errors(include_url=False),
                    },
                ) from exc

        raise QanuniOutputError(
            "OpenAI did not return the expected structured function call.",
            error_code=ErrorCode.API_EMPTY_PARSED_OUTPUT,
            details={
                "provider": "openai",
                "model": runtime.model or self._config.model,
                "response_model": response_model.__name__,
                "expected_function_name": tool_name,
            },
        )

    def _try_extract_salvaged_function_call_result(
        self,
        *,
        response: Any,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> tuple[BaseModel, str] | None:
        """Return a valid function-call payload even when the overall response is incomplete.

        Args:
            response: Raw OpenAI response object.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides used for the request.

        Returns:
            A validated `(model_payload, raw_arguments)` tuple when function-call
            arguments are already complete enough to satisfy the schema;
            otherwise `None`.

        Raises:
            None.
        """
        if getattr(response, "status", None) != "incomplete":
            return None
        tool_name: str = self._function_tool_name(response_model)
        output_item: Any
        for output_item in getattr(response, "output", []):
            if getattr(output_item, "type", None) != "function_call":
                continue
            if getattr(output_item, "name", None) != tool_name:
                continue
            raw_arguments: str = getattr(output_item, "arguments", "")
            try:
                return response_model.model_validate_json(raw_arguments), raw_arguments
            except ValidationError:
                return None
        return None

    @staticmethod
    def _extract_refusal_text(response: Any) -> str | None:
        """Extract a refusal string from a response output message when present.

        Args:
            response: Raw OpenAI response object.

        Returns:
            The refusal text if present, otherwise `None`.

        Raises:
            None.
        """
        output_item: Any
        for output_item in getattr(response, "output", []):
            if getattr(output_item, "type", None) != "message":
                continue
            content_item: Any
            for content_item in getattr(output_item, "content", []):
                if getattr(content_item, "type", None) == "refusal":
                    refusal: Any = getattr(content_item, "refusal", None)
                    return refusal if isinstance(refusal, str) else None
        return None

    def _wrap_api_error(
        self,
        *,
        error: OpenAIAPIError,
        operation: str,
        runtime: ToolRuntimeConfig,
        attempt_index: int,
        total_attempts: int,
    ) -> QanuniAPIError:
        """Convert provider exceptions into richer SDK API errors.

        Args:
            error: OpenAI API exception raised by the current request.
            operation: Provider operation name used for diagnostics.
            runtime: Runtime provider configuration used for the request.
            attempt_index: One-based attempt number that failed.
            total_attempts: Total number of allowed API attempts.

        Returns:
            A normalized Qanuni API error with provider context.

        Raises:
            None.
        """
        message: str = str(error)
        if isinstance(error, APITimeoutError):
            message = "Request timed out while waiting for the model response."
        return QanuniAPIError(
            message,
            status_code=getattr(error, "status_code", None),
            error_code=ErrorCode.API_PROVIDER_FAILURE,
            details={
                "provider": "openai",
                "operation": operation,
                "model": runtime.model or self._config.model,
                "timeout_seconds": runtime.timeout_seconds or self._config.timeout,
                "max_output_tokens": runtime.max_output_tokens or self._config.max_output_tokens,
                "api_attempt": attempt_index,
                "api_attempts_total": total_attempts,
                "api_retries_configured": runtime.api_retries or 0,
                "exception_type": error.__class__.__name__,
                "suggestion": (
                    "Use a faster model, lower max_output_tokens, or raise timeout_seconds "
                    "explicitly for long-form generation."
                ),
            },
        )

    @staticmethod
    def _incomplete_reason(incomplete_details: Any) -> str | None:
        """Extract the incomplete reason from OpenAI response metadata.

        Args:
            incomplete_details: The provider's incomplete-details payload.

        Returns:
            The incomplete reason if present, otherwise `None`.

        Raises:
            None.
        """
        if incomplete_details is None:
            return None
        if isinstance(incomplete_details, dict):
            value: Any = incomplete_details.get("reason")
            return value if isinstance(value, str) else None
        reason: Any = getattr(incomplete_details, "reason", None)
        return reason if isinstance(reason, str) else None

    @staticmethod
    def _input_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
        """Build the minimal Responses API input message payload.

        Args:
            system_prompt: Rendered system prompt content.
            user_prompt: Rendered user prompt content.

        Returns:
            A list of provider message payload dictionaries.

        Raises:
            None.
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _usage_from_response(response: Any) -> ProviderUsage:
        """Normalize provider usage information from the OpenAI response object.

        Args:
            response: OpenAI response object returned by the SDK.

        Returns:
            A normalized provider-usage object.

        Raises:
            None.
        """
        usage: Any = getattr(response, "usage", None)
        if usage is None:
            return ProviderUsage()
        return ProviderUsage(
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
