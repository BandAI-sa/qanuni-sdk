from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APITimeoutError
from pydantic import BaseModel

from qanuni.core.exceptions import ErrorCode, QanuniAPIError
from qanuni.models.common import ToolRuntimeConfig
from qanuni.providers.openai_provider import OpenAIProvider


class DemoStructuredResult(BaseModel):
    """Minimal schema used to exercise strict function-call structured output."""

    title: str
    score: int


class FakeSyncResponses:
    """Record sync structured calls and replay canned responses."""

    def __init__(self, responses: list[Any]) -> None:
        """Store canned sync responses.

        Args:
            responses: Ordered responses returned on successive `create` calls.

        Returns:
            None.

        Raises:
            None.
        """
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        """Return the next canned response while recording request kwargs.

        Args:
            **kwargs: Request kwargs passed to the provider client.

        Returns:
            The next canned response object.

        Raises:
            AssertionError: If more calls are made than configured responses.
        """
        self.calls.append(kwargs)
        return self._responses[len(self.calls) - 1]


class FakeAsyncResponses:
    """Record async structured calls and replay canned responses."""

    def __init__(self, responses: list[Any]) -> None:
        """Store canned async responses.

        Args:
            responses: Ordered responses returned on successive `create` calls.

        Returns:
            None.

        Raises:
            None.
        """
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        """Return the next canned response while recording request kwargs.

        Args:
            **kwargs: Request kwargs passed to the provider client.

        Returns:
            The next canned response object.

        Raises:
            AssertionError: If more calls are made than configured responses.
        """
        self.calls.append(kwargs)
        return self._responses[len(self.calls) - 1]


class FakeSyncResponsesWithError:
    """Raise a configured exception on the first sync call."""

    def __init__(self, error: Exception) -> None:
        """Store the exception to raise during `create`.

        Args:
            error: Exception raised whenever `create` is called.

        Returns:
            None.

        Raises:
            None.
        """
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        """Raise the configured exception after recording request kwargs.

        Args:
            **kwargs: Request kwargs passed to the provider client.

        Returns:
            Never returns successfully.

        Raises:
            Exception: The configured provider exception.
        """
        self.calls.append(kwargs)
        raise self.error


def make_function_call_response(
    *,
    arguments: str,
    function_name: str = "DemoStructuredResult",
    status: str = "completed",
    incomplete_reason: str | None = None,
) -> Any:
    """Create a fake Responses API payload with a strict function-call item.

    Args:
        arguments: JSON string returned in the function-call arguments.
        function_name: Tool name returned by the model.
        status: Response lifecycle status.
        incomplete_reason: Optional incomplete reason used by diagnostics.

    Returns:
        A lightweight object that mimics the attributes used by the provider.

    Raises:
        None.
    """
    incomplete_details: Any = (
        SimpleNamespace(reason=incomplete_reason) if incomplete_reason is not None else None
    )
    return SimpleNamespace(
        status=status,
        incomplete_details=incomplete_details,
        output=[
            SimpleNamespace(
                type="function_call",
                name=function_name,
                arguments=arguments,
                status="completed",
            )
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20, total_tokens=30),
    )


def make_refusal_response(*, refusal: str) -> Any:
    """Create a fake response that contains a refusal content item.

    Args:
        refusal: Refusal text returned by the model.

    Returns:
        A lightweight object that mimics the attributes used by the provider.

    Raises:
        None.
    """
    return SimpleNamespace(
        status="completed",
        incomplete_details=None,
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="refusal", refusal=refusal)],
            )
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20, total_tokens=30),
    )


def test_openai_provider_uses_strict_function_calling_for_structured_output(config) -> None:
    """Provider should force one strict function call for structured payloads.

    Args:
        config: Shared SDK configuration fixture.

    Returns:
        None.

    Raises:
        None.
    """
    provider = OpenAIProvider(config)
    fake_responses = FakeSyncResponses(
        responses=[make_function_call_response(arguments='{"title":"analysis","score":88}')]
    )
    provider._client = SimpleNamespace(responses=fake_responses)

    response = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=DemoStructuredResult,
        runtime=ToolRuntimeConfig(
            model="gpt-5-mini",
            max_output_tokens=2400,
            reasoning_effort="medium",
            verbosity="low",
        ),
    )

    assert response.data.title == "analysis"
    assert response.data.score == 88
    assert len(fake_responses.calls) == 1
    assert fake_responses.calls[0]["parallel_tool_calls"] is False
    assert fake_responses.calls[0]["tool_choice"] == {
        "type": "function",
        "name": "DemoStructuredResult",
    }
    assert fake_responses.calls[0]["tools"][0]["name"] == "DemoStructuredResult"
    assert fake_responses.calls[0]["tools"][0]["strict"] is True
    assert fake_responses.calls[0]["text"]["verbosity"] == "low"
    assert fake_responses.calls[0]["reasoning"] == {"effort": "medium"}


