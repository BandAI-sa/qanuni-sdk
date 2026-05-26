"""Drafting namespace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.drafting import SimplifyResult, SummaryResult, TextImprovementResult
from qanuni.models.legal import ClauseExtractionResult
from qanuni.providers.base_provider import BaseProvider
from qanuni.tools.drafting.extract_clauses import DraftingClauseExtractionTool
from qanuni.tools.drafting.improve import ImproveTextTool
from qanuni.tools.drafting.simplify import SimplifyLegalTextTool
from qanuni.tools.drafting.summarize import SummarizeLegalDocumentTool


class DraftingTools:
    """Group drafting tools under a single client namespace.

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
        """Initialize drafting namespace tools.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._improve = ImproveTextTool(config, provider_factory)
        self._summarize = SummarizeLegalDocumentTool(config, provider_factory)
        self._simplify = SimplifyLegalTextTool(config, provider_factory)
        self._extract_clauses = DraftingClauseExtractionTool(config, provider_factory)

    def improve(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> TextImprovementResult:
        """Improve legal text synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured text-improvement result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._improve.run(data, runtime=_config, **kwargs)

    async def aimprove(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> TextImprovementResult:
        """Improve legal text asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured text-improvement result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._improve.arun(data, runtime=_config, **kwargs)

    def summarize(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> SummaryResult:
        """Summarize legal documents synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured document-summary result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._summarize.run(data, runtime=_config, **kwargs)

    async def asummarize(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> SummaryResult:
        """Summarize legal documents asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured document-summary result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._summarize.arun(data, runtime=_config, **kwargs)

    def simplify(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> SimplifyResult:
        """Simplify legal text synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured legal-simplification result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._simplify.run(data, runtime=_config, **kwargs)

    async def asimplify(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> SimplifyResult:
        """Simplify legal text asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured legal-simplification result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._simplify.arun(data, runtime=_config, **kwargs)

    def extract_clauses(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ClauseExtractionResult:
        """Extract clause structure from legal drafting synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured clause-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_clauses.run(data, runtime=_config, **kwargs)

    async def aextract_clauses(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ClauseExtractionResult:
        """Extract clause structure from legal drafting asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured clause-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_clauses.arun(data, runtime=_config, **kwargs)
