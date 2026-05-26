"""Executor for deterministic legal-agent plans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qanuni.agent.guardrails import AgentGuardrails
from qanuni.agent.logger import AgentLogSession
from qanuni.agent.metadata import AgentCapabilityRegistry
from qanuni.agent.models import AgentPlan, AgentRunInput, AgentRunStatus
from qanuni.agent.payloads import AgentCapabilityPayloadBuilder
from qanuni.agent.state_store import AgentStateStore

if TYPE_CHECKING:
    from qanuni.client import LegalClient


class AgentExecutor:
    """Execute planned workflow capabilities step by step with guardrails.

    Args:
        client: Shared SDK client used to invoke workflow capabilities.
        registry: Capability registry exposed to the executor.
        payload_builder: Shared payload builder used to adapt agent inputs.
        guardrails: Guardrail engine used during execution.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        client: LegalClient,
        registry: AgentCapabilityRegistry,
        payload_builder: AgentCapabilityPayloadBuilder,
        guardrails: AgentGuardrails,
    ) -> None:
        """Store the collaborating services used during execution.

        Args:
            client: Shared SDK client used to invoke workflow capabilities.
            registry: Capability registry exposed to the executor.
            payload_builder: Shared payload builder used to adapt agent inputs.
            guardrails: Guardrail engine used during execution.

        Returns:
            None.

        Raises:
            None.
        """
        self._client = client
        self._registry = registry
        self._payload_builder = payload_builder
        self._guardrails = guardrails

    def execute(
        self,
        request: AgentRunInput,
        plan: AgentPlan,
        *,
        log_session: AgentLogSession | None = None,
    ) -> tuple[AgentRunStatus, AgentStateStore]:
        """Execute one deterministic agent plan synchronously.

        Args:
            request: Normalized agent run input from the user.
            plan: Deterministic plan produced by the planner.
            log_session: Optional per-run logger used to persist execution traces.

        Returns:
            A terminal runtime status plus the populated state store.

        Raises:
            None.
        """
        state_store = AgentStateStore(request=request, scenario=plan.scenario, plan=plan)
        if not plan.steps:
            status = (
                AgentRunStatus.NEEDS_MORE_INFORMATION
                if plan.status_hint == "needs_more_information"
                else AgentRunStatus.BLOCKED
            )
            if log_session is not None:
                log_session.log(
                    level="WARNING",
                    event="run_stopped_without_steps",
                    message="توقف الـ agent قبل التنفيذ لعدم وجود خطوات قابلة للتنفيذ.",
                    details={"status": status.value},
                )
            return status, state_store

        for plan_step in plan.steps:
            capability = self._registry.get_capability(plan_step.capability_id)
            predecessor_issues = self._guardrails.validate_predecessors(
                capability,
                state_store.completed_capabilities(),
            )
            if predecessor_issues:
                guardrail_message = (
                    "لا يمكن تنفيذ هذه الخطوة قبل استكمال المسارات السابقة: "
                    + "، ".join(predecessor_issues)
                )
                state_store.record_blocked_step(
                    plan_step=plan_step,
                    guardrail_message=guardrail_message,
                )
                if log_session is not None:
                    log_session.log_blocked_step(
                        plan_step=plan_step,
                        guardrail_message=guardrail_message,
                    )
                return AgentRunStatus.BLOCKED, state_store

            payload = self._payload_builder.build_payload(capability, request, state_store)
            missing_inputs = self._guardrails.missing_inputs_for_payload(capability, payload)
            if missing_inputs:
                state_store.record_missing_inputs(
                    plan_step=plan_step,
                    missing_inputs=missing_inputs,
                )
                if log_session is not None:
                    log_session.log_missing_inputs(plan_step, missing_inputs)
                return AgentRunStatus.NEEDS_MORE_INFORMATION, state_store

            workflow_callable = getattr(self._client.workflow, capability.workflow_method)
            if log_session is not None:
                log_session.log_step_start(plan_step, payload)
            result = workflow_callable(payload)
            result_issues = self._guardrails.validate_result(capability, result)
            if result_issues:
                guardrail_message = " ".join(result_issues)
                state_store.record_blocked_step(
                    plan_step=plan_step,
                    guardrail_message=guardrail_message,
                )
                if log_session is not None:
                    log_session.log_blocked_step(
                        plan_step=plan_step,
                        guardrail_message=guardrail_message,
                    )
                return AgentRunStatus.BLOCKED, state_store

            state_store.record_completed_step(plan_step=plan_step, result=result)
            if log_session is not None:
                log_session.log_step_completed(plan_step, result)

        return AgentRunStatus.COMPLETED, state_store

    async def aexecute(
        self,
        request: AgentRunInput,
        plan: AgentPlan,
        *,
        log_session: AgentLogSession | None = None,
    ) -> tuple[AgentRunStatus, AgentStateStore]:
        """Execute one deterministic agent plan asynchronously.

        Args:
            request: Normalized agent run input from the user.
            plan: Deterministic plan produced by the planner.
            log_session: Optional per-run logger used to persist execution traces.

        Returns:
            A terminal runtime status plus the populated state store.

        Raises:
            None.
        """
        state_store = AgentStateStore(request=request, scenario=plan.scenario, plan=plan)
        if not plan.steps:
            status = (
                AgentRunStatus.NEEDS_MORE_INFORMATION
                if plan.status_hint == "needs_more_information"
                else AgentRunStatus.BLOCKED
            )
            if log_session is not None:
                log_session.log(
                    level="WARNING",
                    event="run_stopped_without_steps",
                    message="توقف الـ agent قبل التنفيذ لعدم وجود خطوات قابلة للتنفيذ.",
                    details={"status": status.value},
                )
            return status, state_store

        for plan_step in plan.steps:
            capability = self._registry.get_capability(plan_step.capability_id)
            predecessor_issues = self._guardrails.validate_predecessors(
                capability,
                state_store.completed_capabilities(),
            )
            if predecessor_issues:
                guardrail_message = (
                    "لا يمكن تنفيذ هذه الخطوة قبل استكمال المسارات السابقة: "
                    + "، ".join(predecessor_issues)
                )
                state_store.record_blocked_step(
                    plan_step=plan_step,
                    guardrail_message=guardrail_message,
                )
                if log_session is not None:
                    log_session.log_blocked_step(
                        plan_step=plan_step,
                        guardrail_message=guardrail_message,
                    )
                return AgentRunStatus.BLOCKED, state_store

            payload = self._payload_builder.build_payload(capability, request, state_store)
            missing_inputs = self._guardrails.missing_inputs_for_payload(capability, payload)
            if missing_inputs:
                state_store.record_missing_inputs(
                    plan_step=plan_step,
                    missing_inputs=missing_inputs,
                )
                if log_session is not None:
                    log_session.log_missing_inputs(plan_step, missing_inputs)
                return AgentRunStatus.NEEDS_MORE_INFORMATION, state_store

            workflow_callable = getattr(
                self._client.workflow,
                f"a{capability.workflow_method}",
            )
            if log_session is not None:
                log_session.log_step_start(plan_step, payload)
            result = await workflow_callable(payload)
            result_issues = self._guardrails.validate_result(capability, result)
            if result_issues:
                guardrail_message = " ".join(result_issues)
                state_store.record_blocked_step(
                    plan_step=plan_step,
                    guardrail_message=guardrail_message,
                )
                if log_session is not None:
                    log_session.log_blocked_step(
                        plan_step=plan_step,
                        guardrail_message=guardrail_message,
                    )
                return AgentRunStatus.BLOCKED, state_store

            state_store.record_completed_step(plan_step=plan_step, result=result)
            if log_session is not None:
                log_session.log_step_completed(plan_step, result)

        return AgentRunStatus.COMPLETED, state_store
