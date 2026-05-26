"""Policies namespace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.policies import HRPolicyResult, JobDescriptionResult
from qanuni.providers.base_provider import BaseProvider
from qanuni.tools.policies.hr_policy import HRPolicyGeneratorTool
from qanuni.tools.policies.job_description import JobDescriptionGeneratorTool


class PolicyTools:
    """Group policy and HR-document tools under a single client namespace.

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
        """Initialize policies namespace tools.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._hr_policy = HRPolicyGeneratorTool(config, provider_factory)
        self._job_description = JobDescriptionGeneratorTool(config, provider_factory)

    def generate_hr_policy(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> HRPolicyResult:
        """Generate an HR policy synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured HR-policy result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._hr_policy.run(data, runtime=_config, **kwargs)

    async def agenerate_hr_policy(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> HRPolicyResult:
        """Generate an HR policy asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured HR-policy result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._hr_policy.arun(data, runtime=_config, **kwargs)

    def job_description(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> JobDescriptionResult:
        """Generate a job description synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured job-description result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._job_description.run(data, runtime=_config, **kwargs)

    async def ajob_description(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> JobDescriptionResult:
        """Generate a job description asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured job-description result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._job_description.arun(data, runtime=_config, **kwargs)
