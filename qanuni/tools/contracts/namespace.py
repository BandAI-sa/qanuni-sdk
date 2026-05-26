"""Contracts namespace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.contracts import (
    ContractRiskScoreResult,
    GapAnalysisResult,
    MOUResult,
    NDAResult,
)
from qanuni.providers.base_provider import BaseProvider
from qanuni.tools.contracts.gap_analysis import ContractGapAnalysisTool
from qanuni.tools.contracts.mou_generator import MOUGeneratorTool
from qanuni.tools.contracts.nda_generator import NDAGeneratorTool
from qanuni.tools.contracts.risk_score import ContractRiskScoreTool


class ContractTools:
    """Group contract and commercial tools under a single client namespace.

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
        """Initialize contract namespace tools.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._gap_analysis = ContractGapAnalysisTool(config, provider_factory)
        self._risk_score = ContractRiskScoreTool(config, provider_factory)
        self._generate_nda = NDAGeneratorTool(config, provider_factory)
        self._generate_mou = MOUGeneratorTool(config, provider_factory)

    def gap_analysis(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> GapAnalysisResult:
        """Analyze a contract for structural and legal drafting weaknesses.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured contract-gap analysis result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._gap_analysis.run(data, runtime=_config, **kwargs)

    async def agap_analysis(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> GapAnalysisResult:
        """Run async contract gap analysis.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured contract-gap analysis result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._gap_analysis.arun(data, runtime=_config, **kwargs)

    def risk_score(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ContractRiskScoreResult:
        """Score contract risk synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured contract risk-score result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._risk_score.run(data, runtime=_config, **kwargs)

    async def arisk_score(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ContractRiskScoreResult:
        """Score contract risk asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured contract risk-score result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._risk_score.arun(data, runtime=_config, **kwargs)

    def generate_nda(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> NDAResult:
        """Generate an Arabic NDA suitable for Saudi business contexts.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured NDA generation result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._generate_nda.run(data, runtime=_config, **kwargs)

    async def agenerate_nda(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> NDAResult:
        """Run async NDA generation.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured NDA generation result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._generate_nda.arun(data, runtime=_config, **kwargs)

    def generate_mou(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> MOUResult:
        """Generate an Arabic memorandum of understanding.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured MOU generation result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._generate_mou.run(data, runtime=_config, **kwargs)

    async def agenerate_mou(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> MOUResult:
        """Run async MOU generation.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured MOU generation result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._generate_mou.arun(data, runtime=_config, **kwargs)
