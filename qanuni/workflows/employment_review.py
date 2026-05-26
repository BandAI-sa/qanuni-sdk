"""Employment-review workflow orchestration."""

from __future__ import annotations

from typing import Literal

from qanuni.models.labor import EndOfServiceResult, ProbationCheckResult
from qanuni.models.workflows import EmploymentReviewWorkflowInput, EmploymentReviewWorkflowResult
from qanuni.utils.documents import resolve_document_text
from qanuni.workflows.base import BaseWorkflow
from qanuni.workflows.state import WorkflowStateBuilder


class EmploymentReviewWorkflow(
    BaseWorkflow[EmploymentReviewWorkflowInput, EmploymentReviewWorkflowResult]
):
    """Compose labor and atomic tools into a stronger employment-review workflow."""

    WORKFLOW_ID = "workflow.employment_review"
    INPUT_MODEL = EmploymentReviewWorkflowInput
    OUTPUT_MODEL = EmploymentReviewWorkflowResult

    def _run(self, input_data: EmploymentReviewWorkflowInput) -> EmploymentReviewWorkflowResult:
        """Execute the employment-review workflow synchronously.

        Args:
            input_data: Parsed workflow input for the current employment-review run.

        Returns:
            A structured employment-review workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        document_text = resolve_document_text(
            text=input_data.document_text,
            file_path=input_data.document_file,
        )
        document_type_hint = input_data.document_type or "عقد عمل"
        builder = WorkflowStateBuilder(self.WORKFLOW_ID)

        classification = self._client.legal.classify_document_type(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.classify_document_type"),
        )
        builder.add_result_step(
            step_id="classify_document",
            title="تصنيف المستند",
            result=classification,
            summary=classification.summary,
        )

        party_result = self._client.legal.extract_parties(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_parties"),
        )
        builder.add_result_step(
            step_id="extract_parties",
            title="استخراج الأطراف",
            result=party_result,
            summary=party_result.summary,
        )

        date_result = self._client.legal.extract_dates(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_dates"),
        )
        builder.add_result_step(
            step_id="extract_dates",
            title="استخراج التواريخ",
            result=date_result,
            summary=date_result.summary,
        )

        amount_result = self._client.legal.extract_amounts(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_amounts"),
        )
        builder.add_result_step(
            step_id="extract_amounts",
            title="استخراج المقابل المالي",
            result=amount_result,
            summary=amount_result.summary,
        )

        obligation_result = self._client.legal.extract_obligations(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_obligations"),
        )
        builder.add_result_step(
            step_id="extract_obligations",
            title="استخراج الالتزامات",
            result=obligation_result,
            summary=obligation_result.summary,
        )

        termination_result = self._client.legal.extract_termination_terms(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_termination_terms"),
        )
        builder.add_result_step(
            step_id="extract_termination_terms",
            title="استخراج أحكام الإنهاء",
            result=termination_result,
            summary=termination_result.summary,
        )

        probation_result: ProbationCheckResult | None = None
        if input_data.probation_days is not None:
            probation_result = self._client.labor.probation_check(
                probation_days=input_data.probation_days,
                contract_type=input_data.contract_type,
                extension_in_writing=input_data.extension_in_writing,
                contract_text_snippet=document_text[:400],
                _config=self._runtime_for(input_data, "labor.probation_check"),
            )
            builder.add_result_step(
                step_id="probation_check",
                title="فحص فترة التجربة",
                result=probation_result,
                summary=probation_result.legal_explanation,
            )
        else:
            builder.add_skipped_step(
                step_id="probation_check",
                title="فحص فترة التجربة",
                summary="تم تجاوز الخطوة لعدم تزويد workflow بقيمة probation_days.",
            )

        end_of_service_result: EndOfServiceResult | None = None
        if (
            input_data.monthly_salary is not None
            and input_data.years_of_service is not None
            and input_data.termination_reason is not None
        ):
            end_of_service_result = self._client.labor.end_of_service(
                monthly_salary=input_data.monthly_salary,
                years_of_service=input_data.years_of_service,
                termination_reason=input_data.termination_reason,
                contract_type=input_data.contract_type,
                _config=self._runtime_for(input_data, "labor.end_of_service"),
            )
            builder.add_result_step(
                step_id="end_of_service",
                title="حساب نهاية الخدمة",
                result=end_of_service_result,
                summary=end_of_service_result.legal_explanation,
            )
        else:
            builder.add_skipped_step(
                step_id="end_of_service",
                title="حساب نهاية الخدمة",
                summary=(
                    "تم تجاوز الخطوة لعدم اكتمال monthly_salary أو years_of_service "
                    "أو termination_reason."
                ),
            )

        employment_risks = self._build_employment_risks(
            probation_result=probation_result,
            termination_risk_notes=[
                item.risk_note or "" for item in termination_result.termination_terms
            ],
        )
        recommended_follow_ups = self._build_follow_ups(
            probation_result=probation_result,
            end_of_service_result=end_of_service_result,
        )
        builder.add_synthesis_step(
            step_id="employment_review_summary",
            title="تلخيص المراجعة العمالية",
            summary=(
                f"تم تحديد {len(employment_risks)} مخاطر و"
                f"{len(recommended_follow_ups)} خطوات متابعة."
            ),
            output_payload={
                "employment_risks": employment_risks,
                "recommended_follow_ups": recommended_follow_ups,
            },
        )

        probation_status = self._probation_status(probation_result)
        final_state = builder.build()
        return EmploymentReviewWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                risk_count=len(employment_risks),
                probation_status=probation_status,
                end_of_service_result=end_of_service_result,
            ),
            probation_status=probation_status,
            end_of_service_amount=(
                end_of_service_result.total_amount if end_of_service_result is not None else None
            ),
            employment_risks=employment_risks,
            recommended_follow_ups=recommended_follow_ups,
        )

    async def _arun(
        self,
        input_data: EmploymentReviewWorkflowInput,
    ) -> EmploymentReviewWorkflowResult:
        """Execute the employment-review workflow asynchronously.

        Args:
            input_data: Parsed workflow input for the current employment-review run.

        Returns:
            A structured employment-review workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        document_text = resolve_document_text(
            text=input_data.document_text,
            file_path=input_data.document_file,
        )
        document_type_hint = input_data.document_type or "عقد عمل"
        builder = WorkflowStateBuilder(self.WORKFLOW_ID)

        classification = await self._client.legal.aclassify_document_type(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.classify_document_type"),
        )
        builder.add_result_step(
            step_id="classify_document",
            title="تصنيف المستند",
            result=classification,
            summary=classification.summary,
        )

        party_result = await self._client.legal.aextract_parties(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_parties"),
        )
        builder.add_result_step(
            step_id="extract_parties",
            title="استخراج الأطراف",
            result=party_result,
            summary=party_result.summary,
        )

        date_result = await self._client.legal.aextract_dates(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_dates"),
        )
        builder.add_result_step(
            step_id="extract_dates",
            title="استخراج التواريخ",
            result=date_result,
            summary=date_result.summary,
        )

        amount_result = await self._client.legal.aextract_amounts(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_amounts"),
        )
        builder.add_result_step(
            step_id="extract_amounts",
            title="استخراج المقابل المالي",
            result=amount_result,
            summary=amount_result.summary,
        )

        obligation_result = await self._client.legal.aextract_obligations(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_obligations"),
        )
        builder.add_result_step(
            step_id="extract_obligations",
            title="استخراج الالتزامات",
            result=obligation_result,
            summary=obligation_result.summary,
        )

        termination_result = await self._client.legal.aextract_termination_terms(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_termination_terms"),
        )
        builder.add_result_step(
            step_id="extract_termination_terms",
            title="استخراج أحكام الإنهاء",
            result=termination_result,
            summary=termination_result.summary,
        )

        probation_result: ProbationCheckResult | None = None
        if input_data.probation_days is not None:
            probation_result = await self._client.labor.aprobation_check(
                probation_days=input_data.probation_days,
                contract_type=input_data.contract_type,
                extension_in_writing=input_data.extension_in_writing,
                contract_text_snippet=document_text[:400],
                _config=self._runtime_for(input_data, "labor.probation_check"),
            )
            builder.add_result_step(
                step_id="probation_check",
                title="فحص فترة التجربة",
                result=probation_result,
                summary=probation_result.legal_explanation,
            )
        else:
            builder.add_skipped_step(
                step_id="probation_check",
                title="فحص فترة التجربة",
                summary="تم تجاوز الخطوة لعدم تزويد workflow بقيمة probation_days.",
            )

        end_of_service_result: EndOfServiceResult | None = None
        if (
            input_data.monthly_salary is not None
            and input_data.years_of_service is not None
            and input_data.termination_reason is not None
        ):
            end_of_service_result = await self._client.labor.aend_of_service(
                monthly_salary=input_data.monthly_salary,
                years_of_service=input_data.years_of_service,
                termination_reason=input_data.termination_reason,
                contract_type=input_data.contract_type,
                _config=self._runtime_for(input_data, "labor.end_of_service"),
            )
            builder.add_result_step(
                step_id="end_of_service",
                title="حساب نهاية الخدمة",
                result=end_of_service_result,
                summary=end_of_service_result.legal_explanation,
            )
        else:
            builder.add_skipped_step(
                step_id="end_of_service",
                title="حساب نهاية الخدمة",
                summary=(
                    "تم تجاوز الخطوة لعدم اكتمال monthly_salary أو years_of_service "
                    "أو termination_reason."
                ),
            )

        employment_risks = self._build_employment_risks(
            probation_result=probation_result,
            termination_risk_notes=[
                item.risk_note or "" for item in termination_result.termination_terms
            ],
        )
        recommended_follow_ups = self._build_follow_ups(
            probation_result=probation_result,
            end_of_service_result=end_of_service_result,
        )
        builder.add_synthesis_step(
            step_id="employment_review_summary",
            title="تلخيص المراجعة العمالية",
            summary=(
                f"تم تحديد {len(employment_risks)} مخاطر و"
                f"{len(recommended_follow_ups)} خطوات متابعة."
            ),
            output_payload={
                "employment_risks": employment_risks,
                "recommended_follow_ups": recommended_follow_ups,
            },
        )

        probation_status = self._probation_status(probation_result)
        final_state = builder.build()
        return EmploymentReviewWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                risk_count=len(employment_risks),
                probation_status=probation_status,
                end_of_service_result=end_of_service_result,
            ),
            probation_status=probation_status,
            end_of_service_amount=(
                end_of_service_result.total_amount if end_of_service_result is not None else None
            ),
            employment_risks=employment_risks,
            recommended_follow_ups=recommended_follow_ups,
        )

    def _probation_status(
        self,
        probation_result: ProbationCheckResult | None,
    ) -> Literal["not_run", "legal", "violation"]:
        """Normalize the probation result into a workflow-friendly status label.

        Args:
            probation_result: Optional probation-check result from the labor namespace.

        Returns:
            A normalized probation status for the workflow result model.

        Raises:
            None.
        """
        if probation_result is None:
            return "not_run"
        return "legal" if probation_result.is_legal else "violation"

    def _build_employment_risks(
        self,
        *,
        probation_result: ProbationCheckResult | None,
        termination_risk_notes: list[str],
    ) -> list[str]:
        """Collect labor risks from the workflow's deterministic and extracted steps.

        Args:
            probation_result: Optional probation-check result from the labor namespace.
            termination_risk_notes: Risk notes extracted from termination clauses.

        Returns:
            A deduplicated list of employment-review risks.

        Raises:
            None.
        """
        risks = [note.strip() for note in termination_risk_notes if note.strip()]
        if probation_result is not None and probation_result.violations:
            risks.extend(probation_result.violations)
        return self._unique_strings(risks)

    def _build_follow_ups(
        self,
        *,
        probation_result: ProbationCheckResult | None,
        end_of_service_result: EndOfServiceResult | None,
    ) -> list[str]:
        """Translate workflow findings into concrete next actions.

        Args:
            probation_result: Optional probation-check result from the labor namespace.
            end_of_service_result: Optional end-of-service calculation result.

        Returns:
            A deduplicated list of follow-up actions.

        Raises:
            None.
        """
        follow_ups: list[str] = []
        if probation_result is not None and not probation_result.is_legal:
            follow_ups.append("راجع نص فترة التجربة وعدّل المدة أو مبرر التمديد الكتابي.")
        if end_of_service_result is not None and end_of_service_result.additional_entitlements:
            follow_ups.extend(end_of_service_result.additional_entitlements)
        return self._unique_strings(follow_ups)

    def _build_executive_summary(
        self,
        *,
        risk_count: int,
        probation_status: Literal["not_run", "legal", "violation"],
        end_of_service_result: EndOfServiceResult | None,
    ) -> str:
        """Summarize the full employment review in one concise Arabic paragraph.

        Args:
            risk_count: Number of risks synthesized by the workflow.
            probation_status: Normalized probation-review status.
            end_of_service_result: Optional end-of-service calculation result.

        Returns:
            A concise Arabic executive summary for the workflow result.

        Raises:
            None.
        """
        end_of_service_note = (
            f" وتم تقدير نهاية الخدمة بمبلغ {end_of_service_result.total_amount:.2f}."
            if end_of_service_result is not None
            else ""
        )
        return (
            f"المراجعة العمالية جمعت بين تحليل المستند والضوابط النظامية، وحددت {risk_count} "
            f"مخاطر تشغيلية مع حالة فترة تجربة = {probation_status}.{end_of_service_note}"
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
