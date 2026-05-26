"""Shared state store for deterministic legal-agent execution."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from qanuni.agent.models import (
    AgentDocument,
    AgentExecutionStep,
    AgentPlan,
    AgentPlanStep,
    AgentRunInput,
    AgentScenario,
    AgentState,
)
from qanuni.models.workflows import WorkflowState


class AgentStateStore:
    """Collect intermediate workflow results across a single agent run.

    Args:
        request: Normalized agent run input from the user.
        scenario: Scenario selected by the planner.
        plan: Deterministic plan selected for execution.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        *,
        request: AgentRunInput,
        scenario: AgentScenario | None,
        plan: AgentPlan,
    ) -> None:
        """Initialize the agent state store for a new run.

        Args:
            request: Normalized agent run input from the user.
            scenario: Scenario selected by the planner.
            plan: Deterministic plan selected for execution.

        Returns:
            None.

        Raises:
            None.
        """
        self._request = request
        self._state = AgentState(selected_scenario=scenario, goal=request.goal)
        self._results_by_capability: dict[str, BaseModel] = {}
        plan_step: AgentPlanStep
        for plan_step in plan.steps:
            self._state.execution_steps.append(
                AgentExecutionStep(
                    step_id=plan_step.step_id,
                    capability_id=plan_step.capability_id,
                    title=plan_step.title,
                    status="planned",
                    produced_entities=plan_step.produced_entities,
                )
            )

    def record_completed_step(
        self,
        *,
        plan_step: AgentPlanStep,
        result: BaseModel,
    ) -> None:
        """Persist one successful workflow execution into the agent state.

        Args:
            plan_step: Planned step currently being executed.
            result: Workflow result model returned by the SDK.

        Returns:
            None.

        Raises:
            None.
        """
        execution_step = self._execution_step(plan_step.step_id)
        execution_step.status = "completed"
        execution_step.summary = str(getattr(result, "executive_summary", "تم تنفيذ الخطوة بنجاح."))

        self._results_by_capability[plan_step.capability_id] = result
        self._state.completed_capabilities.append(plan_step.capability_id)
        self._state.capability_outputs[plan_step.capability_id] = result.model_dump(mode="json")

        workflow_state = getattr(result, "state", None)
        if isinstance(workflow_state, WorkflowState):
            self._state.workflow_states[plan_step.capability_id] = workflow_state
            self._merge_workflow_state(workflow_state)

    def record_missing_inputs(
        self,
        *,
        plan_step: AgentPlanStep,
        missing_inputs: list[str],
    ) -> None:
        """Persist a stopping condition caused by missing user inputs.

        Args:
            plan_step: Planned step currently being executed.
            missing_inputs: Canonical missing input names detected by guardrails.

        Returns:
            None.

        Raises:
            None.
        """
        execution_step = self._execution_step(plan_step.step_id)
        execution_step.status = "needs_more_information"
        execution_step.summary = "توقفت الخطوة لعدم اكتمال البيانات اللازمة للتنفيذ."
        execution_step.missing_inputs = list(missing_inputs)
        self._extend_unique_scalars(self._state.missing_inputs, missing_inputs)

    def record_blocked_step(
        self,
        *,
        plan_step: AgentPlanStep,
        guardrail_message: str,
    ) -> None:
        """Persist a hard block raised by predecessor or output guardrails.

        Args:
            plan_step: Planned step currently being executed.
            guardrail_message: Human-readable guardrail explanation.

        Returns:
            None.

        Raises:
            None.
        """
        execution_step = self._execution_step(plan_step.step_id)
        execution_step.status = "blocked"
        execution_step.summary = guardrail_message
        self._extend_unique_scalars(self._state.guardrail_messages, [guardrail_message])

    def result_for(self, capability_id: str) -> BaseModel | None:
        """Return one completed workflow result by capability ID.

        Args:
            capability_id: Stable capability identifier from the registry.

        Returns:
            The completed workflow result if available, otherwise `None`.

        Raises:
            None.
        """
        return self._results_by_capability.get(capability_id)

    def completed_capabilities(self) -> list[str]:
        """Return the ordered list of completed capabilities.

        Args:
            None.

        Returns:
            A copy of the completed capability list.

        Raises:
            None.
        """
        return list(self._state.completed_capabilities)

    def primary_document_text(self) -> str | None:
        """Return the primary document text when it exists on the request.

        Args:
            None.

        Returns:
            The primary document text, otherwise `None`.

        Raises:
            None.
        """
        document: AgentDocument
        for document in self._request.documents:
            if document.role == "primary":
                return document.text
        return self._request.documents[0].text if self._request.documents else None

    def build(self) -> AgentState:
        """Return the current agent state snapshot.

        Args:
            None.

        Returns:
            The current agent state snapshot.

        Raises:
            None.
        """
        return self._state

    def _execution_step(self, step_id: str) -> AgentExecutionStep:
        execution_step: AgentExecutionStep
        for execution_step in self._state.execution_steps:
            if execution_step.step_id == step_id:
                return execution_step
        raise KeyError(step_id)

    def _merge_workflow_state(self, workflow_state: WorkflowState) -> None:
        self._extend_unique_scalars(
            self._state.legal_reference_source_ids,
            workflow_state.legal_reference_source_ids,
        )
        self._extend_unique_scalars(
            self._state.legal_reference_rule_ids,
            workflow_state.legal_reference_rule_ids,
        )
        self._extend_unique_models(
            self._state.legal_references,
            workflow_state.legal_references,
        )
        self._extend_unique_models(
            self._state.evidence_items,
            workflow_state.evidence_items,
        )
        self._extend_unique_models(
            self._state.findings,
            workflow_state.findings,
        )
        self._extend_unique_models(
            self._state.recommended_actions,
            workflow_state.recommended_actions,
        )
        self._extend_unique_models(
            self._state.affected_parties,
            workflow_state.affected_parties,
        )
        self._extend_unique_models(
            self._state.timeline_events,
            workflow_state.timeline_events,
        )
        artifact_name: str
        artifact_text: str
        for artifact_name, artifact_text in workflow_state.generated_artifacts.items():
            self._state.generated_artifacts[artifact_name] = artifact_text

    def _extend_unique_scalars(self, target: list[str], values: list[str]) -> None:
        value: str
        for value in values:
            if value not in target:
                target.append(value)

    def _extend_unique_models(self, target: list[Any], values: list[Any]) -> None:
        existing_keys = {self._model_key(item) for item in target}
        value: Any
        for value in values:
            key = self._model_key(value)
            if key in existing_keys:
                continue
            existing_keys.add(key)
            target.append(value)

    def _model_key(self, value: Any) -> str:
        if hasattr(value, "model_dump_json"):
            return str(value.model_dump_json())
        return str(value)
