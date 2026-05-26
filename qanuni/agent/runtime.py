"""Public runtime facade for the deterministic legal agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from qanuni.agent.executor import AgentExecutor
from qanuni.agent.guardrails import AgentGuardrails
from qanuni.agent.logger import AgentLogManager
from qanuni.agent.metadata import AgentCapabilityMetadata, AgentCapabilityRegistry
from qanuni.agent.models import AgentPlan, AgentRunInput, AgentRunResult
from qanuni.agent.payloads import AgentCapabilityPayloadBuilder
from qanuni.agent.planner import AgentPlanner
from qanuni.agent.synthesizer import AgentAnswerSynthesizer
from qanuni.core.exceptions import ErrorCode, QanuniValidationError

if TYPE_CHECKING:
    from qanuni.client import LegalClient


class AgentRuntime:
    """Expose deterministic planning and execution on top of shipped workflows.

    Args:
        client: Shared SDK client used to execute workflow capabilities.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, client: LegalClient) -> None:
        """Initialize the deterministic runtime and its collaborating services.

        Args:
            client: Shared SDK client used to execute workflow capabilities.

        Returns:
            None.

        Raises:
            None.
        """
        self._client = client
        self._registry = AgentCapabilityRegistry()
        self._payload_builder = AgentCapabilityPayloadBuilder()
        self._guardrails = AgentGuardrails()
        self._planner = AgentPlanner(
            registry=self._registry,
            payload_builder=self._payload_builder,
            guardrails=self._guardrails,
        )
        self._log_manager = AgentLogManager(
            enabled=client.config.agent_logging_enabled,
            log_dir=client.config.agent_log_dir,
        )
        self._executor = AgentExecutor(
            client=client,
            registry=self._registry,
            payload_builder=self._payload_builder,
            guardrails=self._guardrails,
        )
        self._synthesizer = AgentAnswerSynthesizer(self._guardrails)

    def list_capabilities(self) -> list[AgentCapabilityMetadata]:
        """Return the fixed capability registry exposed to the planner.

        Args:
            None.

        Returns:
            A list of deterministic capability metadata records.

        Raises:
            None.
        """
        return self._registry.list_capabilities()

    def plan(
        self,
        data: AgentRunInput | dict[str, Any] | None = None,
        /,
        **kwargs: Any,
    ) -> AgentPlan:
        """Build a deterministic plan without executing it.

        Args:
            data: Optional agent input model instance or plain dictionary payload.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            The deterministic plan selected for the current request.

        Raises:
            QanuniValidationError: If the supplied agent input is invalid.
        """
        request = self._coerce_input(data, kwargs)
        log_session = self._log_manager.start_session(operation="plan")
        log_session.log_request(request)
        try:
            plan = self._planner.plan(request)
            log_session.log_plan(plan)
            return plan
        except Exception as exc:
            log_session.log_exception(event="plan_failed", error=exc)
            raise

    def run(
        self,
        data: AgentRunInput | dict[str, Any] | None = None,
        /,
        **kwargs: Any,
    ) -> AgentRunResult:
        """Plan and execute one deterministic legal-agent run synchronously.

        Args:
            data: Optional agent input model instance or plain dictionary payload.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            The final legal-agent run result.

        Raises:
            QanuniValidationError: If the supplied agent input is invalid.
        """
        request = self._coerce_input(data, kwargs)
        log_session = self._log_manager.start_session(operation="run")
        log_session.log_request(request)
        try:
            plan = self._planner.plan(request)
            log_session.log_plan(plan)
            status, state_store = self._executor.execute(
                request,
                plan,
                log_session=log_session,
            )
            answer_text, next_question = self._synthesizer.synthesize(
                request=request,
                plan=plan,
                state_store=state_store,
                status=status,
            )
            result = AgentRunResult(
                status=status,
                scenario=plan.scenario,
                plan=plan,
                state=state_store.build(),
                answer_text=answer_text,
                next_question=next_question,
                run_id=log_session.run_id,
                log_path=str(log_session.log_path) if log_session.log_path is not None else None,
            )
            log_session.log_run_completed(result)
            return result
        except Exception as exc:
            log_session.log_exception(event="run_failed", error=exc)
            raise

    async def arun(
        self,
        data: AgentRunInput | dict[str, Any] | None = None,
        /,
        **kwargs: Any,
    ) -> AgentRunResult:
        """Plan and execute one deterministic legal-agent run asynchronously.

        Args:
            data: Optional agent input model instance or plain dictionary payload.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            The final legal-agent run result.

        Raises:
            QanuniValidationError: If the supplied agent input is invalid.
        """
        request = self._coerce_input(data, kwargs)
        log_session = self._log_manager.start_session(operation="arun")
        log_session.log_request(request)
        try:
            plan = self._planner.plan(request)
            log_session.log_plan(plan)
            status, state_store = await self._executor.aexecute(
                request,
                plan,
                log_session=log_session,
            )
            answer_text, next_question = self._synthesizer.synthesize(
                request=request,
                plan=plan,
                state_store=state_store,
                status=status,
            )
            result = AgentRunResult(
                status=status,
                scenario=plan.scenario,
                plan=plan,
                state=state_store.build(),
                answer_text=answer_text,
                next_question=next_question,
                run_id=log_session.run_id,
                log_path=str(log_session.log_path) if log_session.log_path is not None else None,
            )
            log_session.log_run_completed(result)
            return result
        except Exception as exc:
            log_session.log_exception(event="run_failed", error=exc)
            raise

    def _coerce_input(
        self,
        data: AgentRunInput | dict[str, Any] | None,
        kwargs: dict[str, Any],
    ) -> AgentRunInput:
        if data is not None and kwargs:
            raise QanuniValidationError(
                "Pass either an agent input model/dict or keyword arguments, not both.",
                error_code=ErrorCode.VALIDATION_INPUT_CONFLICT,
                details={"runtime": "agent"},
            )
        if isinstance(data, AgentRunInput):
            return data
        if data is None:
            payload: dict[str, Any] = kwargs
        elif isinstance(data, dict):
            payload = data
        else:
            raise QanuniValidationError(
                "Expected AgentRunInput or dict input for the legal agent runtime.",
                error_code=ErrorCode.VALIDATION_INPUT_TYPE,
                details={"runtime": "agent", "input_model": AgentRunInput.__name__},
            )
        try:
            return AgentRunInput.model_validate(payload)
        except ValidationError as exc:
            raise QanuniValidationError(
                "The supplied agent input is invalid.",
                error_code=ErrorCode.VALIDATION_FAILED,
                details={
                    "runtime": "agent",
                    "input_model": AgentRunInput.__name__,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc
