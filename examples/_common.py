"""Shared helpers for the human-testing example suite."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import atexit
import inspect
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any, Literal

from _bootstrap import ensure_project_root_on_path
from pydantic import BaseModel

ensure_project_root_on_path()

import qanuni
from qanuni import LegalClient
from qanuni.acceptance.documents import (
    list_sample_documents,
    load_sample_document,
    sample_document_path,
)
from qanuni.acceptance.runner import (
    AcceptanceArtifactPaths,
    build_acceptance_client,
    resolve_acceptance_artifact_paths,
)

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - fallback path only matters without tqdm installed
    tqdm = None

if TYPE_CHECKING:
    from qanuni.agent.models import AgentPlan, AgentRunResult, AgentState
    from qanuni.models.workflows import WorkflowState


@dataclass(frozen=True, slots=True)
class ExampleContext:
    """Collect shared runtime objects for one human-testing example.

    Args:
        title: Human-readable example title shown in the terminal output.
        mode: Whether the example uses the mocked provider or live OpenAI calls.
        working_dir: Root directory where artifacts are stored for the example run.
        artifact_paths: Resolved cache and observability locations for the example run.
        client: Configured Qanuni client used by the example.

    Returns:
        None.

    Raises:
        None.
    """

    title: str
    mode: Literal["mocked", "live"]
    working_dir: Path
    artifact_paths: AcceptanceArtifactPaths
    client: LegalClient
    cli_verbosity: Literal["silent", "simple", "full"]
    report_profile: Literal["full", "compact", "legal"]


@dataclass(slots=True)
class _OperationToken:
    """Track one in-flight CLI progress operation.

    Args:
        label: Stable label shown to the human tester.
        started_at: High-resolution timestamp for elapsed-time reporting.

    Returns:
        None.

    Raises:
        None.
    """

    label: str
    started_at: float


@dataclass(slots=True)
class _ExampleOutputSession:
    """Collect one example report and mirror simple progress to stderr.

    Args:
        mode: Example execution mode.
        cli_verbosity: Console-verbosity level for human-facing progress.

    Returns:
        None.

    Raises:
        None.
    """

    mode: Literal["mocked", "live"]
    cli_verbosity: Literal["silent", "simple", "full"]
    report_profile: Literal["full", "compact", "legal"] = "full"
    output_file: Path | None = None
    title: str | None = None
    sections: list[dict[str, Any]] = field(default_factory=list)
    _bar: Any = None
    _discovered_operations: int = 0
    _completed_operations: int = 0
    _active_stack: list[str] = field(default_factory=list)
    _flushed: bool = False

    def __post_init__(self) -> None:
        """Initialize mutable state and the optional tqdm progress bar.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        if self.cli_verbosity == "silent" or tqdm is None:
            self._bar = None
            return
        self._bar = tqdm(
            total=0,
            file=sys.stderr,
            dynamic_ncols=True,
            leave=True,
            unit="call",
            bar_format="{desc} | completed {n_fmt}/{total_fmt} | elapsed {elapsed}",
        )
        self._bar.set_description_str("qanuni example ready")
        self._bar.refresh()

    def set_title(self, title: str) -> None:
        """Bind a human-readable example title to this session.

        Args:
            title: Example title shown in CLI progress and stored in the final JSON report.

        Returns:
            None.

        Raises:
            None.
        """
        if self.title == title:
            return
        self.title = title
        if self.cli_verbosity != "silent":
            self._stderr_line(f"==> {title} [{self.mode}]")
        self._set_bar_description(title)

    def add_section(self, title: str, payload: Any) -> None:
        """Append one JSON-safe section to the final example report.

        Args:
            title: Human-readable section title.
            payload: JSON-serializable payload or object convertible through
                fallback stringification.

        Returns:
            None.

        Raises:
            TypeError: If the payload cannot be converted into a JSON-safe structure.
        """
        safe_payload: Any = _json_safe(payload)
        self.sections.append({"title": title, "payload": safe_payload})
        if self.cli_verbosity == "full":
            self._stderr_line(f"\n--- {title} ---")
            self._stderr_json(safe_payload)

    def start_operation(self, label: str) -> _OperationToken:
        """Register the beginning of one CLI-visible operation.

        Args:
            label: Human-readable operation label such as `workflow.contract_review`.

        Returns:
            Token later passed back into `complete_operation` or `fail_operation`.

        Raises:
            None.
        """
        token = _OperationToken(label=label, started_at=perf_counter())
        self._active_stack.append(label)
        self._discovered_operations += 1
        if self._bar is not None:
            self._bar.total = max(self._bar.total or 0, self._discovered_operations)
            self._set_bar_description(f"running {label}")
            self._bar.refresh()
        if self.cli_verbosity != "silent":
            self._stderr_line(f"--> {label}")
        return token

    def complete_operation(self, token: _OperationToken, *, detail: str | None = None) -> None:
        """Mark one CLI-visible operation as completed successfully.

        Args:
            token: Operation token returned by `start_operation`.
            detail: Optional compact detail appended to the completion line.

        Returns:
            None.

        Raises:
            None.
        """
        elapsed_seconds: float = perf_counter() - token.started_at
        self._completed_operations += 1
        if token.label in self._active_stack:
            self._active_stack.remove(token.label)
        if self._bar is not None:
            self._bar.update(1)
            self._set_bar_description(self._active_stack[-1] if self._active_stack else "idle")
            self._bar.refresh()
        suffix: str = f" | {detail}" if detail else ""
        if self.cli_verbosity != "silent":
            self._stderr_line(f"<-- {token.label} [{elapsed_seconds:.1f}s]{suffix}")

    def fail_operation(self, token: _OperationToken, *, detail: str) -> None:
        """Mark one CLI-visible operation as failed.

        Args:
            token: Operation token returned by `start_operation`.
            detail: Compact error detail shown to the human tester.

        Returns:
            None.

        Raises:
            None.
        """
        elapsed_seconds: float = perf_counter() - token.started_at
        if token.label in self._active_stack:
            self._active_stack.remove(token.label)
        self._set_bar_description(self._active_stack[-1] if self._active_stack else "failed")
        if self.cli_verbosity != "silent":
            self._stderr_line(f"<!! {token.label} [{elapsed_seconds:.1f}s] | {detail}")

    def flush_stdout_report(self) -> None:
        """Emit the final consolidated JSON report to stdout once.

        Args:
            None.

        Returns:
            None.

        Raises:
            OSError: If stdout cannot be written.
            TypeError: If the report cannot be serialized.
        """
        if self._flushed:
            return
        report_payload: dict[str, Any] = self._build_report_payload()
        if self.output_file is not None:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            self.output_file.write_text(
                json.dumps(report_payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        else:
            _write_json_stream(sys.stdout, report_payload)
        self._flushed = True
        if self._bar is not None:
            self._bar.close()

    def _build_report_payload(self) -> dict[str, Any]:
        """Build the final JSON payload according to the selected report profile.

        Args:
            None.

        Returns:
            Final JSON-ready report payload.

        Raises:
            None.
        """
        if self.report_profile == "compact":
            return self._build_compact_report()
        if self.report_profile == "legal":
            return self._build_legal_report()
        return {
            "title": self.title,
            "mode": self.mode,
            "cli_verbosity": self.cli_verbosity,
            "report_profile": self.report_profile,
            "sections": self.sections,
        }

    def _build_compact_report(self) -> dict[str, Any]:
        """Build a smaller technical summary from the collected full sections.

        Args:
            None.

        Returns:
            Compact JSON-ready report payload.

        Raises:
            None.
        """
        section_map = self._section_map()
        compact_report: dict[str, Any] = {
            "title": self.title,
            "mode": self.mode,
            "cli_verbosity": self.cli_verbosity,
            "report_profile": self.report_profile,
        }
        legal_brief: Any = section_map.get("Legal task brief")
        if isinstance(legal_brief, dict):
            compact_report["matter"] = {
                "difficulty": legal_brief.get("difficulty"),
                "legal_question": legal_brief.get("legal_question"),
                "scenario_hint": legal_brief.get("scenario_hint"),
                "documents": legal_brief.get("documents", []),
            }
        agent_plan: Any = section_map.get("Agent plan")
        if isinstance(agent_plan, dict):
            compact_report["plan"] = {
                "scenario": agent_plan.get("scenario"),
                "plan_summary": agent_plan.get("plan_summary"),
                "capabilities": [
                    {
                        "capability_id": step.get("capability_id"),
                        "title": step.get("title"),
                        "reason": step.get("reason"),
                    }
                    for step in agent_plan.get("steps", [])
                ],
            }
        agent_result_summary: Any = section_map.get("Agent result summary")
        if isinstance(agent_result_summary, dict):
            compact_report["outcome"] = {
                "status": agent_result_summary.get("status"),
                "scenario": agent_result_summary.get("scenario"),
                "completed_capabilities": agent_result_summary.get(
                    "completed_capabilities", []
                ),
                "missing_inputs": agent_result_summary.get("missing_inputs", []),
                "guardrail_messages": agent_result_summary.get("guardrail_messages", []),
                "generated_artifacts": sorted(
                    (agent_result_summary.get("generated_artifacts") or {}).keys()
                ),
            }
        final_answer: Any = section_map.get("Agent final Arabic answer")
        if isinstance(final_answer, dict):
            compact_report["final_answer"] = final_answer.get("answer_text")

        compact_report["workflows"] = self._compact_workflow_summaries(section_map)
        compact_report["key_findings"] = self._extract_key_findings(section_map)
        compact_report["recommended_actions"] = self._extract_recommended_actions(section_map)
        compact_report["generated_documents"] = self._extract_generated_artifacts(section_map)
        compact_report["observability_summary"] = self._summarize_observability(section_map)
        compact_report["section_titles"] = [section["title"] for section in self.sections]
        return compact_report

    def _build_legal_report(self) -> dict[str, Any]:
        """Build a legal-facing brief for non-technical reviewers.

        Args:
            None.

        Returns:
            Concise legal JSON-ready report payload.

        Raises:
            None.
        """
        section_map = self._section_map()
        legal_brief: Any = section_map.get("Legal task brief")
        agent_plan: Any = section_map.get("Agent plan")
        agent_result_summary: Any = section_map.get("Agent result summary")
        final_answer: Any = section_map.get("Agent final Arabic answer")

        report: dict[str, Any] = {
            "title": self.title,
            "audience": "legal_non_technical",
            "mode": self.mode,
            "report_profile": self.report_profile,
            "matter": {
                "difficulty": (
                    legal_brief.get("difficulty") if isinstance(legal_brief, dict) else None
                ),
                "legal_question": (
                    legal_brief.get("legal_question") if isinstance(legal_brief, dict) else None
                ),
                "documents": (
                    legal_brief.get("documents", []) if isinstance(legal_brief, dict) else []
                ),
                "facts": self._shrink_facts(legal_brief.get("facts", {}))
                if isinstance(legal_brief, dict)
                else {},
            },
            "agent_plan": {
                "scenario": agent_plan.get("scenario") if isinstance(agent_plan, dict) else None,
                "plan_summary": agent_plan.get("plan_summary")
                if isinstance(agent_plan, dict)
                else None,
                "steps": self._legal_plan_steps(agent_plan.get("steps", []))
                if isinstance(agent_plan, dict)
                else [],
            },
            "result": {
                "status": agent_result_summary.get("status")
                if isinstance(agent_result_summary, dict)
                else None,
                "completed_capabilities": agent_result_summary.get(
                    "completed_capabilities", []
                )
                if isinstance(agent_result_summary, dict)
                else [],
                "final_answer": final_answer.get("answer_text")
                if isinstance(final_answer, dict)
                else None,
                "missing_inputs": agent_result_summary.get("missing_inputs", [])
                if isinstance(agent_result_summary, dict)
                else [],
                "guardrail_messages": agent_result_summary.get("guardrail_messages", [])
                if isinstance(agent_result_summary, dict)
                else [],
            },
            "what_agent_did": self._compact_execution_flow(section_map),
            "key_findings": self._extract_key_findings(section_map, limit=8),
            "recommended_actions": self._extract_recommended_actions(section_map, limit=8),
            "generated_documents": self._extract_generated_artifacts(
                section_map,
                excerpt_length=900,
            ),
        }
        next_question = self._extract_next_question(section_map)
        if next_question:
            report["result"]["next_question"] = next_question
        return report

    def _section_map(self) -> dict[str, Any]:
        """Map section titles to their payloads for easier report shaping.

        Args:
            None.

        Returns:
            Dictionary keyed by section title.

        Raises:
            None.
        """
        return {section["title"]: section["payload"] for section in self.sections}

    def _compact_workflow_summaries(self, section_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Build short workflow summaries from either agent or workflow sections.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            List of compact workflow summaries.

        Raises:
            None.
        """
        summaries: list[dict[str, Any]] = []
        agent_run_payload: Any = section_map.get("Agent run result payload")
        if isinstance(agent_run_payload, dict):
            execution_steps = (agent_run_payload.get("state") or {}).get("execution_steps", [])
            for step in execution_steps:
                summaries.append(
                    {
                        "capability_id": step.get("capability_id"),
                        "title": step.get("title"),
                        "status": step.get("status"),
                        "summary": step.get("summary"),
                    }
                )
            return summaries

        workflow_state_payload: Any = section_map.get("Workflow state payload")
        if isinstance(workflow_state_payload, dict):
            summaries.append(
                {
                    "workflow_id": workflow_state_payload.get("workflow_id"),
                    "status": "completed",
                    "summary": self._first_non_empty(
                        [
                            workflow_state_payload.get("executive_summary"),
                            self._join_step_summaries(workflow_state_payload.get("steps", [])),
                        ]
                    ),
                    "step_count": len(workflow_state_payload.get("steps", [])),
                }
            )
        return summaries

    def _compact_execution_flow(self, section_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Build a legal-friendly step-by-step summary of what the agent executed.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            List of concise execution-step summaries.

        Raises:
            None.
        """
        flow: list[dict[str, Any]] = []
        agent_run_payload: Any = section_map.get("Agent run result payload")
        if not isinstance(agent_run_payload, dict):
            return flow
        execution_steps = (agent_run_payload.get("state") or {}).get("execution_steps", [])
        for index, step in enumerate(execution_steps, start=1):
            flow.append(
                {
                    "order": index,
                    "capability": step.get("capability_id"),
                    "title": step.get("title"),
                    "summary": step.get("summary"),
                }
            )
        return flow

    def _extract_key_findings(
        self,
        section_map: dict[str, Any],
        *,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        """Extract the highest-signal findings from agent or workflow state.

        Args:
            section_map: Section-title mapping for the current example.
            limit: Maximum number of findings returned.

        Returns:
            List of concise findings.

        Raises:
            None.
        """
        findings = self._state_findings(section_map)
        return [
            {
                "severity": finding.get("severity"),
                "title": finding.get("title"),
                "summary": finding.get("summary"),
                "recommendation": finding.get("recommendation"),
            }
            for finding in findings[:limit]
        ]

    def _extract_recommended_actions(
        self,
        section_map: dict[str, Any],
        *,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        """Extract top recommended actions from agent or workflow state.

        Args:
            section_map: Section-title mapping for the current example.
            limit: Maximum number of actions returned.

        Returns:
            List of concise recommended actions.

        Raises:
            None.
        """
        actions = self._state_actions(section_map)
        return [
            {
                "priority": action.get("priority"),
                "title": action.get("title"),
                "description": action.get("description"),
            }
            for action in actions[:limit]
        ]

    def _extract_generated_artifacts(
        self,
        section_map: dict[str, Any],
        *,
        excerpt_length: int = 500,
    ) -> list[dict[str, Any]]:
        """Extract generated document artifacts with short excerpts.

        Args:
            section_map: Section-title mapping for the current example.
            excerpt_length: Maximum number of characters kept per artifact excerpt.

        Returns:
            List of generated-artifact summaries.

        Raises:
            None.
        """
        artifacts = self._state_generated_artifacts(section_map)
        return [
            {
                "name": name,
                "excerpt": text[:excerpt_length],
            }
            for name, text in artifacts.items()
        ]

    def _summarize_observability(self, section_map: dict[str, Any]) -> dict[str, Any]:
        """Build a small observability summary without dumping raw event payloads.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            Compact observability summary.

        Raises:
            None.
        """
        events = section_map.get("Observability events", [])
        if not isinstance(events, list):
            return {}
        tool_calls = [event for event in events if event.get("scope_type") == "tool"]
        workflow_calls = [event for event in events if event.get("scope_type") == "workflow"]
        return {
            "tool_calls": len(tool_calls),
            "workflow_calls": len(workflow_calls),
            "failed_calls": len([event for event in events if event.get("status") == "failure"]),
            "total_tokens": sum(int(event.get("total_tokens") or 0) for event in events),
            "total_latency_ms": sum(int(event.get("latency_ms") or 0) for event in events),
        }

    @staticmethod
    def _legal_plan_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert raw plan steps into a legal-friendly summary shape.

        Args:
            steps: Raw plan-step payloads.

        Returns:
            List of concise plan-step summaries.

        Raises:
            None.
        """
        return [
            {
                "order": index,
                "capability": step.get("capability_id"),
                "title": step.get("title"),
                "reason": step.get("reason"),
            }
            for index, step in enumerate(steps, start=1)
        ]

    @staticmethod
    def _shrink_facts(facts: dict[str, Any]) -> dict[str, Any]:
        """Keep only human-readable fact values in a compact structure.

        Args:
            facts: Full fact payload supplied to the example.

        Returns:
            Compact fact dictionary safe for legal-facing reports.

        Raises:
            None.
        """
        compact_facts: dict[str, Any] = {}
        fact_key: str
        fact_value: Any
        for fact_key, fact_value in facts.items():
            if isinstance(fact_value, (str, int, float, bool)) or fact_value is None:
                compact_facts[fact_key] = fact_value
                continue
            if isinstance(fact_value, dict):
                compact_facts[fact_key] = {
                    nested_key: nested_value
                    for nested_key, nested_value in fact_value.items()
                    if isinstance(nested_value, (str, int, float, bool)) or nested_value is None
                }
        return compact_facts

    @staticmethod
    def _join_step_summaries(steps: list[dict[str, Any]]) -> str | None:
        """Join the first few workflow step summaries into one concise sentence.

        Args:
            steps: Raw workflow-step payloads.

        Returns:
            Concise joined step summary, or `None` if unavailable.

        Raises:
            None.
        """
        summaries = [step.get("summary") for step in steps if isinstance(step.get("summary"), str)]
        if not summaries:
            return None
        return " | ".join(summaries[:3])

    @staticmethod
    def _first_non_empty(values: list[Any]) -> Any:
        """Return the first truthy value from a candidate list.

        Args:
            values: Candidate values in preference order.

        Returns:
            First truthy value, or `None` when every candidate is empty.

        Raises:
            None.
        """
        value: Any
        for value in values:
            if value:
                return value
        return None

    @staticmethod
    def _extract_next_question(section_map: dict[str, Any]) -> str | None:
        """Extract the next clarifying question from the final agent payload when present.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            Next question string, or `None`.

        Raises:
            None.
        """
        agent_run_payload: Any = section_map.get("Agent run result payload")
        if not isinstance(agent_run_payload, dict):
            return None
        next_question: Any = agent_run_payload.get("next_question")
        return next_question if isinstance(next_question, str) and next_question else None

    def _state_findings(self, section_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract findings from the richest available state payload.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            List of finding dictionaries.

        Raises:
            None.
        """
        agent_run_payload: Any = section_map.get("Agent run result payload")
        if isinstance(agent_run_payload, dict):
            state = agent_run_payload.get("state") or {}
            findings = state.get("findings")
            if isinstance(findings, list) and findings:
                return findings
            workflow_states = state.get("workflow_states") or {}
            return self._aggregate_workflow_state_items(workflow_states, "findings")
        workflow_state_payload: Any = section_map.get("Workflow state payload")
        if isinstance(workflow_state_payload, dict):
            findings = workflow_state_payload.get("findings")
            if isinstance(findings, list):
                return findings
        return []

    def _state_actions(self, section_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract recommended actions from the richest available state payload.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            List of action dictionaries.

        Raises:
            None.
        """
        agent_run_payload: Any = section_map.get("Agent run result payload")
        if isinstance(agent_run_payload, dict):
            state = agent_run_payload.get("state") or {}
            actions = state.get("recommended_actions")
            if isinstance(actions, list) and actions:
                return actions
            workflow_states = state.get("workflow_states") or {}
            return self._aggregate_workflow_state_items(
                workflow_states,
                "recommended_actions",
            )
        workflow_state_payload: Any = section_map.get("Workflow state payload")
        if isinstance(workflow_state_payload, dict):
            actions = workflow_state_payload.get("recommended_actions")
            if isinstance(actions, list):
                return actions
        return []

    def _state_generated_artifacts(self, section_map: dict[str, Any]) -> dict[str, str]:
        """Extract generated text artifacts from the richest available state payload.

        Args:
            section_map: Section-title mapping for the current example.

        Returns:
            Mapping of artifact names to generated text.

        Raises:
            None.
        """
        agent_run_payload: Any = section_map.get("Agent run result payload")
        if isinstance(agent_run_payload, dict):
            state = agent_run_payload.get("state") or {}
            artifacts = state.get("generated_artifacts")
            if isinstance(artifacts, dict) and artifacts:
                return {str(key): str(value) for key, value in artifacts.items()}
            workflow_states = state.get("workflow_states") or {}
            return self._aggregate_generated_artifacts(workflow_states)
        workflow_state_payload: Any = section_map.get("Workflow state payload")
        if isinstance(workflow_state_payload, dict):
            artifacts = workflow_state_payload.get("generated_artifacts")
            if isinstance(artifacts, dict):
                return {str(key): str(value) for key, value in artifacts.items()}
        return {}

    @staticmethod
    def _aggregate_workflow_state_items(
        workflow_states: dict[str, Any],
        key: str,
    ) -> list[dict[str, Any]]:
        """Flatten one list field from every captured workflow state.

        Args:
            workflow_states: Raw workflow-state mapping stored inside an agent run.
            key: Name of the list field to collect from each workflow state.

        Returns:
            Flattened list of dictionary items from every workflow state.

        Raises:
            None.
        """
        aggregated: list[dict[str, Any]] = []
        workflow_state: Any
        for workflow_state in workflow_states.values():
            if not isinstance(workflow_state, dict):
                continue
            items: Any = workflow_state.get(key)
            if not isinstance(items, list):
                continue
            aggregated.extend(item for item in items if isinstance(item, dict))
        return aggregated

    @staticmethod
    def _aggregate_generated_artifacts(workflow_states: dict[str, Any]) -> dict[str, str]:
        """Merge generated-text artifacts from every captured workflow state.

        Args:
            workflow_states: Raw workflow-state mapping stored inside an agent run.

        Returns:
            Combined generated-artifact mapping.

        Raises:
            None.
        """
        aggregated: dict[str, str] = {}
        workflow_id: str
        workflow_state: Any
        for workflow_id, workflow_state in workflow_states.items():
            if not isinstance(workflow_state, dict):
                continue
            artifacts: Any = workflow_state.get("generated_artifacts")
            if not isinstance(artifacts, dict):
                continue
            artifact_name: Any
            artifact_value: Any
            for artifact_name, artifact_value in artifacts.items():
                aggregated[f"{workflow_id}:{artifact_name}"] = str(artifact_value)
        return aggregated

    def attach_client_hooks(self, client: LegalClient) -> None:
        """Wrap public namespace entrypoints so examples expose live progress.

        Args:
            client: Configured SDK client whose public namespaces should be wrapped.

        Returns:
            None.

        Raises:
            None.
        """
        self._wrap_namespace(
            client.agent,
            namespace_label="agent",
            method_names=("plan", "run", "arun"),
        )
        namespace_label: str
        for namespace_label in (
            "labor",
            "contracts",
            "compliance",
            "drafting",
            "legal",
            "policies",
            "workflow",
        ):
            namespace_object: Any = getattr(client, namespace_label)
            self._wrap_namespace(namespace_object, namespace_label=namespace_label)

    def _wrap_namespace(
        self,
        namespace_object: Any,
        *,
        namespace_label: str,
        method_names: tuple[str, ...] | None = None,
    ) -> None:
        """Wrap selected public callables on one namespace object.

        Args:
            namespace_object: Namespace instance whose methods should be wrapped.
            namespace_label: Stable prefix shown in CLI progress output.
            method_names: Optional explicit method allow-list.

        Returns:
            None.

        Raises:
            None.
        """
        attribute_name: str
        if method_names is None:
            candidate_names: list[str] = [
                name for name in dir(namespace_object) if not name.startswith("_")
            ]
        else:
            candidate_names = list(method_names)
        for attribute_name in candidate_names:
            original_callable: Any = getattr(namespace_object, attribute_name, None)
            if original_callable is None or not callable(original_callable):
                continue
            if getattr(original_callable, "__qanuni_cli_wrapped__", False):
                continue
            wrapped_callable: Callable[..., Any] = self._build_wrapper(
                label=f"{namespace_label}.{attribute_name}",
                original_callable=original_callable,
            )
            setattr(namespace_object, attribute_name, wrapped_callable)

    def _build_wrapper(
        self,
        *,
        label: str,
        original_callable: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Create one progress-aware sync wrapper around a callable.

        Args:
            label: Stable progress label shown to the human tester.
            original_callable: Callable being wrapped.

        Returns:
            Wrapped callable that reports start, success, and failure.

        Raises:
            None.
        """

        if inspect.iscoroutinefunction(original_callable):

            @wraps(original_callable)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                token: _OperationToken = self.start_operation(label)
                try:
                    result: Any = await original_callable(*args, **kwargs)
                except Exception as exc:
                    self.fail_operation(token, detail=_compact_error_label(exc))
                    raise
                self.complete_operation(token, detail=_compact_result_label(result))
                return result

            async_wrapper.__qanuni_cli_wrapped__ = True
            return async_wrapper

        @wraps(original_callable)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            token: _OperationToken = self.start_operation(label)
            try:
                result: Any = original_callable(*args, **kwargs)
            except Exception as exc:
                self.fail_operation(token, detail=_compact_error_label(exc))
                raise
            self.complete_operation(token, detail=_compact_result_label(result))
            return result

        wrapper.__qanuni_cli_wrapped__ = True
        return wrapper

    def _stderr_line(self, text: str) -> None:
        """Write one human-facing progress line to stderr safely.

        Args:
            text: Text line written to stderr.

        Returns:
            None.

        Raises:
            OSError: If stderr cannot be written.
        """
        _write_line_stream(sys.stderr, text)

    def _stderr_json(self, payload: Any) -> None:
        """Write one JSON payload to stderr safely.

        Args:
            payload: JSON-safe payload written to stderr.

        Returns:
            None.

        Raises:
            OSError: If stderr cannot be written.
            TypeError: If the payload cannot be serialized.
        """
        _write_json_stream(sys.stderr, payload)

    def _set_bar_description(self, description: str) -> None:
        """Refresh the tqdm description when the progress bar is enabled.

        Args:
            description: Short current status description.

        Returns:
            None.

        Raises:
            None.
        """
        if self._bar is None:
            return
        self._bar.set_description_str(description)


_ACTIVE_OUTPUT_SESSION: _ExampleOutputSession | None = None


def _activate_output_session(
    *,
    mode: Literal["mocked", "live"],
    cli_verbosity: Literal["silent", "simple", "full"],
    report_profile: Literal["full", "compact", "legal"] = "full",
    output_file: Path | None = None,
) -> _ExampleOutputSession:
    """Create or reuse the singleton output session for the current example process.

    Args:
        mode: Example execution mode.
        cli_verbosity: Human-facing CLI verbosity level.

    Returns:
        The active output session for the current example process.

    Raises:
        None.
    """
    global _ACTIVE_OUTPUT_SESSION
    if _ACTIVE_OUTPUT_SESSION is None:
        _ACTIVE_OUTPUT_SESSION = _ExampleOutputSession(
            mode=mode,
            cli_verbosity=cli_verbosity,
            report_profile=report_profile,
            output_file=output_file,
        )
        atexit.register(_flush_active_output_session)
    return _ACTIVE_OUTPUT_SESSION


def _require_output_session() -> _ExampleOutputSession:
    """Return the active output session or create a safe default one.

    Args:
        None.

    Returns:
        The active output session.

    Raises:
        None.
    """
    if _ACTIVE_OUTPUT_SESSION is None:
        return _activate_output_session(mode="mocked", cli_verbosity="simple")
    return _ACTIVE_OUTPUT_SESSION


def _flush_active_output_session() -> None:
    """Emit the final stdout JSON report if an output session is active.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    if _ACTIVE_OUTPUT_SESSION is None:
        return
    _ACTIVE_OUTPUT_SESSION.flush_stdout_report()


def _compact_result_label(result: Any) -> str:
    """Build a short human-facing summary for one completed operation.

    Args:
        result: Returned value produced by a wrapped SDK call.

    Returns:
        Compact one-line summary suitable for stderr progress output.

    Raises:
        None.
    """
    if hasattr(result, "status") and hasattr(result, "scenario"):
        status: Any = getattr(result, "status", None)
        scenario: Any = getattr(result, "scenario", None)
        return f"status={status} scenario={scenario}"
    if hasattr(result, "workflow_id") and hasattr(result, "steps"):
        step_count: int = len(getattr(result, "steps", []))
        return f"workflow_id={getattr(result, 'workflow_id', None)} steps={step_count}"
    summary: Any = getattr(result, "summary", None)
    if isinstance(summary, str) and summary:
        return summary[:120]
    tokens_used: Any = getattr(result, "tokens_used", None)
    execution_time_ms: Any = getattr(result, "execution_time_ms", None)
    details: list[str] = []
    if tokens_used is not None:
        details.append(f"tokens={tokens_used}")
    if execution_time_ms is not None:
        details.append(f"latency_ms={execution_time_ms}")
    return " | ".join(details) if details else result.__class__.__name__


def _compact_error_label(error: Exception) -> str:
    """Build a short human-facing error label for stderr progress output.

    Args:
        error: Exception raised during one wrapped SDK call.

    Returns:
        Compact one-line error label.

    Raises:
        None.
    """
    error_code: Any = getattr(error, "error_code", None)
    if error_code is not None:
        return f"{error.__class__.__name__} {error_code}"
    return error.__class__.__name__


def parse_standard_args(description: str) -> argparse.Namespace:
    """Parse the standard CLI arguments shared by the example scripts.

    Args:
        description: Human-readable script description shown by `--help`.

    Returns:
        Parsed command-line namespace.

    Raises:
        SystemExit: If argument parsing fails.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--mode",
        choices=("mocked", "live"),
        default="mocked",
        help="Whether to run the example with deterministic mocked outputs or live OpenAI calls.",
    )
    parser.add_argument(
        "--working-dir",
        help="Optional working directory for cache, observability, and MCP artifacts.",
    )
    parser.add_argument(
        "--cli-verbosity",
        choices=("silent", "simple", "full"),
        default="simple",
        help=(
            "How much live progress to show on stderr while stdout remains a final JSON report."
        ),
    )
    parser.add_argument(
        "--output-file",
        help="Optional UTF-8 JSON file written directly by the example runner.",
    )
    parser.add_argument(
        "--report-profile",
        choices=("full", "compact", "legal"),
        default="full",
        help=(
            "Shape of the final JSON report: full raw details, compact summary, "
            "or a legal-facing brief."
        ),
    )
    args = parser.parse_args()
    _activate_output_session(
        mode=args.mode,
        cli_verbosity=args.cli_verbosity,
        report_profile=args.report_profile,
        output_file=Path(args.output_file).resolve() if args.output_file else None,
    )
    return args


def build_context(*, title: str, args: argparse.Namespace) -> ExampleContext:
    """Build the shared runtime context for one human-testing example.

    Args:
        title: Human-readable title shown in the terminal output.
        args: Parsed command-line arguments produced by `parse_standard_args`.

    Returns:
        Fully initialized example context.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
        OSError: If the selected working directory cannot be created.
    """
    working_dir = (
        Path(args.working_dir)
        if getattr(args, "working_dir", None)
        else Path(tempfile.mkdtemp(prefix="qanuni-human-example-"))
    )
    artifact_paths = resolve_acceptance_artifact_paths(working_dir)
    client = build_acceptance_client(
        mode=args.mode,
        cache_enabled=True,
        observability_persist=True,
        working_dir=artifact_paths.root_dir,
    )
    output_session: _ExampleOutputSession = _require_output_session()
    output_session.set_title(title)
    output_session.attach_client_hooks(client)
    return ExampleContext(
        title=title,
        mode=args.mode,
        working_dir=artifact_paths.root_dir,
        artifact_paths=artifact_paths,
        client=client,
        cli_verbosity=args.cli_verbosity,
        report_profile=args.report_profile,
    )


def emit_header(title: str) -> None:
    """Print a visible section header.

    Args:
        title: Text shown inside the header.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    output_session: _ExampleOutputSession = _require_output_session()
    output_session.set_title(title)
    if output_session.cli_verbosity != "full":
        return
    rule = "=" * 88
    _write_line_stream(sys.stderr, rule)
    _write_line_stream(sys.stderr, title)
    _write_line_stream(sys.stderr, rule)


def emit_environment(context: ExampleContext) -> None:
    """Print the runtime environment details for one example.

    Args:
        context: Example runtime context to describe.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_header(context.title)
    emit_json(
        "Environment",
        {
            "mode": context.mode,
            "qanuni_version": qanuni.__version__,
            "qanuni_import_path": qanuni.__file__,
            "working_dir": str(context.working_dir),
            "artifact_paths": context.artifact_paths.as_json(),
        },
    )


def emit_sample_document_index() -> None:
    """Print the packaged sample documents used by the example suite.

    Args:
        None.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_json(
        "Packaged sample documents",
        [
            {"name": name, "path": str(sample_document_path(name))}
            for name in list_sample_documents()
        ],
    )


def emit_document_excerpt(name: str, *, length: int = 360) -> None:
    """Print a short excerpt from one packaged sample document.

    Args:
        name: Packaged sample-document file name.
        length: Maximum number of characters to print.

    Returns:
        None.

    Raises:
        FileNotFoundError: If the requested sample document does not exist.
    """
    document_text = load_sample_document(name)
    emit_json(
        f"Document excerpt: {name}",
        {
            "path": str(sample_document_path(name)),
            "excerpt": document_text[:length],
        },
    )


def emit_tool_catalog(client: LegalClient, *, namespace: str | None = None) -> None:
    """Print the shipped tool metadata for one namespace or for the whole SDK.

    Args:
        client: Qanuni client used to query the catalog.
        namespace: Optional namespace filter such as `legal` or `contracts`.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    tool_records = client.list_tools(namespace=namespace)
    emit_json(
        f"Tool catalog{' for ' + namespace if namespace else ''}",
        [
            {
                "tool_id": record.tool_id,
                "namespace": record.namespace,
                "category": record.category,
                "implementation": record.implementation,
                "description": record.description,
            }
            for record in tool_records
        ],
    )


def emit_model(title: str, model: BaseModel) -> None:
    """Print one structured Pydantic model as JSON.

    Args:
        title: Human-readable section title.
        model: Pydantic model instance to serialize.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
        TypeError: If the model cannot be serialized.
    """
    emit_json(title, model.model_dump(mode="json"))


def emit_workflow_state(state: WorkflowState) -> None:
    """Print a workflow state both as a step summary and as full JSON.

    Args:
        state: Workflow state returned by one orchestrated workflow.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_json(
        "Workflow step summary",
        [
            {
                "step_id": step.step_id,
                "title": step.title,
                "status": step.status,
                "tool_id": step.tool_id,
                "summary": step.summary,
            }
            for step in state.steps
        ],
    )
    emit_json("Workflow state payload", state.model_dump(mode="json"))


def emit_agent_plan(plan: AgentPlan) -> None:
    """Print the selected deterministic agent plan.

    Args:
        plan: Agent plan produced by `client.agent.plan(...)`.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_json("Agent plan", plan.model_dump(mode="json"))


def emit_agent_state(state: AgentState) -> None:
    """Print the aggregated deterministic agent state.

    Args:
        state: Agent state returned by `client.agent.run(...)`.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_json(
        "Agent execution steps",
        [step.model_dump(mode="json") for step in state.execution_steps],
    )
    emit_json("Agent state payload", state.model_dump(mode="json"))


def emit_legal_task_brief(
    *,
    difficulty: Literal["easy", "medium", "hard", "complex"],
    legal_question: str,
    scenario_hint: str | None,
    documents: list[dict[str, Any]],
    facts: dict[str, Any],
    what_to_watch: list[str],
    acceptance_criteria: list[str],
) -> None:
    """Print a human-readable legal-task brief before running the agent.

    Args:
        difficulty: Relative difficulty label for the legal scenario.
        legal_question: Main legal objective the tester wants the agent to solve.
        scenario_hint: Optional deterministic scenario hint passed to the planner.
        documents: Document descriptors supplied to the agent runtime.
        facts: Fact payload supplied alongside the documents.
        what_to_watch: Behaviors the tester should inspect while the run executes.
        acceptance_criteria: High-level success criteria for the scenario.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_json(
        "Legal task brief",
        {
            "difficulty": difficulty,
            "legal_question": legal_question,
            "scenario_hint": scenario_hint,
            "documents": documents,
            "facts": facts,
            "what_to_watch": what_to_watch,
            "acceptance_criteria": acceptance_criteria,
        },
    )


def emit_agent_result_summary(result: AgentRunResult) -> None:
    """Print the terminal outcome of one agent run in a compact summary.

    Args:
        result: Full deterministic agent result returned by `client.agent.run(...)`.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    emit_json(
        "Agent result summary",
        {
            "status": result.status,
            "scenario": result.scenario,
            "next_question": result.next_question,
            "completed_capabilities": result.state.completed_capabilities,
            "missing_inputs": result.state.missing_inputs,
            "guardrail_messages": result.state.guardrail_messages,
            "generated_artifacts": result.state.generated_artifacts,
        },
    )
    emit_json("Agent final Arabic answer", {"answer_text": result.answer_text})


def emit_agent_workflow_breakdown(state: AgentState) -> None:
    """Print each workflow state captured inside the aggregated agent state.

    Args:
        state: Agent state returned by `client.agent.run(...)`.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    workflow_id: str
    workflow_state: WorkflowState
    for workflow_id, workflow_state in state.workflow_states.items():
        emit_json(
            f"Workflow breakdown: {workflow_id}",
            {
                "workflow_id": workflow_state.workflow_id,
                "model_used": workflow_state.model_used,
                "tokens_used": workflow_state.tokens_used,
                "estimated_cost_usd": workflow_state.estimated_cost_usd,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "title": step.title,
                        "tool_id": step.tool_id,
                        "status": step.status,
                        "summary": step.summary,
                    }
                    for step in workflow_state.steps
                ],
                "step_output_keys": sorted(workflow_state.step_outputs.keys()),
                "findings_count": len(workflow_state.findings),
                "recommended_actions_count": len(workflow_state.recommended_actions),
                "generated_artifacts": workflow_state.generated_artifacts,
            },
        )


def emit_observability(context: ExampleContext) -> None:
    """Print runtime observability events and the persisted log location.

    Args:
        context: Example runtime context that owns the observability recorder.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    events = [
        _json_safe(event.model_dump(mode="python"))
        for event in context.client.observability.snapshot()
    ]
    emit_json("Observability events", events)
    log_path = context.artifact_paths.observability_log_path
    emit_json(
        "Observability artifact",
        {
            "path": str(log_path),
            "exists": log_path.exists(),
            "excerpt": log_path.read_text(encoding="utf-8")[:1200]
            if log_path.exists()
            else "",
        },
    )


def emit_json(title: str, payload: Any) -> None:
    """Print one labeled JSON payload.

    Args:
        title: Human-readable section title.
        payload: JSON-serializable object to print.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
        TypeError: If the payload cannot be serialized.
    """
    _require_output_session().add_section(title, payload)

def _write_json_stream(stream: Any, payload: Any) -> None:
    """Serialize and write one payload to a specific stream safely.

    Args:
        stream: Text or binary stream that receives the serialized payload.
        payload: JSON-serializable object to print.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
        TypeError: If the payload cannot be serialized.
    """
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if hasattr(stream, "buffer"):
        stream.buffer.write(rendered.encode("utf-8"))
        stream.buffer.write(b"\n")
        return
    stream.write(rendered)
    stream.write("\n")


def _json_safe(payload: Any) -> Any:
    """Convert a Python object into a JSON-safe structure.

    Args:
        payload: Arbitrary Python object.

    Returns:
        JSON-safe representation of the supplied object.

    Raises:
        TypeError: If the payload cannot be serialized even with fallback string conversion.
    """
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))


def _write_line_stream(stream: Any, text: str) -> None:
    """Write one line to a stream with UTF-8-safe behavior on Windows terminals.

    Args:
        stream: Text or binary stream that receives the line.
        text: Text line to write.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
    """
    if hasattr(stream, "buffer"):
        stream.buffer.write(text.encode("utf-8"))
        stream.buffer.write(b"\n")
        return
    stream.write(text)
    stream.write("\n")
