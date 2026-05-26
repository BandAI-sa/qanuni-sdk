"""Per-run logging utilities for the deterministic legal agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel

from qanuni.agent.models import AgentPlan, AgentPlanStep, AgentRunInput, AgentRunResult


class AgentLogManager:
    """Create one dated log session for each agent planning or execution call.

    Args:
        enabled: Whether file logging is enabled.
        log_dir: Root directory where dated agent logs should be written.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, *, enabled: bool, log_dir: Path) -> None:
        """Store the logging configuration used for future agent sessions.

        Args:
            enabled: Whether file logging is enabled.
            log_dir: Root directory where dated agent logs should be written.

        Returns:
            None.

        Raises:
            None.
        """
        self._enabled: bool = enabled
        self._log_dir: Path = log_dir

    def start_session(self, *, operation: Literal["plan", "run", "arun"]) -> AgentLogSession:
        """Open a new log session for one agent operation.

        Args:
            operation: Agent operation name such as `plan`, `run`, or `arun`.

        Returns:
            A writable log session for the requested operation.

        Raises:
            None.
        """
        return AgentLogSession(
            enabled=self._enabled,
            log_dir=self._log_dir,
            operation=operation,
        )


class AgentLogSession:
    """Append concise structured log events for one agent operation.

    Args:
        enabled: Whether this session should write to disk.
        log_dir: Root directory where dated log files should be written.
        operation: Agent operation name such as `plan`, `run`, or `arun`.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        log_dir: Path,
        operation: Literal["plan", "run", "arun"],
    ) -> None:
        """Create one run-scoped log session with a dated file path.

        Args:
            enabled: Whether this session should write to disk.
            log_dir: Root directory where dated log files should be written.
            operation: Agent operation name such as `plan`, `run`, or `arun`.

        Returns:
            None.

        Raises:
            None.
        """
        self._enabled: bool = enabled
        self._operation: Literal["plan", "run", "arun"] = operation
        self._started_at: datetime = datetime.now(UTC)
        self._run_id: str = f"agent_{uuid4().hex[:12]}"
        self._lock: Lock = Lock()
        self._log_path: Path | None = None
        if self._enabled:
            date_dir: str = self._started_at.strftime("%Y%m%d")
            timestamp_label: str = self._started_at.strftime("%Y%m%d_%H%M%S_%fZ")
            self._log_path = (
                log_dir
                / date_dir
                / f"{operation}_{timestamp_label}_{self._run_id}.jsonl"
            )
            self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def run_id(self) -> str:
        """Return the stable identifier for this agent log session.

        Args:
            None.

        Returns:
            Stable agent-run identifier.

        Raises:
            None.
        """
        return self._run_id

    @property
    def log_path(self) -> Path | None:
        """Return the physical log path when file logging is enabled.

        Args:
            None.

        Returns:
            Log-file path, or `None` when file logging is disabled.

        Raises:
            None.
        """
        return self._log_path

    def log_request(self, request: AgentRunInput) -> None:
        """Persist a concise summary of the incoming agent request.

        Args:
            request: Normalized agent request supplied by the caller.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="INFO",
            event="request_received",
            message="استقبل الـ agent طلبًا جديدًا وبدأ تجهيز المسار.",
            details=self._summarize_request(request),
        )

    def log_plan(self, plan: AgentPlan) -> None:
        """Persist a concise summary of the selected deterministic plan.

        Args:
            plan: Deterministic plan selected by the planner.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="INFO",
            event="plan_selected",
            message="تم اختيار الخطة القانونية المعتمدة لهذا الطلب.",
            details=self._summarize_plan(plan),
        )

    def log_step_start(self, plan_step: AgentPlanStep, payload: dict[str, Any]) -> None:
        """Persist the start of one workflow capability execution step.

        Args:
            plan_step: Planned step about to be executed.
            payload: Prepared payload passed into the workflow.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="INFO",
            event="step_started",
            message=f"بدأ الـ agent تنفيذ الخطوة {plan_step.capability_id}.",
            details={
                "step_id": plan_step.step_id,
                "capability_id": plan_step.capability_id,
                "title": plan_step.title,
                "payload_summary": self._summarize_value(payload),
            },
        )

    def log_step_completed(self, plan_step: AgentPlanStep, result: BaseModel) -> None:
        """Persist one successfully completed workflow capability.

        Args:
            plan_step: Planned step that completed successfully.
            result: Workflow result model returned by the SDK.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="INFO",
            event="step_completed",
            message=f"اكتملت الخطوة {plan_step.capability_id} بنجاح.",
            details={
                "step_id": plan_step.step_id,
                "capability_id": plan_step.capability_id,
                "result_summary": self._summarize_result(result),
            },
        )

    def log_missing_inputs(self, plan_step: AgentPlanStep, missing_inputs: list[str]) -> None:
        """Persist a missing-input stopping condition for one step.

        Args:
            plan_step: Planned step that could not continue.
            missing_inputs: Canonical missing input names.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="WARNING",
            event="step_needs_more_information",
            message=f"توقفت الخطوة {plan_step.capability_id} لوجود بيانات ناقصة.",
            details={
                "step_id": plan_step.step_id,
                "capability_id": plan_step.capability_id,
                "missing_inputs": missing_inputs,
            },
        )

    def log_blocked_step(self, plan_step: AgentPlanStep, guardrail_message: str) -> None:
        """Persist a guardrail block raised for one step.

        Args:
            plan_step: Planned step blocked by a guardrail.
            guardrail_message: Human-readable explanation for the block.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="WARNING",
            event="step_blocked",
            message=f"تم حظر الخطوة {plan_step.capability_id} بواسطة guardrails.",
            details={
                "step_id": plan_step.step_id,
                "capability_id": plan_step.capability_id,
                "guardrail_message": guardrail_message,
            },
        )

    def log_run_completed(self, result: AgentRunResult) -> None:
        """Persist the terminal summary for one completed agent operation.

        Args:
            result: Final agent result returned to the caller.

        Returns:
            None.

        Raises:
            None.
        """
        self.log(
            level="INFO",
            event="run_completed",
            message="اكتمل تشغيل الـ agent ووصل إلى نتيجة نهائية.",
            details=self._summarize_run_result(result),
        )

    def log_exception(self, *, event: str, error: Exception) -> None:
        """Persist one runtime exception raised by the agent path.

        Args:
            event: Stable event name describing the failure point.
            error: Exception raised during planning or execution.

        Returns:
            None.

        Raises:
            None.
        """
        error_code: Any = getattr(error, "error_code", None)
        self.log(
            level="ERROR",
            event=event,
            message="فشل تشغيل الـ agent بسبب استثناء وقت التنفيذ.",
            details={
                "error_type": error.__class__.__name__,
                "error_message": str(error),
                "error_code": str(error_code) if error_code is not None else None,
            },
        )

    def log(
        self,
        *,
        level: Literal["INFO", "WARNING", "ERROR"],
        event: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append one structured log record to this session file.

        Args:
            level: Log severity label.
            event: Stable machine-readable event name.
            message: Human-readable Arabic message describing the event.
            details: Optional compact structured details.

        Returns:
            None.

        Raises:
            None.
        """
        if self._log_path is None:
            return
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": event,
            "message": message,
            "run_id": self._run_id,
            "operation": self._operation,
            "details": self._summarize_value(details or {}),
        }
        serialized: str = json.dumps(payload, ensure_ascii=False)
        try:
            with self._lock:
                with self._log_path.open("a", encoding="utf-8") as file_handle:
                    file_handle.write(serialized)
                    file_handle.write("\n")
        except OSError:
            return None

    @classmethod
    def _summarize_request(cls, request: AgentRunInput) -> dict[str, Any]:
        """Build a compact summary of one agent request.

        Args:
            request: Normalized agent request supplied by the caller.

        Returns:
            Compact JSON-safe request summary.

        Raises:
            None.
        """
        return {
            "goal": cls._truncate_text(request.goal, 280),
            "scenario_hint": request.scenario_hint.value if request.scenario_hint else None,
            "document_count": len(request.documents),
            "documents": [
                {
                    "name": document.name,
                    "document_type": document.document_type,
                    "role": document.role,
                    "file_path": document.file_path,
                    "text_length": len(document.text or ""),
                    "text_excerpt": cls._truncate_text(document.text, 180),
                }
                for document in request.documents[:4]
            ],
            "facts": cls._summarize_value(request.facts),
            "shared_runtime": (
                request.shared_runtime.model_dump(mode="json")
                if request.shared_runtime is not None
                else None
            ),
            "step_runtime_overrides": {
                key: value.model_dump(mode="json")
                for key, value in request.step_runtime_overrides.items()
            },
        }

    @classmethod
    def _summarize_plan(cls, plan: AgentPlan) -> dict[str, Any]:
        """Build a compact summary of one deterministic plan.

        Args:
            plan: Deterministic plan selected by the planner.

        Returns:
            Compact JSON-safe plan summary.

        Raises:
            None.
        """
        return {
            "scenario": plan.scenario.value if plan.scenario is not None else None,
            "status_hint": plan.status_hint,
            "plan_summary": cls._truncate_text(plan.plan_summary, 320),
            "steps": [
                {
                    "step_id": step.step_id,
                    "capability_id": step.capability_id,
                    "title": step.title,
                    "required_inputs": step.required_inputs,
                    "missing_inputs": step.missing_inputs,
                    "produced_entities": step.produced_entities,
                    "risk_domain": step.risk_domain,
                    "recommended_predecessors": step.recommended_predecessors,
                }
                for step in plan.steps
            ],
            "planning_notes": [cls._truncate_text(note, 240) for note in plan.planning_notes[:6]],
        }

    @classmethod
    def _summarize_result(cls, result: BaseModel) -> dict[str, Any]:
        """Build a compact summary of one workflow result.

        Args:
            result: Workflow result model returned by the SDK.

        Returns:
            Compact JSON-safe result summary.

        Raises:
            None.
        """
        workflow_state: Any = getattr(result, "state", None)
        generated_artifacts: dict[str, Any] = {}
        if workflow_state is not None and hasattr(workflow_state, "generated_artifacts"):
            generated_artifacts = getattr(workflow_state, "generated_artifacts", {}) or {}
        return {
            "result_model": result.__class__.__name__,
            "workflow_id": getattr(result, "workflow_id", None),
            "executive_summary": cls._truncate_text(
                getattr(result, "executive_summary", None),
                280,
            ),
            "tokens_used": getattr(result, "tokens_used", None),
            "model_used": getattr(result, "model_used", None),
            "estimated_cost_usd": getattr(result, "estimated_cost_usd", None),
            "generated_artifact_keys": sorted(generated_artifacts.keys()),
        }

    @classmethod
    def _summarize_run_result(cls, result: AgentRunResult) -> dict[str, Any]:
        """Build a compact summary of the final agent run result.

        Args:
            result: Final agent result returned to the caller.

        Returns:
            Compact JSON-safe terminal summary.

        Raises:
            None.
        """
        return {
            "status": result.status.value,
            "scenario": result.scenario.value if result.scenario is not None else None,
            "completed_capabilities": result.state.completed_capabilities,
            "missing_inputs": result.state.missing_inputs,
            "guardrail_messages": result.state.guardrail_messages,
            "generated_artifact_keys": sorted(result.state.generated_artifacts.keys()),
            "answer_excerpt": cls._truncate_text(result.answer_text, 500),
            "next_question": cls._truncate_text(result.next_question, 280),
            "log_path": str(result.log_path) if result.log_path is not None else None,
        }

    @classmethod
    def _summarize_value(
        cls,
        value: Any,
        *,
        max_depth: int = 3,
        max_items: int = 6,
    ) -> Any:
        """Reduce nested values into compact JSON-safe summaries.

        Args:
            value: Arbitrary Python value to summarize.
            max_depth: Maximum recursive nesting depth to preserve.
            max_items: Maximum list or dict items preserved at each level.

        Returns:
            Compact JSON-safe summary value.

        Raises:
            None.
        """
        return cls._summarize_value_inner(
            value,
            depth=0,
            max_depth=max_depth,
            max_items=max_items,
        )

    @classmethod
    def _summarize_value_inner(
        cls,
        value: Any,
        *,
        depth: int,
        max_depth: int,
        max_items: int,
    ) -> Any:
        """Implement recursive value summarization for log payloads.

        Args:
            value: Arbitrary Python value to summarize.
            depth: Current recursion depth.
            max_depth: Maximum recursive nesting depth to preserve.
            max_items: Maximum list or dict items preserved at each level.

        Returns:
            Compact JSON-safe summary value.

        Raises:
            None.
        """
        if isinstance(value, BaseModel):
            return cls._summarize_value_inner(
                value.model_dump(mode="json"),
                depth=depth,
                max_depth=max_depth,
                max_items=max_items,
            )
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return cls._truncate_text(value, 280)
        if depth >= max_depth:
            return cls._truncate_text(str(value), 280)
        if isinstance(value, dict):
            summarized_dict: dict[str, Any] = {}
            index: int
            key: Any
            nested_value: Any
            for index, (key, nested_value) in enumerate(value.items()):
                if index >= max_items:
                    summarized_dict["__truncated_items__"] = len(value) - max_items
                    break
                summarized_dict[str(key)] = cls._summarize_value_inner(
                    nested_value,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_items=max_items,
                )
            return summarized_dict
        if isinstance(value, (list, tuple, set)):
            summarized_list: list[Any] = [
                cls._summarize_value_inner(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_items=max_items,
                )
                for item in list(value)[:max_items]
            ]
            if len(value) > max_items:
                summarized_list.append({"__truncated_items__": len(value) - max_items})
            return summarized_list
        return cls._truncate_text(str(value), 280)

    @staticmethod
    def _truncate_text(text: str | None, limit: int) -> str | None:
        """Return one string unchanged or truncated with length metadata.

        Args:
            text: Input text value that may need truncation.
            limit: Maximum number of characters preserved before truncation.

        Returns:
            Original string, truncated string, or `None` when the input is `None`.

        Raises:
            None.
        """
        if text is None:
            return None
        if len(text) <= limit:
            return text
        return f"{text[:limit]}... [truncated {len(text) - limit} chars]"
