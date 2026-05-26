"""Provider protocol used by prompt-backed tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from qanuni.models.common import ToolRuntimeConfig

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class ProviderUsage:
    """Store token-usage data reported by a model provider.

    Args:
        input_tokens: Number of input tokens consumed, if available.
        output_tokens: Number of output tokens produced, if available.
        total_tokens: Total tokens consumed, if available.

    Returns:
        None.

    Raises:
        None.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True)
class ProviderResponse(Generic[T]):
    """Store a normalized structured response returned by a provider.

    Args:
        data: Structured result parsed into the requested response model.
        model: Effective model identifier used for the request.
        usage: Token-usage information reported by the provider.
        raw_text: Optional raw text returned by the provider.

    Returns:
        None.

    Raises:
        None.
    """

    data: T
    model: str
    usage: ProviderUsage
    raw_text: str | None = None


class BaseProvider(ABC):
    """Define the abstract interface implemented by model providers.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[T]:
        """Generate a structured response using the backing model provider.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider output cannot be parsed into the target schema.
        """

    @abstractmethod
    async def agenerate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[T]:
        """Generate a structured response asynchronously.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized structured provider response.

        Raises:
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider output cannot be parsed into the target schema.
        """
