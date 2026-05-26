"""Tests for selective caching in mature tool surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qanuni.client import LegalClient
from qanuni.models.common import ToolRuntimeConfig
from qanuni.providers.base_provider import BaseProvider, ProviderResponse


class CountingProvider(BaseProvider):
    """Count provider invocations while returning deterministic responses.

    Args:
        delegate: Provider used to build deterministic fake responses.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, delegate: BaseProvider) -> None:
        """Store the deterministic provider delegate.

        Args:
            delegate: Provider used to build deterministic fake responses.

        Returns:
            None.

        Raises:
            None.
        """
        self.delegate = delegate
        self.calls = 0

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Count synchronous structured-generation calls.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            Delegated structured provider response.

        Raises:
            None.
        """
        self.calls += 1
        return self.delegate.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
            runtime=runtime,
        )

    async def agenerate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Count asynchronous structured-generation calls.

        Args:
            system_prompt: Rendered system prompt sent to the provider.
            user_prompt: Rendered user prompt sent to the provider.
            response_model: Structured response model expected from the provider.
            runtime: Runtime provider overrides for the current call.

        Returns:
            Delegated structured provider response.

        Raises:
            None.
        """
        self.calls += 1
        return await self.delegate.agenerate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
            runtime=runtime,
        )


def test_cache_hits_on_second_review_call(
    provider_factory: object,
    tmp_path: Path,
) -> None:
    """Reuse cached review results instead of calling the provider twice.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.
        tmp_path: Temporary directory used for cache isolation.

    Returns:
        None.

    Raises:
        AssertionError: If the second call does not hit cache.
    """
    counting_provider = CountingProvider(provider_factory())  # type: ignore[operator]
    client = LegalClient(
        provider_factory=lambda: counting_provider,
        asset_manifest_enforced=False,
        cache_enabled=True,
        cache_dir=tmp_path / "cache",
    )

    first = client.contracts.risk_score(
        contract_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        contract_type="service_agreement",
    )
    second = client.contracts.risk_score(
        contract_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        contract_type="service_agreement",
    )

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert counting_provider.calls == 1


def test_generators_bypass_selective_cache(
    provider_factory: object,
    tmp_path: Path,
) -> None:
    """Keep free-form generation tools outside the selective cache policy.

    Args:
        provider_factory: Pytest fixture that creates the deterministic fake provider.
        tmp_path: Temporary directory used for cache isolation.

    Returns:
        None.

    Raises:
        AssertionError: If a generation tool is unexpectedly cached.
    """
    counting_provider = CountingProvider(provider_factory())  # type: ignore[operator]
    client = LegalClient(
        provider_factory=lambda: counting_provider,
        asset_manifest_enforced=False,
        cache_enabled=True,
        cache_dir=tmp_path / "cache",
    )

    first = client.contracts.generate_nda(
        nda_type="mutual",
        disclosing_party="شركة ألف",
        receiving_party="شركة باء",
        purpose="دراسة شراكة تشغيلية",
        confidentiality_period_years=3,
    )
    second = client.contracts.generate_nda(
        nda_type="mutual",
        disclosing_party="شركة ألف",
        receiving_party="شركة باء",
        purpose="دراسة شراكة تشغيلية",
        confidentiality_period_years=3,
    )

    assert first.cache_hit is False
    assert second.cache_hit is False
    assert counting_provider.calls == 2
