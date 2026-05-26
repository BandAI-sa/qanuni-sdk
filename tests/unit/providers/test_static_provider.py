from __future__ import annotations

import asyncio

import pytest

from qanuni.core.exceptions import ErrorCode, QanuniAPIError, QanuniOutputError
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.drafting import TextImprovementResult
from qanuni.providers import StaticProvider


def test_static_provider_returns_structured_payload() -> None:
    """Static provider should coerce configured payloads into the requested response model."""
    provider = StaticProvider(
        responses={
            TextImprovementResult: {
                "improved_text": "النص المحسن",
                "changes": [
                    {
                        "original": "النص القديم",
                        "improved": "النص المحسن",
                        "reason": "زيادة الوضوح",
                    }
                ],
                "overall_assessment": "النتيجة محسنة.",
                "improvement_score": 91.0,
            }
        }
    )

    response = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=TextImprovementResult,
        runtime=ToolRuntimeConfig(),
    )

    assert response.data.improvement_score == 91.0
    assert response.model == "static://qanuni"


def test_static_provider_supports_async_generation() -> None:
    """Static provider should mirror sync behavior in async flows."""
    provider = StaticProvider(
        responses={
            TextImprovementResult: {
                "improved_text": "النص المحسن",
                "changes": [],
                "overall_assessment": "جاهز.",
                "improvement_score": 80.0,
            }
        }
    )

    response = asyncio.run(
        provider.agenerate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=TextImprovementResult,
            runtime=ToolRuntimeConfig(model="demo-local"),
        )
    )

    assert response.data.overall_assessment == "جاهز."
    assert response.model == "demo-local"


def test_static_provider_raises_when_model_is_not_configured() -> None:
    """Static provider should fail clearly when no payload is configured for a response model."""
    provider = StaticProvider(
        responses={
            TextImprovementResult: {
                "improved_text": "النص المحسن",
                "changes": [],
                "overall_assessment": "جاهز.",
                "improvement_score": 80.0,
            }
        }
    )

    with pytest.raises(QanuniAPIError) as exc_info:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=type("AnonymousModel", (), {}),
            runtime=ToolRuntimeConfig(),
        )

    assert exc_info.value.error_code == ErrorCode.API_PROVIDER_FAILURE


def test_static_provider_raises_when_payload_shape_is_invalid() -> None:
    """Static provider should surface schema mismatches as structured output errors."""
    provider = StaticProvider(
        responses={
            TextImprovementResult: {
                "overall_assessment": "ناقص",
            }
        }
    )

    with pytest.raises(QanuniOutputError) as exc_info:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=TextImprovementResult,
            runtime=ToolRuntimeConfig(),
        )

    assert exc_info.value.error_code == ErrorCode.OUTPUT_SCHEMA_MISMATCH
