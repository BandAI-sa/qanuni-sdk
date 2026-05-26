"""Pre-litigation notice workflow orchestration."""

from __future__ import annotations

from qanuni.models.compliance import DemandLetterResult
from qanuni.models.drafting import TextImprovementResult
from qanuni.models.workflows import (
    PreLitigationNoticeWorkflowInput,
    PreLitigationNoticeWorkflowResult,
    WorkflowState,
)
from qanuni.utils.documents import resolve_document_text
from qanuni.workflows.base import BaseWorkflow
from qanuni.workflows.state import WorkflowStateBuilder


class PreLitigationNoticeWorkflow(
    BaseWorkflow[PreLitigationNoticeWorkflowInput, PreLitigationNoticeWorkflowResult]
):
    """Compose support extraction and drafting into a pre-litigation workflow."""

    WORKFLOW_ID = "workflow.pre_litigation_notice"
    INPUT_MODEL = PreLitigationNoticeWorkflowInput
    OUTPUT_MODEL = PreLitigationNoticeWorkflowResult

    def _run(
        self,
        input_data: PreLitigationNoticeWorkflowInput,
    ) -> PreLitigationNoticeWorkflowResult:
        """Execute the pre-litigation notice workflow synchronously.

        Args:
            input_data: Parsed workflow input for the current notice flow.

        Returns:
            A structured pre-litigation notice workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        builder = WorkflowStateBuilder(self.WORKFLOW_ID)
        support_text = self._resolve_support_text(input_data)

        if support_text:
            document_type_hint = input_data.support_document_type or "مستند داعم للمطالبة"
            classification = self._client.legal.classify_document_type(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.classify_document_type"),
            )
            builder.add_result_step(
                step_id="classify_support_document",
                title="تصنيف المستند الداعم",
                result=classification,
                summary=classification.summary,
            )

            party_result = self._client.legal.extract_parties(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_parties"),
            )
            builder.add_result_step(
                step_id="extract_support_parties",
                title="استخراج الأطراف",
                result=party_result,
                summary=party_result.summary,
            )

            obligation_result = self._client.legal.extract_obligations(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_obligations"),
            )
            builder.add_result_step(
                step_id="extract_support_obligations",
                title="استخراج الالتزامات",
                result=obligation_result,
                summary=obligation_result.summary,
            )

            amount_result = self._client.legal.extract_amounts(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_amounts"),
            )
            builder.add_result_step(
                step_id="extract_support_amounts",
                title="استخراج المبالغ",
                result=amount_result,
                summary=amount_result.summary,
            )

            date_result = self._client.legal.extract_dates(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_dates"),
            )
            builder.add_result_step(
                step_id="extract_support_dates",
                title="استخراج التواريخ",
                result=date_result,
                summary=date_result.summary,
            )

            dispute_result = self._client.legal.extract_dispute_resolution(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_dispute_resolution"),
            )
            builder.add_result_step(
                step_id="extract_dispute_path",
                title="استخراج مسار النزاع",
                result=dispute_result,
                summary=dispute_result.summary,
            )
        else:
            builder.add_skipped_step(
                step_id="support_document_analysis",
                title="تحليل المستند الداعم",
                summary=(
                    "لا يوجد support_document_text أو support_document_file، "
                    "فتم الاعتماد على وصف الواقعة فقط."
                ),
            )

        demand_letter_result = self._client.compliance.demand_letter(
            sender_name=input_data.sender_name,
            recipient_name=input_data.recipient_name,
            claim_type=input_data.claim_type,
            claim_amount=input_data.claim_amount,
            incident_description=input_data.incident_description,
            deadline_days=input_data.deadline_days,
            threat_of_action=input_data.threat_of_action,
            _config=self._runtime_for(input_data, "compliance.demand_letter"),
        )
        builder.add_result_step(
            step_id="generate_demand_letter",
            title="إنشاء خطاب المطالبة",
            result=demand_letter_result,
            summary="تم إنشاء خطاب مطالبة مبدئي بناءً على الوقائع والمدخلات المتاحة.",
        )

        improved_letter_result = self._client.drafting.improve(
            original_text=demand_letter_result.letter_text,
            improvement_goals=["clarity", "formality", "precision"],
            context="خطاب مطالبة قانونية قبل النزاع",
            _config=self._runtime_for(input_data, "drafting.improve"),
        )
        builder.add_result_step(
            step_id="improve_demand_letter",
            title="تحسين خطاب المطالبة",
            result=improved_letter_result,
            summary=improved_letter_result.overall_assessment,
        )
        builder.add_generated_artifact(
            name="demand_letter",
            text=improved_letter_result.improved_text,
        )

        state = builder.build()
        claim_support_summary = self._build_claim_support_summary(state)
        negotiation_points = self._build_negotiation_points(
            demand_letter_result=demand_letter_result,
            improved_letter_result=improved_letter_result,
        )
        builder.add_synthesis_step(
            step_id="pre_litigation_strategy",
            title="تلخيص الموقف قبل النزاع",
            summary=(
                f"تم اشتقاق {len(claim_support_summary)} مؤشرات دعم و"
                f"{len(negotiation_points)} نقاط تفاوض من المسار."
            ),
            output_payload={
                "claim_support_summary": claim_support_summary,
                "negotiation_points": negotiation_points,
            },
        )

        final_state = builder.build()
        return PreLitigationNoticeWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                support_points=len(claim_support_summary),
                negotiation_points=len(negotiation_points),
            ),
            demand_letter_text=improved_letter_result.improved_text,
            claim_support_summary=claim_support_summary,
            negotiation_points=negotiation_points,
        )

    async def _arun(
        self,
        input_data: PreLitigationNoticeWorkflowInput,
    ) -> PreLitigationNoticeWorkflowResult:
        """Execute the pre-litigation notice workflow asynchronously.

        Args:
            input_data: Parsed workflow input for the current notice flow.

        Returns:
            A structured pre-litigation notice workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        builder = WorkflowStateBuilder(self.WORKFLOW_ID)
        support_text = self._resolve_support_text(input_data)

        if support_text:
            document_type_hint = input_data.support_document_type or "مستند داعم للمطالبة"
            classification = await self._client.legal.aclassify_document_type(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.classify_document_type"),
            )
            builder.add_result_step(
                step_id="classify_support_document",
                title="تصنيف المستند الداعم",
                result=classification,
                summary=classification.summary,
            )

            party_result = await self._client.legal.aextract_parties(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_parties"),
            )
            builder.add_result_step(
                step_id="extract_support_parties",
                title="استخراج الأطراف",
                result=party_result,
                summary=party_result.summary,
            )

            obligation_result = await self._client.legal.aextract_obligations(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_obligations"),
            )
            builder.add_result_step(
                step_id="extract_support_obligations",
                title="استخراج الالتزامات",
                result=obligation_result,
                summary=obligation_result.summary,
            )

            amount_result = await self._client.legal.aextract_amounts(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_amounts"),
            )
            builder.add_result_step(
                step_id="extract_support_amounts",
                title="استخراج المبالغ",
                result=amount_result,
                summary=amount_result.summary,
            )

            date_result = await self._client.legal.aextract_dates(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_dates"),
            )
            builder.add_result_step(
                step_id="extract_support_dates",
                title="استخراج التواريخ",
                result=date_result,
                summary=date_result.summary,
            )

            dispute_result = await self._client.legal.aextract_dispute_resolution(
                document_text=support_text,
                document_type=document_type_hint,
                _config=self._runtime_for(input_data, "legal.extract_dispute_resolution"),
            )
            builder.add_result_step(
                step_id="extract_dispute_path",
                title="استخراج مسار النزاع",
                result=dispute_result,
                summary=dispute_result.summary,
            )
        else:
            builder.add_skipped_step(
                step_id="support_document_analysis",
                title="تحليل المستند الداعم",
                summary=(
                    "لا يوجد support_document_text أو support_document_file، "
                    "فتم الاعتماد على وصف الواقعة فقط."
                ),
            )

        demand_letter_result = await self._client.compliance.ademand_letter(
            sender_name=input_data.sender_name,
            recipient_name=input_data.recipient_name,
            claim_type=input_data.claim_type,
            claim_amount=input_data.claim_amount,
            incident_description=input_data.incident_description,
            deadline_days=input_data.deadline_days,
            threat_of_action=input_data.threat_of_action,
            _config=self._runtime_for(input_data, "compliance.demand_letter"),
        )
        builder.add_result_step(
            step_id="generate_demand_letter",
            title="إنشاء خطاب المطالبة",
            result=demand_letter_result,
            summary="تم إنشاء خطاب مطالبة مبدئي بناءً على الوقائع والمدخلات المتاحة.",
        )

        improved_letter_result = await self._client.drafting.aimprove(
            original_text=demand_letter_result.letter_text,
            improvement_goals=["clarity", "formality", "precision"],
            context="خطاب مطالبة قانونية قبل النزاع",
            _config=self._runtime_for(input_data, "drafting.improve"),
        )
        builder.add_result_step(
            step_id="improve_demand_letter",
            title="تحسين خطاب المطالبة",
            result=improved_letter_result,
            summary=improved_letter_result.overall_assessment,
        )
        builder.add_generated_artifact(
            name="demand_letter",
            text=improved_letter_result.improved_text,
        )

        state = builder.build()
        claim_support_summary = self._build_claim_support_summary(state)
        negotiation_points = self._build_negotiation_points(
            demand_letter_result=demand_letter_result,
            improved_letter_result=improved_letter_result,
        )
        builder.add_synthesis_step(
            step_id="pre_litigation_strategy",
            title="تلخيص الموقف قبل النزاع",
            summary=(
                f"تم اشتقاق {len(claim_support_summary)} مؤشرات دعم و"
                f"{len(negotiation_points)} نقاط تفاوض من المسار."
            ),
            output_payload={
                "claim_support_summary": claim_support_summary,
                "negotiation_points": negotiation_points,
            },
        )

        final_state = builder.build()
        return PreLitigationNoticeWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                support_points=len(claim_support_summary),
                negotiation_points=len(negotiation_points),
            ),
            demand_letter_text=improved_letter_result.improved_text,
            claim_support_summary=claim_support_summary,
            negotiation_points=negotiation_points,
        )

    def _resolve_support_text(
        self,
        input_data: PreLitigationNoticeWorkflowInput,
    ) -> str | None:
        """Resolve the optional supporting document text for the workflow.

        Args:
            input_data: Parsed workflow input for the current notice flow.

        Returns:
            Supporting text when available, otherwise `None`.

        Raises:
            None.
        """
        if not input_data.support_document_text and not input_data.support_document_file:
            return None
        return resolve_document_text(
            text=input_data.support_document_text,
            file_path=input_data.support_document_file,
        )

    def _build_claim_support_summary(self, state: WorkflowState) -> list[str]:
        """Summarize the evidence extracted from the supporting document.

        Args:
            state: Final shared workflow state accumulated across support steps.

        Returns:
            A short list of claim-support signals extracted from the state.

        Raises:
            None.
        """
        support_points: list[str] = []
        if state.extracted_obligations:
            support_points.append(
                "تم استخراج "
                f"{len(state.extracted_obligations)} التزامات تعاقدية يمكن الاستناد إليها."
            )
        if state.extracted_amounts:
            support_points.append(
                f"تم رصد {len(state.extracted_amounts)} مبالغ مالية مرتبطة بالمطالبة."
            )
        if state.timeline_events:
            support_points.append(
                f"تم تحديد {len(state.timeline_events)} عناصر زمنية قد تدعم سرد الوقائع والمهل."
            )
        return support_points

    def _build_negotiation_points(
        self,
        *,
        demand_letter_result: DemandLetterResult,
        improved_letter_result: TextImprovementResult,
    ) -> list[str]:
        """Merge drafting and demand-letter notes into negotiation talking points.

        Args:
            demand_letter_result: Base demand-letter output.
            improved_letter_result: Improved drafting output for the same letter.

        Returns:
            A deduplicated list of negotiation points.

        Raises:
            None.
        """
        points = list(demand_letter_result.strategic_notes)
        points.extend(change.reason for change in improved_letter_result.changes)
        return self._unique_strings(points)

    def _build_executive_summary(
        self,
        *,
        support_points: int,
        negotiation_points: int,
    ) -> str:
        """Describe the value of the pre-litigation orchestration in one paragraph.

        Args:
            support_points: Number of extracted support indicators.
            negotiation_points: Number of negotiation points derived by the workflow.

        Returns:
            A concise Arabic executive summary for the workflow result.

        Raises:
            None.
        """
        return (
            f"هذا workflow جمع بين تحليل الأدلة الداعمة وصياغة خطاب المطالبة وتحسينه، "
            f"وأنتج {support_points} مؤشرات دعم و{negotiation_points} نقاط تفاوض قبل التصعيد."
        )

    def _unique_strings(self, values: list[str]) -> list[str]:
        """Deduplicate non-empty string values while preserving order.

        Args:
            values: Raw string values collected from multiple workflow steps.

        Returns:
            A stable list of unique non-empty strings.

        Raises:
            None.
        """
        unique_values: list[str] = []
        value: str
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in unique_values:
                continue
            unique_values.append(normalized)
        return unique_values
