"""Compliance tool namespace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.compliance import (
    DemandLetterResult,
    PDPLCheckResult,
    PrivacyPolicyResult,
    VATCheckResult,
)
from qanuni.providers.base_provider import BaseProvider
from qanuni.tools.compliance.demand_letter import DemandLetterTool
from qanuni.tools.compliance.pdpl_check import PDPLCheckTool
from qanuni.tools.compliance.privacy_policy import PrivacyPolicyGeneratorTool
from qanuni.tools.compliance.vat_check import VATCheckTool


class ComplianceTools:
    """Group compliance tools under a single client namespace.

    Args:
        config: Resolved SDK configuration object.
        provider_factory: Zero-argument callable that returns a provider instance.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        config: QanuniConfig,
        provider_factory: Callable[[], BaseProvider],
    ) -> None:
        """Initialize compliance namespace tools.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._privacy_policy = PrivacyPolicyGeneratorTool(config, provider_factory)
        self._pdpl_check = PDPLCheckTool(config, provider_factory)
        self._vat_check = VATCheckTool(config, provider_factory)
        self._demand_letter = DemandLetterTool(config, provider_factory)

    def generate_privacy_policy(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> PrivacyPolicyResult:
        """Generate an Arabic privacy policy for a Saudi-facing service.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured privacy-policy result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._privacy_policy.run(data, runtime=_config, **kwargs)

    async def agenerate_privacy_policy(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> PrivacyPolicyResult:
        """Run async privacy-policy generation.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured privacy-policy result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._privacy_policy.arun(data, runtime=_config, **kwargs)

    def pdpl_check(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> PDPLCheckResult:
        """Check PDPL compliance synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured PDPL compliance-check result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._pdpl_check.run(data, runtime=_config, **kwargs)

    async def apdpl_check(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> PDPLCheckResult:
        """Check PDPL compliance asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured PDPL compliance-check result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._pdpl_check.arun(data, runtime=_config, **kwargs)

    def vat_check(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> VATCheckResult:
        """Check VAT compliance synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured VAT compliance-check result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._vat_check.run(data, runtime=_config, **kwargs)

    async def avat_check(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> VATCheckResult:
        """Check VAT compliance asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured VAT compliance-check result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._vat_check.arun(data, runtime=_config, **kwargs)

    def demand_letter(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DemandLetterResult:
        """Generate a formal Arabic legal demand letter.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured demand-letter result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._demand_letter.run(data, runtime=_config, **kwargs)

    async def ademand_letter(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DemandLetterResult:
        """Run async demand-letter generation.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured demand-letter result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._demand_letter.arun(data, runtime=_config, **kwargs)
