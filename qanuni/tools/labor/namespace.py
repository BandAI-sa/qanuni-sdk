"""Labor tool namespace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.labor import (
    EmploymentContractGenerationResult,
    EndOfServiceResult,
    ProbationCheckResult,
)
from qanuni.providers.base_provider import BaseProvider
from qanuni.tools.labor.end_of_service import EndOfServiceTool
from qanuni.tools.labor.generate_contract import EmploymentContractGenerationTool
from qanuni.tools.labor.probation_check import ProbationCheckTool


class LaborTools:
    """Group labor-law tools under a single client namespace.

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
        """Initialize labor namespace tools.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._end_of_service = EndOfServiceTool(config, provider_factory)
        self._probation_check = ProbationCheckTool(config, provider_factory)
        self._generate_contract = EmploymentContractGenerationTool(config, provider_factory)

    def end_of_service(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> EndOfServiceResult:
        """Calculate end-of-service benefits synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured end-of-service result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._end_of_service.run(data, runtime=_config, **kwargs)

    async def aend_of_service(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> EndOfServiceResult:
        """Calculate end-of-service benefits asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured end-of-service result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._end_of_service.arun(data, runtime=_config, **kwargs)

    def probation_check(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ProbationCheckResult:
        """Validate probation-period legality synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured probation-check result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._probation_check.run(data, runtime=_config, **kwargs)

    async def aprobation_check(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ProbationCheckResult:
        """Validate probation-period legality asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured probation-check result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._probation_check.arun(data, runtime=_config, **kwargs)

    def generate_contract(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> EmploymentContractGenerationResult:
        """Generate an employment contract synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured employment-contract generation result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._generate_contract.run(data, runtime=_config, **kwargs)

    async def agenerate_contract(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> EmploymentContractGenerationResult:
        """Generate an employment contract asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured employment-contract generation result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._generate_contract.arun(data, runtime=_config, **kwargs)
