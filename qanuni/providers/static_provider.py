"""Static provider for local demos, smoke tests, and deterministic integration flows."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

from pydantic import BaseModel, ValidationError

from qanuni.core.exceptions import ErrorCode, QanuniAPIError, QanuniOutputError
from qanuni.models.common import ToolRuntimeConfig
from qanuni.providers.base_provider import BaseProvider, ProviderResponse, ProviderUsage

StaticPayload: TypeAlias = BaseModel | dict[str, Any]
StaticResponseFactory: TypeAlias = Callable[
    [type[BaseModel], str, str, ToolRuntimeConfig],
    StaticPayload,
]


class StaticProvider(BaseProvider):
    """Return predefined structured payloads without calling an external model provider.

    Args:
        responses: Optional mapping from response model class to a static payload.
        fallback_factory: Optional callable used when a model is not present in `responses`.
        default_model: Display-only model label surfaced in returned metadata.
        usage: Optional token-usage metadata to attach to responses.

    Returns:
        None.

    Raises:
        ValueError: If no responses and no fallback factory are provided.
    """

    def __init__(
        self,
        *,
        responses: Mapping[type[BaseModel], StaticPayload] | None = None,
        fallback_factory: StaticResponseFactory | None = None,
        default_model: str = "static://qanuni",
        usage: ProviderUsage | None = None,
    ) -> None:
        """Store deterministic payloads used for local prompt-backed flows.

        Args:
            responses: Optional mapping from response model class to a static payload.
            fallback_factory: Optional callable used when a model is not present in `responses`.
            default_model: Display-only model label surfaced in returned metadata.
            usage: Optional token-usage metadata to attach to responses.

        Returns:
            None.

        Raises:
            ValueError: If no responses and no fallback factory are provided.
        """
        if not responses and fallback_factory is None:
            raise ValueError("StaticProvider requires responses or a fallback_factory.")

        self._responses: dict[type[BaseModel], StaticPayload] = dict(responses or {})
        self._fallback_factory: StaticResponseFactory | None = fallback_factory
        self._default_model: str = default_model
        self._usage: ProviderUsage = usage or ProviderUsage(
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
        )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Return a structured response from static local data.

        Args:
            system_prompt: Rendered system prompt supplied by the calling tool.
            user_prompt: Rendered user prompt supplied by the calling tool.
            response_model: Structured response model expected by the calling tool.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized provider response built from local static payloads.

        Raises:
            QanuniAPIError: If no payload is configured for the requested model.
            QanuniOutputError: If the configured payload cannot be validated.
        """
        payload: StaticPayload = self._resolve_payload(
            response_model=response_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            runtime=runtime,
        )
        data: BaseModel = self._coerce_payload(response_model=response_model, payload=payload)
        return ProviderResponse(
            data=data,
            model=runtime.model or self._default_model,
            usage=self._usage,
            raw_text=self._serialize_payload(payload),
        )

    async def agenerate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Return a structured response asynchronously from static local data.

        Args:
            system_prompt: Rendered system prompt supplied by the calling tool.
            user_prompt: Rendered user prompt supplied by the calling tool.
            response_model: Structured response model expected by the calling tool.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A normalized provider response built from local static payloads.

        Raises:
            QanuniAPIError: If no payload is configured for the requested model.
            QanuniOutputError: If the configured payload cannot be validated.
        """
        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
            runtime=runtime,
        )

    def _resolve_payload(
        self,
        *,
        response_model: type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        runtime: ToolRuntimeConfig,
    ) -> StaticPayload:
        canonical_model: type[BaseModel] = getattr(
            response_model,
            "__qanuni_output_model__",
            response_model,
        )
        payload: StaticPayload | None = self._responses.get(response_model)
        if payload is None:
            payload = self._responses.get(canonical_model)
        if payload is not None:
            return payload
        if self._fallback_factory is not None:
            return self._fallback_factory(
                response_model,
                system_prompt,
                user_prompt,
                runtime,
            )
        raise QanuniAPIError(
            "The static provider does not have a configured payload for the requested model.",
            error_code=ErrorCode.API_PROVIDER_FAILURE,
            details={"response_model": canonical_model.__name__},
        )

    def _coerce_payload(
        self,
        *,
        response_model: type[BaseModel],
        payload: StaticPayload,
    ) -> BaseModel:
        if isinstance(payload, response_model):
            return payload

        normalized_payload: dict[str, Any]
        if isinstance(payload, BaseModel):
            normalized_payload = payload.model_dump(mode="json")
        else:
            normalized_payload = payload

        try:
            return response_model.model_validate(normalized_payload)
        except ValidationError as exc:
            raise QanuniOutputError(
                "The static provider payload does not match the requested schema.",
                error_code=ErrorCode.OUTPUT_SCHEMA_MISMATCH,
                details={
                    "response_model": response_model.__name__,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc

    def _serialize_payload(self, payload: StaticPayload) -> str:
        if isinstance(payload, BaseModel):
            normalized_payload: Any = payload.model_dump(mode="json")
        else:
            normalized_payload = payload
        return json.dumps(normalized_payload, ensure_ascii=False, default=str)
