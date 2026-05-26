"""Capability metadata used by the deterministic legal-agent planner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from qanuni.agent.models import AgentScenario
from qanuni.models.workflows import (
    ContractReviewWorkflowInput,
    EmploymentReviewWorkflowInput,
    PolicyGenerationReviewInput,
    PreLitigationNoticeWorkflowInput,
    PrivacyComplianceReviewInput,
)


@dataclass(frozen=True, slots=True)
class AgentCapabilityMetadata:
    """Describe one workflow capability exposed to the legal-agent runtime.

    Args:
        capability_id: Stable capability identifier selected by the planner.
        workflow_method: Public workflow method name exposed on `client.workflow`.
        title: Human-readable Arabic title for the capability.
        description: Short capability description used in planning notes.
        input_model: Workflow input model used for runtime validation.
        required_inputs: User-facing required input descriptors.
        produced_entities: Normalized entity groups produced by the capability.
        risk_domain: Primary legal domain covered by the capability.
        cost_hint: Relative cost hint used during planning.
        latency_hint: Relative latency hint used during planning.
        recommended_predecessors: Capability IDs that should run before this one.
        supported_scenarios: Scenarios where this capability can be planned.
        completion_requirements: Output paths required before synthesis can trust the result.

    Returns:
        None.

    Raises:
        None.
    """

    capability_id: str
    workflow_method: str
    title: str
    description: str
    input_model: type[BaseModel]
    required_inputs: tuple[str, ...]
    produced_entities: tuple[str, ...]
    risk_domain: str
    cost_hint: Literal["low", "medium", "high"]
    latency_hint: Literal["low", "medium", "high"]
    recommended_predecessors: tuple[str, ...]
    supported_scenarios: tuple[AgentScenario, ...]
    completion_requirements: tuple[str, ...]


class AgentCapabilityRegistry:
    """Expose the fixed capability registry used by the agent planner.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    _CAPABILITIES: tuple[AgentCapabilityMetadata, ...] = (
        AgentCapabilityMetadata(
            capability_id="workflow.contract_review",
            workflow_method="contract_review",
            title="مراجعة عقد متكاملة",
            description="يراجع العقد عبر التصنيف والاستخراج وتحليل الثغرات وتقييم المخاطر.",
            input_model=ContractReviewWorkflowInput,
            required_inputs=("document_text|document_file",),
            produced_entities=(
                "document_type",
                "clauses",
                "parties",
                "dates",
                "amounts",
                "obligations",
                "termination_terms",
                "dispute_resolution",
                "risk_assessment",
                "amendment_recommendations",
            ),
            risk_domain="contracts",
            cost_hint="high",
            latency_hint="high",
            recommended_predecessors=(),
            supported_scenarios=(
                AgentScenario.CONTRACT_DISPUTE_NOTICE,
                AgentScenario.CONTRACT_REVIEW_ONLY,
            ),
            completion_requirements=("executive_summary", "risk_level", "state.steps"),
        ),
        AgentCapabilityMetadata(
            capability_id="workflow.employment_review",
            workflow_method="employment_review",
            title="مراجعة علاقة عمل",
            description="يجمع بين قراءة مستند العمل والفحوصات النظامية الخاصة بالعمالة.",
            input_model=EmploymentReviewWorkflowInput,
            required_inputs=("document_text|document_file",),
            produced_entities=(
                "document_type",
                "parties",
                "dates",
                "amounts",
                "obligations",
                "termination_terms",
                "employment_risks",
                "financial_entitlements",
            ),
            risk_domain="employment",
            cost_hint="medium",
            latency_hint="medium",
            recommended_predecessors=(),
            supported_scenarios=(AgentScenario.EMPLOYMENT_RIGHTS_REVIEW,),
            completion_requirements=("executive_summary", "state.steps"),
        ),
        AgentCapabilityMetadata(
            capability_id="workflow.privacy_compliance_review",
            workflow_method="privacy_compliance_review",
            title="مراجعة امتثال خصوصية",
            description="يفحص المستند الحالي ويولد أولويات معالجة وقد يولد مسودة سياسة علاجية.",
            input_model=PrivacyComplianceReviewInput,
            required_inputs=("document_text|document_file",),
            produced_entities=(
                "document_type",
                "clauses",
                "privacy_gaps",
                "remediation_priorities",
                "policy_draft",
            ),
            risk_domain="privacy",
            cost_hint="medium",
            latency_hint="medium",
            recommended_predecessors=(),
            supported_scenarios=(AgentScenario.PRIVACY_REMEDIATION,),
            completion_requirements=("executive_summary", "compliance_score", "state.steps"),
        ),
        AgentCapabilityMetadata(
            capability_id="workflow.pre_litigation_notice",
            workflow_method="pre_litigation_notice",
            title="إعداد مسار مطالبة قبل النزاع",
            description="ينشئ خطاب مطالبة مدعومًا بتحليل المستندات وتحسين الصياغة.",
            input_model=PreLitigationNoticeWorkflowInput,
            required_inputs=(
                "sender_name",
                "recipient_name",
                "claim_type",
                "incident_description",
                "deadline_days",
                "threat_of_action",
            ),
            produced_entities=(
                "demand_letter",
                "negotiation_points",
                "claim_support_summary",
            ),
            risk_domain="pre_litigation",
            cost_hint="medium",
            latency_hint="medium",
            recommended_predecessors=("workflow.contract_review",),
            supported_scenarios=(AgentScenario.CONTRACT_DISPUTE_NOTICE,),
            completion_requirements=("demand_letter_text", "state.steps"),
        ),
        AgentCapabilityMetadata(
            capability_id="workflow.policy_generation_review",
            workflow_method="policy_generation_review",
            title="توليد ومراجعة سياسة",
            description="يولد سياسة أو وصفًا وظيفيًا ثم يراجع الناتج عبر مسار مخصص.",
            input_model=PolicyGenerationReviewInput,
            required_inputs=("policy_kind",),
            produced_entities=("generated_policy_text", "review_notes", "follow_up_actions"),
            risk_domain="policies",
            cost_hint="medium",
            latency_hint="medium",
            recommended_predecessors=(),
            supported_scenarios=(AgentScenario.POLICY_CREATION_REVIEW,),
            completion_requirements=("generated_text", "state.steps"),
        ),
    )

    def list_capabilities(self) -> list[AgentCapabilityMetadata]:
        """Return all agent capabilities known to the registry.

        Args:
            None.

        Returns:
            A list of agent capability metadata records.

        Raises:
            None.
        """
        return list(self._CAPABILITIES)

    def get_capability(self, capability_id: str) -> AgentCapabilityMetadata:
        """Look up one capability by its stable identifier.

        Args:
            capability_id: Stable capability identifier selected by the planner.

        Returns:
            The matching capability metadata record.

        Raises:
            KeyError: If the requested capability does not exist.
        """
        capability: AgentCapabilityMetadata
        for capability in self._CAPABILITIES:
            if capability.capability_id == capability_id:
                return capability
        raise KeyError(capability_id)

    def capabilities_for_scenario(
        self,
        scenario: AgentScenario,
    ) -> list[AgentCapabilityMetadata]:
        """Return capabilities that support one scenario.

        Args:
            scenario: Scenario identifier selected by the planner.

        Returns:
            A list of capability metadata records allowed for that scenario.

        Raises:
            None.
        """
        return [
            capability
            for capability in self._CAPABILITIES
            if scenario in capability.supported_scenarios
        ]
