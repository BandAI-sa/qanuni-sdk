"""Atomic legal extraction namespace."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.legal import (
    AmountExtractionResult,
    ClauseExtractionResult,
    DateExtractionResult,
    DisputeResolutionExtractionResult,
    DocumentTypeClassificationResult,
    ObligationExtractionResult,
    PartyExtractionResult,
    TerminationTermExtractionResult,
)
from qanuni.providers.base_provider import BaseProvider
from qanuni.tools.legal.classify_document_type import DocumentTypeClassificationTool
from qanuni.tools.legal.extract_amounts import AmountExtractionTool
from qanuni.tools.legal.extract_clauses import ClauseExtractionTool
from qanuni.tools.legal.extract_dates import DateExtractionTool
from qanuni.tools.legal.extract_dispute_resolution import DisputeResolutionExtractionTool
from qanuni.tools.legal.extract_obligations import ObligationExtractionTool
from qanuni.tools.legal.extract_parties import PartyExtractionTool
from qanuni.tools.legal.extract_termination_terms import TerminationTermExtractionTool


class LegalTools:
    """Group atomic legal extraction tools under a single client namespace.

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
        """Initialize atomic extraction tools.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._extract_clauses = ClauseExtractionTool(config, provider_factory)
        self._extract_parties = PartyExtractionTool(config, provider_factory)
        self._extract_dates = DateExtractionTool(config, provider_factory)
        self._extract_amounts = AmountExtractionTool(config, provider_factory)
        self._extract_obligations = ObligationExtractionTool(config, provider_factory)
        self._extract_termination_terms = TerminationTermExtractionTool(
            config,
            provider_factory,
        )
        self._extract_dispute_resolution = DisputeResolutionExtractionTool(
            config,
            provider_factory,
        )
        self._classify_document_type = DocumentTypeClassificationTool(
            config,
            provider_factory,
        )

    def extract_clauses(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ClauseExtractionResult:
        """Extract clause units synchronously.

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
        """Extract clause units asynchronously.

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

    def extract_parties(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> PartyExtractionResult:
        """Extract parties synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured party-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_parties.run(data, runtime=_config, **kwargs)

    async def aextract_parties(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> PartyExtractionResult:
        """Extract parties asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured party-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_parties.arun(data, runtime=_config, **kwargs)

    def extract_dates(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DateExtractionResult:
        """Extract legal dates synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured date-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_dates.run(data, runtime=_config, **kwargs)

    async def aextract_dates(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DateExtractionResult:
        """Extract legal dates asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured date-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_dates.arun(data, runtime=_config, **kwargs)

    def extract_amounts(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> AmountExtractionResult:
        """Extract monetary amounts synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured amount-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_amounts.run(data, runtime=_config, **kwargs)

    async def aextract_amounts(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> AmountExtractionResult:
        """Extract monetary amounts asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured amount-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_amounts.arun(data, runtime=_config, **kwargs)

    def extract_obligations(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ObligationExtractionResult:
        """Extract obligations synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured obligation-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_obligations.run(data, runtime=_config, **kwargs)

    async def aextract_obligations(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> ObligationExtractionResult:
        """Extract obligations asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured obligation-extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_obligations.arun(data, runtime=_config, **kwargs)

    def extract_termination_terms(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> TerminationTermExtractionResult:
        """Extract termination terms synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured termination-term extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_termination_terms.run(data, runtime=_config, **kwargs)

    async def aextract_termination_terms(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> TerminationTermExtractionResult:
        """Extract termination terms asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured termination-term extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_termination_terms.arun(data, runtime=_config, **kwargs)

    def extract_dispute_resolution(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DisputeResolutionExtractionResult:
        """Extract dispute-resolution terms synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured dispute-resolution extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._extract_dispute_resolution.run(data, runtime=_config, **kwargs)

    async def aextract_dispute_resolution(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DisputeResolutionExtractionResult:
        """Extract dispute-resolution terms asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured dispute-resolution extraction result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._extract_dispute_resolution.arun(
            data,
            runtime=_config,
            **kwargs,
        )

    def classify_document_type(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DocumentTypeClassificationResult:
        """Classify legal document types synchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured document-type classification result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return self._classify_document_type.run(data, runtime=_config, **kwargs)

    async def aclassify_document_type(
        self,
        data: Any = None,
        /,
        *,
        _config: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> DocumentTypeClassificationResult:
        """Classify legal document types asynchronously.

        Args:
            data: Optional model instance or plain payload dictionary.
            _config: Optional per-call runtime overrides.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured document-type classification result.

        Raises:
            QanuniValidationError: If the supplied input is invalid.
        """
        return await self._classify_document_type.arun(data, runtime=_config, **kwargs)
