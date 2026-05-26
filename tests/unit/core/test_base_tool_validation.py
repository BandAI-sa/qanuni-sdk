from __future__ import annotations

import pytest

from qanuni import LegalClient
from qanuni.core.exceptions import ErrorCode, QanuniConfigError, QanuniValidationError
from qanuni.models.common import ToolRuntimeConfig
from qanuni.providers.base_provider import BaseProvider, ProviderResponse, ProviderUsage


def test_prompt_backed_tool_wraps_input_validation_errors(config, provider_factory) -> None:
    """Prompt-backed tools should emit structured Qanuni validation errors for bad payloads."""
    client = LegalClient(provider_factory=provider_factory)

    with pytest.raises(QanuniValidationError) as exc_info:
        client.contracts.gap_analysis(contract_type="service_agreement")

    assert exc_info.value.error_code == ErrorCode.VALIDATION_DOCUMENT_SOURCE_MISSING
    assert exc_info.value.details["tool_id"] == "contracts.gap_analysis"
    assert exc_info.value.details["errors"]


def test_custom_provider_allows_prompt_tools_without_openai_key(provider_factory) -> None:
    """A custom provider should allow local prompt-backed flows without OpenAI credentials."""
    client = LegalClient(provider_factory=provider_factory)

    result = client.drafting.improve(
        original_text="يلتزم الطرف الأول بالدفع عند الإنجاز.",
        improvement_goals=["clarity", "precision"],
        context="service agreement",
    )

    assert result.improvement_score == 88.0


def test_default_provider_still_requires_api_key(tmp_path, monkeypatch) -> None:
    """The default OpenAI provider should still fail clearly when no API key is configured."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = LegalClient()

    with pytest.raises(QanuniConfigError) as exc_info:
        client.drafting.improve(
            original_text="يلتزم الطرف الأول بالدفع عند الإنجاز.",
            improvement_goals=["clarity"],
            context="service agreement",
        )

    assert exc_info.value.error_code == ErrorCode.CONFIG_API_KEY_MISSING


def test_prompt_defaults_override_global_reasoning_and_verbosity() -> None:
    """Tool-specific prompt defaults should beat broad global tuning values.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    class CapturingProvider(BaseProvider):
        """Record the runtime passed by a prompt-backed tool.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """

        def __init__(self) -> None:
            """Initialize a container for the last runtime.

            Args:
                None.

            Returns:
                None.

            Raises:
                None.
            """
            self.last_runtime: ToolRuntimeConfig | None = None

        def generate_structured(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            response_model: type[object],
            runtime: ToolRuntimeConfig,
        ) -> ProviderResponse[object]:
            """Capture runtime values and return a minimal valid payload.

            Args:
                system_prompt: Rendered system instructions.
                user_prompt: Rendered user instructions.
                response_model: Provider-facing result schema.
                runtime: Final runtime config selected by the tool layer.

            Returns:
                A deterministic provider response matching the target schema.

            Raises:
                None.
            """
            del system_prompt, user_prompt
            self.last_runtime = runtime
            return ProviderResponse(
                data=response_model.model_validate(
                    {
                        "letter_text": "خطاب مطالبة موجز.",
                        "legal_notice_elements": [
                            "الأطراف",
                            "الوقائع",
                            "المطالبة",
                            "المهلة",
                        ],
                        "strategic_notes": [
                            "تأكد من مراجعة المستندات المؤيدة قبل الإرسال."
                        ],
                    }
                ),
                model=runtime.model or "fake-model",
                usage=ProviderUsage(total_tokens=123),
                raw_text="{}",
            )

        async def agenerate_structured(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            response_model: type[object],
            runtime: ToolRuntimeConfig,
        ) -> ProviderResponse[object]:
            """Delegate async calls to the same deterministic implementation.

            Args:
                system_prompt: Rendered system instructions.
                user_prompt: Rendered user instructions.
                response_model: Provider-facing result schema.
                runtime: Final runtime config selected by the tool layer.

            Returns:
                A deterministic provider response matching the target schema.

            Raises:
                None.
            """
            return self.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                runtime=runtime,
            )

    provider = CapturingProvider()
    client = LegalClient(
        api_key="sk-test",
        provider_factory=lambda: provider,
        reasoning_effort="medium",
        verbosity="medium",
    )

    client.compliance.demand_letter(
        sender_name="BandAI",
        recipient_name="ClientCo",
        claim_type="سداد",
        claim_amount=1000.0,
        incident_description="فاتورة متأخرة.",
        deadline_days=7,
        threat_of_action="إجراءات قانونية",
    )

    assert provider.last_runtime is not None
    assert provider.last_runtime.reasoning_effort == "low"
    assert provider.last_runtime.verbosity == "low"
