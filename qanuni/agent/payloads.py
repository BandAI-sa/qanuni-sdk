"""Payload builders that adapt agent requests into workflow inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qanuni.agent.metadata import AgentCapabilityMetadata
from qanuni.agent.models import AgentDocument, AgentRunInput

if TYPE_CHECKING:
    from qanuni.agent.state_store import AgentStateStore


class AgentCapabilityPayloadBuilder:
    """Build workflow payloads from the agent request and shared runtime state.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    def build_payload(
        self,
        capability: AgentCapabilityMetadata,
        request: AgentRunInput,
        state_store: AgentStateStore | None = None,
    ) -> dict[str, Any]:
        """Build the payload for one workflow capability.

        Args:
            capability: Capability metadata selected by the planner or executor.
            request: Normalized agent run input from the user.
            state_store: Optional state store with previous workflow results.

        Returns:
            A workflow input payload ready for validation and execution.

        Raises:
            KeyError: If the capability is unknown to the payload builder.
        """
        shared_payload = {
            "shared_runtime": request.shared_runtime,
            "step_runtime_overrides": request.step_runtime_overrides,
        }
        if capability.capability_id == "workflow.contract_review":
            return shared_payload | self._build_contract_review_payload(request)
        if capability.capability_id == "workflow.employment_review":
            return shared_payload | self._build_employment_review_payload(request)
        if capability.capability_id == "workflow.privacy_compliance_review":
            return shared_payload | self._build_privacy_payload(request)
        if capability.capability_id == "workflow.pre_litigation_notice":
            return shared_payload | self._build_pre_litigation_payload(request, state_store)
        if capability.capability_id == "workflow.policy_generation_review":
            return shared_payload | self._build_policy_payload(request)
        raise KeyError(capability.capability_id)

    def _build_contract_review_payload(self, request: AgentRunInput) -> dict[str, Any]:
        primary_document = self._primary_document(request)
        facts = request.facts
        return {
            "document_text": primary_document.text if primary_document is not None else None,
            "document_file": primary_document.file_path if primary_document is not None else None,
            "document_type": (
                primary_document.document_type if primary_document is not None else None
            ),
            "contract_type": facts.get("contract_type"),
            "include_redlines": bool(facts.get("include_redlines", False)),
        }

    def _build_employment_review_payload(self, request: AgentRunInput) -> dict[str, Any]:
        primary_document = self._primary_document(request)
        facts = request.facts
        return {
            "document_text": primary_document.text if primary_document is not None else None,
            "document_file": primary_document.file_path if primary_document is not None else None,
            "document_type": (
                primary_document.document_type if primary_document is not None else None
            ),
            "contract_type": facts.get("contract_type", "indefinite"),
            "probation_days": facts.get("probation_days"),
            "extension_in_writing": bool(facts.get("extension_in_writing", False)),
            "monthly_salary": facts.get("monthly_salary"),
            "years_of_service": facts.get("years_of_service"),
            "termination_reason": facts.get("termination_reason"),
        }

    def _build_privacy_payload(self, request: AgentRunInput) -> dict[str, Any]:
        primary_document = self._primary_document(request)
        facts = request.facts
        return {
            "document_text": primary_document.text if primary_document is not None else None,
            "document_file": primary_document.file_path if primary_document is not None else None,
            "document_type": (
                primary_document.document_type if primary_document is not None else None
            ),
            "processing_context": facts.get("processing_context"),
            "cross_border_transfers": facts.get("cross_border_transfers"),
            "generate_policy_draft": bool(facts.get("generate_policy_draft", False)),
            "company_name": facts.get("company_name"),
            "service_type": facts.get("service_type"),
            "data_collected": list(facts.get("data_collected", [])),
            "data_purposes": list(facts.get("data_purposes", [])),
            "third_party_sharing": bool(facts.get("third_party_sharing", False)),
            "international_transfers": bool(facts.get("international_transfers", False)),
            "dpo_contact": facts.get("dpo_contact"),
        }

    def _build_pre_litigation_payload(
        self,
        request: AgentRunInput,
        state_store: AgentStateStore | None,
    ) -> dict[str, Any]:
        support_document = self._support_document(request)
        facts = request.facts
        support_text = support_document.text if support_document is not None else None
        support_file = support_document.file_path if support_document is not None else None
        if support_text is None and support_file is None and state_store is not None:
            support_text = state_store.primary_document_text()
        return {
            "support_document_text": support_text,
            "support_document_file": support_file,
            "support_document_type": (
                support_document.document_type if support_document is not None else None
            ),
            "contract_type": facts.get("contract_type"),
            "sender_name": facts.get("sender_name"),
            "recipient_name": facts.get("recipient_name"),
            "claim_type": facts.get("claim_type"),
            "claim_amount": facts.get("claim_amount"),
            "incident_description": facts.get("incident_description"),
            "deadline_days": facts.get("deadline_days"),
            "threat_of_action": facts.get("threat_of_action"),
        }

    def _build_policy_payload(self, request: AgentRunInput) -> dict[str, Any]:
        facts = request.facts
        return {
            "policy_kind": facts.get("policy_kind"),
            "policy_type": facts.get("policy_type"),
            "company_name": facts.get("company_name"),
            "industry": facts.get("industry"),
            "employee_count": facts.get("employee_count"),
            "custom_requirements": list(facts.get("custom_requirements", [])),
            "job_title": facts.get("job_title"),
            "department": facts.get("department"),
            "required_experience_years": facts.get("required_experience_years"),
            "required_education": facts.get("required_education"),
            "key_responsibilities": list(facts.get("key_responsibilities", [])),
            "required_skills": list(facts.get("required_skills", [])),
            "saudization_preferred": bool(facts.get("saudization_preferred", False)),
            "salary_range": facts.get("salary_range"),
            "service_type": facts.get("service_type"),
            "data_collected": list(facts.get("data_collected", [])),
            "data_purposes": list(facts.get("data_purposes", [])),
            "third_party_sharing": bool(facts.get("third_party_sharing", False)),
            "international_transfers": bool(facts.get("international_transfers", False)),
            "dpo_contact": facts.get("dpo_contact"),
        }

    def _primary_document(self, request: AgentRunInput) -> AgentDocument | None:
        document: AgentDocument
        for document in request.documents:
            if document.role == "primary":
                return document
        return request.documents[0] if request.documents else None

    def _support_document(self, request: AgentRunInput) -> AgentDocument | None:
        document: AgentDocument
        for document in request.documents:
            if document.role == "supporting":
                return document
        return self._primary_document(request)
