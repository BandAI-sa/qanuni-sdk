from __future__ import annotations

from typing import Any

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.drafting import TextImprovementResult
from qanuni.providers.base_provider import BaseProvider, ProviderResponse, ProviderUsage
from qanuni.tools.drafting.improve import ImproveTextTool
from qanuni.tools.labor.end_of_service import EndOfServiceTool
from qanuni.tools.legal.extract_clauses import ClauseExtractionTool


class CapturingProvider(BaseProvider):
    """Capture rendered prompts while returning deterministic structured output."""

    def __init__(self) -> None:
        """Initialize empty prompt-capture buffers.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self.system_prompt: str = ""
        self.user_prompt: str = ""
        self.response_field_names: list[str] = []

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Capture prompts and return a deterministic text-improvement payload.

        Args:
            system_prompt: Rendered system prompt passed by the tool.
            user_prompt: Rendered user prompt passed by the tool.
            response_model: Structured response model requested by the tool.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A deterministic provider response compatible with the requested schema.

        Raises:
            AssertionError: If the tool requests an unexpected response model.
        """
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.response_field_names = list(response_model.model_fields)
        canonical_model: type[Any] = getattr(
            response_model,
            "__qanuni_output_model__",
            response_model,
        )
        if canonical_model is not TextImprovementResult:
            raise AssertionError(f"Unexpected response model: {response_model}")
        return ProviderResponse(
            data=TextImprovementResult(
                improved_text="يلتزم الطرف الأول بالسداد خلال خمسة عشر يوما من تاريخ الفاتورة.",
                changes=[
                    {
                        "original": "يدفع المبلغ عند الإنجاز.",
                        "improved": (
                            "يلتزم الطرف الأول بالسداد خلال خمسة عشر يوما من تاريخ "
                            "الفاتورة."
                        ),
                        "reason": "جرى توضيح المهلة الزمنية وصياغة الالتزام بشكل أدق.",
                    }
                ],
                overall_assessment="أصبحت الصياغة أوضح وأكثر قابلية للتنفيذ.",
                improvement_score=90.0,
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
        response_model: type[Any],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Capture prompts during async execution using the same deterministic payload.

        Args:
            system_prompt: Rendered system prompt passed by the tool.
            user_prompt: Rendered user prompt passed by the tool.
            response_model: Structured response model requested by the tool.
            runtime: Runtime provider overrides for the current call.

        Returns:
            A deterministic provider response compatible with the requested schema.

        Raises:
            AssertionError: If the tool requests an unexpected response model.
        """
        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
            runtime=runtime,
        )


def test_prompt_backed_tools_attach_legal_reference_metadata(config) -> None:
    """Prompt-backed tools should inject and report the configured legal-reference packet."""
    provider = CapturingProvider()

    def provider_factory() -> BaseProvider:
        return provider

    tool = ImproveTextTool(config, provider_factory)
    result = tool.run(
        original_text="يدفع المبلغ عند الإنجاز.",
        improvement_goals=["clarity", "precision"],
        context="اتفاقية خدمات",
    )

    assert "حزمة المراجع القانونية الملزمة" in provider.system_prompt
    assert "سياسة اللغة" in provider.system_prompt
    assert "sa.drafting.legal_language_baseline" in provider.system_prompt
    assert "drafting-preserve-material-meaning" in provider.system_prompt
    assert "سياق المراجع القانونية" in provider.user_prompt
    assert "tool_id" not in provider.response_field_names
    assert "execution_time_ms" not in provider.response_field_names
    assert "confidence_score" not in provider.response_field_names
    assert "findings" not in provider.response_field_names
    assert result.legal_reference_profile_id == "sa.drafting.legal_language_baseline"
    assert "arabic_legal_drafting_internal_standard" in result.legal_reference_source_ids
    assert "drafting-preserve-material-meaning" in result.legal_reference_rule_ids
    assert result.confidence_score is not None
    assert result.legal_references
    assert result.findings
    assert result.recommended_actions
    assert result.evidence_items


def test_deterministic_tools_attach_legal_reference_metadata(config) -> None:
    """Deterministic tools should still expose the reference packet used for their logic."""
    tool = EndOfServiceTool(config, provider_factory=lambda: CapturingProvider())
    result = tool.run(
        monthly_salary=12000.0,
        years_of_service=3.5,
        termination_reason="contract_completion",
        contract_type="definite",
    )

    assert result.legal_reference_profile_id == "sa.labor.employment_baseline"
    assert "sa_labor_statutory_baseline" in result.legal_reference_source_ids
    assert "labor-distinguish-statutory-vs-contractual" in result.legal_reference_rule_ids
    assert result.confidence_score == 0.98
    assert result.legal_references
    assert result.findings
    assert result.recommended_actions


def test_atomic_legal_tools_attach_extraction_reference_metadata(config, provider_factory) -> None:
    """Atomic legal tools should expose their strict extraction reference packet."""
    tool = ClauseExtractionTool(config, provider_factory)
    result = tool.run(
        document_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        document_type="اتفاقية خدمات",
    )

    assert result.legal_reference_profile_id == "sa.legal.extraction_baseline"
    assert "sa_atomic_extraction_internal_standard" in result.legal_reference_source_ids
    assert "atomic-extraction-anchor-to-explicit-text" in result.legal_reference_rule_ids
    assert result.legal_references
    assert result.evidence_items
