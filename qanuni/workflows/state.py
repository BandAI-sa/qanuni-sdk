"""State builder for multi-step workflow orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qanuni.models.common import BaseResult
from qanuni.models.contracts import ContractRiskScoreResult
from qanuni.models.legal import (
    AmountExtractionResult,
    ClauseExtractionResult,
    DateExtractionResult,
    DisputeResolutionExtractionResult,
    DocumentTypeClassificationResult,
    ObligationExtractionResult,
    TerminationTermExtractionResult,
)
from qanuni.models.workflows import WorkflowState, WorkflowStep


class WorkflowStateBuilder:
    """Accumulate a unified workflow state from multiple tool executions.

    Args:
        workflow_id: Stable workflow identifier for the current orchestration run.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, workflow_id: str) -> None:
        """Initialize an empty workflow state for a new orchestration run.

        Args:
            workflow_id: Stable workflow identifier for the current orchestration run.

        Returns:
            None.

        Raises:
            None.
        """
        self._state = WorkflowState(workflow_id=workflow_id)

    def add_result_step(
        self,
        *,
        step_id: str,
        title: str,
        result: BaseResult,
        summary: str,
    ) -> None:
        """Record one completed tool-backed workflow step and absorb its artifacts.

        Args:
            step_id: Stable step identifier unique within the workflow.
            title: Human-readable workflow step title.
            result: Structured tool result produced by the step.
            summary: Short operational summary of what the step contributed.

        Returns:
            None.

        Raises:
            None.
        """
        self._state.steps.append(
            WorkflowStep(
                step_id=step_id,
                title=title,
                tool_id=result.tool_id or None,
                status="completed",
                summary=summary,
                output_model=result.__class__.__name__,
                output_payload=result.model_dump(mode="json"),
            )
        )
        self._state.step_outputs[step_id] = result.model_dump(mode="json")
        self._absorb_result(result)

    def add_synthesis_step(
        self,
        *,
        step_id: str,
        title: str,
        summary: str,
        output_payload: dict[str, Any] | None = None,
    ) -> None:
        """Record a completed workflow synthesis step that was not a direct tool call.

        Args:
            step_id: Stable step identifier unique within the workflow.
            title: Human-readable workflow step title.
            summary: Short operational summary of the synthesis step.
            output_payload: Optional structured payload produced by the synthesis step.

        Returns:
            None.

        Raises:
            None.
        """
        self._state.steps.append(
            WorkflowStep(
                step_id=step_id,
                title=title,
                tool_id=None,
                status="completed",
                summary=summary,
                output_model="workflow_synthesis",
                output_payload=output_payload or {},
            )
        )
        self._state.step_outputs[step_id] = output_payload or {}

    def add_skipped_step(
        self,
        *,
        step_id: str,
        title: str,
        summary: str,
    ) -> None:
        """Record one workflow step that was intentionally skipped.

        Args:
            step_id: Stable step identifier unique within the workflow.
            title: Human-readable workflow step title.
            summary: Reason why the step was skipped.

        Returns:
            None.

        Raises:
            None.
        """
        self._state.steps.append(
            WorkflowStep(
                step_id=step_id,
                title=title,
                tool_id=None,
                status="skipped",
                summary=summary,
            )
        )

    def add_generated_artifact(self, *, name: str, text: str) -> None:
        """Store one generated artifact inside the shared workflow state.

        Args:
            name: Stable artifact label such as `demand_letter` or `policy_draft`.
            text: Generated artifact text to preserve for later workflow steps.

        Returns:
            None.

        Raises:
            None.
        """
        self._state.generated_artifacts[name] = text

    def build(self) -> WorkflowState:
        """Return the accumulated workflow state.

        Args:
            None.

        Returns:
            The fully accumulated workflow state.

        Raises:
            None.
        """
        return self._state

    def _absorb_result(self, result: BaseResult) -> None:
        """Merge one tool result into the shared workflow state.

        Args:
            result: Structured result produced by one workflow step.

        Returns:
            None.

        Raises:
            None.
        """
        self._extend_unique_scalars(
            target=self._state.legal_reference_profile_ids,
            values=[result.legal_reference_profile_id] if result.legal_reference_profile_id else [],
        )
        self._extend_unique_scalars(
            target=self._state.legal_reference_source_ids,
            values=result.legal_reference_source_ids,
        )
        self._extend_unique_scalars(
            target=self._state.legal_reference_rule_ids,
            values=result.legal_reference_rule_ids,
        )
        self._extend_unique_models(
            target=self._state.legal_references,
            values=result.legal_references,
            key_builder=lambda item: f"{item.source_id}:{item.rule_id or ''}",
        )
        self._extend_unique_models(
            target=self._state.evidence_items,
            values=result.evidence_items,
            key_builder=lambda item: item.evidence_id,
        )
        self._extend_unique_models(
            target=self._state.findings,
            values=result.findings,
            key_builder=lambda item: item.finding_id,
        )
        self._extend_unique_models(
            target=self._state.recommended_actions,
            values=result.recommended_actions,
            key_builder=lambda item: item.action_id,
        )
        self._extend_unique_models(
            target=self._state.affected_parties,
            values=result.affected_parties,
            key_builder=lambda item: f"{item.name}:{item.role.value}",
        )
        self._extend_unique_models(
            target=self._state.timeline_events,
            values=result.timeline_events,
            key_builder=lambda item: f"{item.label}:{item.event_type.value}:{item.value}",
        )

        if isinstance(result, DocumentTypeClassificationResult):
            self._state.primary_document_type = result.primary_document_type
            self._state.alternative_document_types = result.alternative_document_types
            self._state.classification_confidence_band = result.confidence_band
        if isinstance(result, ClauseExtractionResult):
            self._extend_unique_models(
                target=self._state.extracted_clauses,
                values=result.clauses,
                key_builder=lambda item: item.clause_id,
            )
        if isinstance(result, DateExtractionResult):
            self._extend_unique_models(
                target=self._state.extracted_dates,
                values=result.dates,
                key_builder=lambda item: item.date_id,
            )
        if isinstance(result, AmountExtractionResult):
            self._extend_unique_models(
                target=self._state.extracted_amounts,
                values=result.amounts,
                key_builder=lambda item: item.amount_id,
            )
        if isinstance(result, ObligationExtractionResult):
            self._extend_unique_models(
                target=self._state.extracted_obligations,
                values=result.obligations,
                key_builder=lambda item: item.obligation_id,
            )
        if isinstance(result, TerminationTermExtractionResult):
            self._extend_unique_models(
                target=self._state.extracted_termination_terms,
                values=result.termination_terms,
                key_builder=lambda item: item.term_id,
            )
        if isinstance(result, DisputeResolutionExtractionResult):
            self._extend_unique_models(
                target=self._state.extracted_dispute_resolution_terms,
                values=result.dispute_resolution_terms,
                key_builder=lambda item: item.resolution_id,
            )
        if isinstance(result, ContractRiskScoreResult):
            self._state.step_outputs.setdefault("risk_score_card", result.model_dump(mode="json"))

    def _extend_unique_scalars(self, *, target: list[str], values: list[str]) -> None:
        """Append unseen scalar values to the target list.

        Args:
            target: Mutable list receiving deduplicated scalar values.
            values: Candidate scalar values to append.

        Returns:
            None.

        Raises:
            None.
        """
        value: str
        for value in values:
            if value not in target:
                target.append(value)

    def _extend_unique_models(
        self,
        *,
        target: list[Any],
        values: list[Any],
        key_builder: Callable[[Any], str],
    ) -> None:
        """Append unseen model values to the target list using a stable key.

        Args:
            target: Mutable list receiving deduplicated model instances.
            values: Candidate model instances to append.
            key_builder: Callable that builds a unique key per model instance.

        Returns:
            None.

        Raises:
            None.
        """
        seen = {key_builder(item) for item in target}
        value: Any
        for value in values:
            key = key_builder(value)
            if key in seen:
                continue
            seen.add(key)
            target.append(value)
