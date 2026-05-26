"""Workflow namespace exposed by the public SDK client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qanuni.models.workflows import (
    ContractReviewWorkflowResult,
    EmploymentReviewWorkflowResult,
    PolicyGenerationReviewWorkflowResult,
    PreLitigationNoticeWorkflowResult,
    PrivacyComplianceReviewWorkflowResult,
)
from qanuni.workflows.contract_review import ContractReviewWorkflow
from qanuni.workflows.employment_review import EmploymentReviewWorkflow
from qanuni.workflows.policy_generation_review import PolicyGenerationReviewWorkflow
from qanuni.workflows.pre_litigation_notice import PreLitigationNoticeWorkflow
from qanuni.workflows.privacy_compliance_review import PrivacyComplianceReviewWorkflow

if TYPE_CHECKING:
    from qanuni.client import LegalClient


class WorkflowTools:
    """Expose fixed orchestration workflows on top of the SDK tool namespaces.

    Args:
        client: Shared SDK client used to orchestrate namespace tools.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, client: LegalClient) -> None:
        """Initialize the workflow namespace from the shared SDK client.

        Args:
            client: Shared SDK client used to orchestrate namespace tools.

        Returns:
            None.

        Raises:
            None.
        """
        self._contract_review = ContractReviewWorkflow(client)
        self._employment_review = EmploymentReviewWorkflow(client)
        self._privacy_compliance_review = PrivacyComplianceReviewWorkflow(client)
        self._pre_litigation_notice = PreLitigationNoticeWorkflow(client)
        self._policy_generation_review = PolicyGenerationReviewWorkflow(client)

    def contract_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> ContractReviewWorkflowResult:
        """Run the contract-review workflow synchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured contract-review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return self._contract_review.run(data, **kwargs)

    async def acontract_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> ContractReviewWorkflowResult:
        """Run the contract-review workflow asynchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured contract-review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return await self._contract_review.arun(data, **kwargs)

    def employment_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> EmploymentReviewWorkflowResult:
        """Run the employment-review workflow synchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured employment-review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return self._employment_review.run(data, **kwargs)

    async def aemployment_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> EmploymentReviewWorkflowResult:
        """Run the employment-review workflow asynchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured employment-review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return await self._employment_review.arun(data, **kwargs)

    def privacy_compliance_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> PrivacyComplianceReviewWorkflowResult:
        """Run the privacy-compliance review workflow synchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured privacy-compliance review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return self._privacy_compliance_review.run(data, **kwargs)

    async def aprivacy_compliance_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> PrivacyComplianceReviewWorkflowResult:
        """Run the privacy-compliance review workflow asynchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured privacy-compliance review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return await self._privacy_compliance_review.arun(data, **kwargs)

    def pre_litigation_notice(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> PreLitigationNoticeWorkflowResult:
        """Run the pre-litigation notice workflow synchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured pre-litigation notice workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return self._pre_litigation_notice.run(data, **kwargs)

    async def apre_litigation_notice(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> PreLitigationNoticeWorkflowResult:
        """Run the pre-litigation notice workflow asynchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured pre-litigation notice workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return await self._pre_litigation_notice.arun(data, **kwargs)

    def policy_generation_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> PolicyGenerationReviewWorkflowResult:
        """Run the policy-generation review workflow synchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured policy-generation review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return self._policy_generation_review.run(data, **kwargs)

    async def apolicy_generation_review(
        self,
        data: Any = None,
        /,
        **kwargs: Any,
    ) -> PolicyGenerationReviewWorkflowResult:
        """Run the policy-generation review workflow asynchronously.

        Args:
            data: Optional workflow input model instance or plain payload dictionary.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            A structured policy-generation review workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        return await self._policy_generation_review.arun(data, **kwargs)