def test_openai_provider_salvages_valid_function_call_from_incomplete_response(config) -> None:
    """Valid function-call arguments should still succeed when status is incomplete.

    Args:
        config: Shared SDK configuration fixture.

    Returns:
        None.

    Raises:
        None.
    """
    provider = OpenAIProvider(config)
    fake_responses = FakeSyncResponses(
        responses=[
            make_function_call_response(
                arguments='{"title":"analysis","score":88}',
                status="incomplete",
                incomplete_reason="max_output_tokens",
            )
        ]
    )
    provider._client = SimpleNamespace(responses=fake_responses)

    response = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=DemoStructuredResult,
        runtime=ToolRuntimeConfig(
            model="gpt-5-mini",
            max_output_tokens=1200,
            reasoning_effort="medium",
            verbosity="medium",
        ),
    )

    assert response.data.title == "analysis"
    assert response.data.score == 88


def test_openai_provider_raises_for_incomplete_function_call_response(config) -> None:
    """Incomplete structured responses should fail when arguments remain truncated.

    Args:
        config: Shared SDK configuration fixture.

    Returns:
        None.

    Raises:
        None.
    """
    provider = OpenAIProvider(config)
    fake_responses = FakeSyncResponses(
        responses=[
            make_function_call_response(
                arguments='{"title":"analysis"',
                status="incomplete",
                incomplete_reason="max_output_tokens",
            )
        ]
    )
    provider._client = SimpleNamespace(responses=fake_responses)

    with pytest.raises(QanuniAPIError) as exc_info:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=DemoStructuredResult,
            runtime=ToolRuntimeConfig(
                model="gpt-5-mini",
                max_output_tokens=1200,
                reasoning_effort="medium",
                verbosity="medium",
            ),
        )

    assert exc_info.value.error_code == ErrorCode.API_RESPONSE_INCOMPLETE
    assert exc_info.value.details["incomplete_reason"] == "max_output_tokens"
    assert exc_info.value.details["response_model"] == "DemoStructuredResult"


def test_openai_provider_raises_for_model_refusal(config) -> None:
    """Refusals should surface as a dedicated provider error.

    Args:
        config: Shared SDK configuration fixture.

    Returns:
        None.

    Raises:
        None.
    """
    provider = OpenAIProvider(config)
    fake_responses = FakeSyncResponses(
        responses=[make_refusal_response(refusal="I cannot help with that request.")]
    )
    provider._client = SimpleNamespace(responses=fake_responses)

    with pytest.raises(QanuniAPIError) as exc_info:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=DemoStructuredResult,
            runtime=ToolRuntimeConfig(model="gpt-5-mini"),
        )

    assert exc_info.value.error_code == ErrorCode.API_RESPONSE_REFUSAL
    assert exc_info.value.details["refusal"] == "I cannot help with that request."


def test_openai_provider_async_supports_strict_function_calling(config) -> None:
    """Async provider path should extract strict function-call arguments correctly.

    Args:
        config: Shared SDK configuration fixture.

    Returns:
        None.

    Raises:
        None.
    """
    provider = OpenAIProvider(config)
    fake_responses = FakeAsyncResponses(
        responses=[make_function_call_response(arguments='{"title":"analysis","score":91}')]
    )
    provider._aclient = SimpleNamespace(responses=fake_responses)

    response = asyncio.run(
        provider.agenerate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=DemoStructuredResult,
            runtime=ToolRuntimeConfig(model="gpt-5-mini", verbosity="low"),
        )
    )

    assert response.data.score == 91
    assert len(fake_responses.calls) == 1


def test_openai_provider_does_not_retry_timeout_errors(config) -> None:
    """Timeouts should fail once instead of stacking hidden transport retries.

    Args:
        config: Shared SDK configuration fixture.

    Returns:
        None.

    Raises:
        None.
    """
    provider = OpenAIProvider(config)
    timeout_error = APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    fake_responses = FakeSyncResponsesWithError(timeout_error)
    provider._client = SimpleNamespace(responses=fake_responses)

    with pytest.raises(QanuniAPIError) as exc_info:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=DemoStructuredResult,
            runtime=ToolRuntimeConfig(
                model="gpt-5-mini",
                timeout_seconds=30,
                api_retries=2,
                max_output_tokens=1800,
                verbosity="low",
            ),
        )

    assert len(fake_responses.calls) == 1
    assert exc_info.value.details["timeout_seconds"] == 30
    assert exc_info.value.details["api_retries_configured"] == 2
    assert exc_info.value.details["exception_type"] == "APITimeoutError"
