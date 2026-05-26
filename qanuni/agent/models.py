"""Models for the Phase 4 legal agent runtime."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.workflows import WorkflowState
from qanuni.ontology.models import (
    EvidenceItem,
    LegalFinding,
    LegalReferenceRecord,
    PartyRecord,
    RecommendedAction,
    TimelineEvent,
)


class AgentScenario(StrEnum):
    """Enumerate supported deterministic legal-agent scenarios.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    CONTRACT_DISPUTE_NOTICE = "contract_dispute_notice"
    CONTRACT_REVIEW_ONLY = "contract_review_only"
    EMPLOYMENT_RIGHTS_REVIEW = "employment_rights_review"
    POLICY_CREATION_REVIEW = "policy_creation_review"
    PRIVACY_REMEDIATION = "privacy_remediation"
    UNKNOWN = "unknown"


class AgentRunStatus(StrEnum):
    """Enumerate terminal runtime states for the legal agent.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    BLOCKED = "blocked"
    COMPLETED = "completed"
    NEEDS_MORE_INFORMATION = "needs_more_information"


class AgentDocument(BaseModel):
    """Represent one document that can feed the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    name: str | None = None
    text: str | None = None
    file_path: str | None = None
    document_type: str | None = None
    role: Literal["primary", "supporting"] = "primary"

    @model_validator(mode="after")
    def validate_source(self) -> AgentDocument:
        """Require at least one concrete document source.

        Args:
            None.

        Returns:
            The validated agent document instance.

        Raises:
            ValueError: If neither `text` nor `file_path` is supplied.
        """
        if not self.text and not self.file_path:
            raise ValueError("Provide either text or file_path for each agent document.")
        return self


class AgentRunInput(BaseModel):
    """Input payload for one deterministic legal-agent run.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    goal: str
    scenario_hint: AgentScenario | None = None
    documents: list[AgentDocument] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    shared_runtime: ToolRuntimeConfig | None = None
    step_runtime_overrides: dict[str, ToolRuntimeConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_goal(self) -> AgentRunInput:
        """Require a non-empty user goal for planning.

        Args:
            None.

        Returns:
            The validated agent run input instance.

        Raises:
            ValueError: If `goal` is blank after trimming.
        """
        if not self.goal.strip():
            raise ValueError("Provide a non-empty goal for the legal agent.")
        return self


class AgentPlanStep(BaseModel):
    """Describe one planned capability invocation inside the agent plan.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    step_id: str
    capability_id: str
    title: str
    reason: str
    required_inputs: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    produced_entities: list[str] = Field(default_factory=list)
    risk_domain: str
    cost_hint: Literal["low", "medium", "high"]
    latency_hint: Literal["low", "medium", "high"]
    recommended_predecessors: list[str] = Field(default_factory=list)
    status_hint: Literal["ready", "needs_more_information"] = "ready"


class AgentPlan(BaseModel):
    """Represent the deterministic plan produced by the agent planner.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    scenario: AgentScenario | None = None
    status_hint: Literal["ready", "needs_more_information", "blocked"] = "ready"
    plan_summary: str
    steps: list[AgentPlanStep] = Field(default_factory=list)
    planning_notes: list[str] = Field(default_factory=list)


class AgentExecutionStep(BaseModel):
    """Track runtime execution status for one planned agent step.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    step_id: str
    capability_id: str
    title: str
    status: Literal["planned", "completed", "needs_more_information", "blocked"]
    summary: str | None = None
    missing_inputs: list[str] = Field(default_factory=list)
    produced_entities: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Store aggregated runtime state across all executed workflow capabilities.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    selected_scenario: AgentScenario | None = None
    goal: str
    execution_steps: list[AgentExecutionStep] = Field(default_factory=list)
    completed_capabilities: list[str] = Field(default_factory=list)
    workflow_states: dict[str, WorkflowState] = Field(default_factory=dict)
    capability_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    legal_reference_source_ids: list[str] = Field(default_factory=list)
    legal_reference_rule_ids: list[str] = Field(default_factory=list)
    legal_references: list[LegalReferenceRecord] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    findings: list[LegalFinding] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    affected_parties: list[PartyRecord] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)
    generated_artifacts: dict[str, str] = Field(default_factory=dict)
    missing_inputs: list[str] = Field(default_factory=list)
    guardrail_messages: list[str] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    """Return the final result of a legal-agent run.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    status: AgentRunStatus
    scenario: AgentScenario | None = None
    plan: AgentPlan
    state: AgentState
    answer_text: str
    next_question: str | None = None
    run_id: str | None = None
    log_path: str | None = None
