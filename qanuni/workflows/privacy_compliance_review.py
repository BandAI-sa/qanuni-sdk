"""Privacy-compliance review workflow orchestration."""

from __future__ import annotations

from qanuni.models.compliance import PDPLCheckResult, PrivacyPolicyResult
from qanuni.models.workflows import (
    PrivacyComplianceReviewInput,
    PrivacyComplianceReviewWorkflowResult,
)
from qanuni.utils.documents import resolve_document_text
from qanuni.workflows.base import BaseWorkflow
from qanuni.workflows.state import WorkflowStateBuilder


class PrivacyComplianceReviewWorkflow(
    BaseWorkflow[PrivacyComplianceReviewInput, PrivacyComplianceReviewWorkflowResult]
):
    """Compose privacy-policy and PDPL checks into one review workflow."""

    WORKFLOW_ID = "workflow.privacy_compliance_review"
    INPUT_MODEL = PrivacyComplianceReviewInput
    OUTPUT_MODEL = PrivacyComplianceReviewWorkflowResult

    def _run(
        self,
        input_data: PrivacyComplianceReviewInput,
    ) -> PrivacyComplianceReviewWorkflowResult:
        """Execute the privacy-compliance workflow synchronously.

        Args:
            input_data: Parsed workflow input for the current privacy review.

        Returns:
            A structured privacy-compliance workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        document_text = resolve_document_text(
            text=input_data.document_text,
            file_path=input_data.document_file,
        )
        document_type_hint = input_data.document_type or "سياسة أو إشعار خصوصية"
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

        clause_result = self._client.drafting.extract_clauses(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "drafting.extract_clauses"),
        )
        builder.add_result_step(
            step_id="extract_clauses",
            title="استخراج بنية البنود",
            result=clause_result,
            summary=clause_result.summary,
        )

        pdpl_result = self._client.compliance.pdpl_check(
            document_text=document_text,
            processing_context=input_data.processing_context,
            cross_border_transfers=input_data.cross_border_transfers,
            _config=self._runtime_for(input_data, "compliance.pdpl_check"),
        )
        builder.add_result_step(
            step_id="pdpl_check_original",
            title="فحص الامتثال الأصلي",
            result=pdpl_result,
            summary=pdpl_result.summary,
        )

        generated_policy_result: PrivacyPolicyResult | None = None
        generated_policy_check: PDPLCheckResult | None = None
        if input_data.generate_policy_draft:
            generated_policy_result = self._client.compliance.generate_privacy_policy(
                company_name=input_data.company_name or "",
                service_type=input_data.service_type or "",
                data_collected=input_data.data_collected,
                data_purposes=input_data.data_purposes,
                third_party_sharing=input_data.third_party_sharing,
                international_transfers=input_data.international_transfers,
                dpo_contact=input_data.dpo_contact,
                _config=self._runtime_for(input_data, "compliance.generate_privacy_policy"),
            )
            builder.add_result_step(
                step_id="generate_privacy_policy",
                title="توليد مسودة سياسة خصوصية",
                result=generated_policy_result,
                summary="تم توليد مسودة سياسة خصوصية علاجية للمراجعة الداخلية.",
            )
            builder.add_generated_artifact(
                name="policy_draft",
                text=generated_policy_result.policy_text,
            )

            generated_policy_check = self._client.compliance.pdpl_check(
                document_text=generated_policy_result.policy_text,
                processing_context=input_data.processing_context,
                cross_border_transfers=input_data.cross_border_transfers,
                _config=self._runtime_for(input_data, "compliance.pdpl_check"),
            )
            builder.add_result_step(
                step_id="pdpl_check_generated",
                title="فحص المسودة المولدة",
                result=generated_policy_check,
                summary=generated_policy_check.summary,
            )
        else:
            builder.add_skipped_step(
                step_id="generate_privacy_policy",
                title="توليد مسودة سياسة خصوصية",
                summary="تم تجاوز توليد المسودة لأن generate_policy_draft غير مفعّل.",
            )

        remediation_priorities = self._build_remediation_priorities(
            pdpl_result=pdpl_result,
            generated_policy_check=generated_policy_check,
        )
        builder.add_synthesis_step(
            step_id="privacy_remediation_plan",
            title="خطة المعالجة",
            summary=f"تم ترتيب {len(remediation_priorities)} أولويات معالجة خصوصية.",
            output_payload={"remediation_priorities": remediation_priorities},
        )

        final_state = builder.build()
        return PrivacyComplianceReviewWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                original_score=pdpl_result.compliance_score,
                generated_policy_check=generated_policy_check,
            ),
            compliance_score=(
                generated_policy_check.compliance_score
                if generated_policy_check is not None
                else pdpl_result.compliance_score
            ),
            key_gaps=pdpl_result.gaps,
            remediation_priorities=remediation_priorities,
            policy_draft_text=(
                generated_policy_result.policy_text if generated_policy_result is not None else None
            ),
        )

    async def _arun(
        self,
        input_data: PrivacyComplianceReviewInput,
    ) -> PrivacyComplianceReviewWorkflowResult:
        """Execute the privacy-compliance workflow asynchronously.

        Args:
            input_data: Parsed workflow input for the current privacy review.

        Returns:
            A structured privacy-compliance workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        document_text = resolve_document_text(
            text=input_data.document_text,
            file_path=input_data.document_file,
        )
        document_type_hint = input_data.document_type or "سياسة أو إشعار خصوصية"
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

        clause_result = await self._client.drafting.aextract_clauses(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "drafting.extract_clauses"),
        )
        builder.add_result_step(
            step_id="extract_clauses",
            title="استخراج بنية البنود",
            result=clause_result,
            summary=clause_result.summary,
        )

        pdpl_result = await self._client.compliance.apdpl_check(
            document_text=document_text,
            processing_context=input_data.processing_context,
            cross_border_transfers=input_data.cross_border_transfers,
            _config=self._runtime_for(input_data, "compliance.pdpl_check"),
        )
        builder.add_result_step(
            step_id="pdpl_check_original",
            title="فحص الامتثال الأصلي",
            result=pdpl_result,
            summary=pdpl_result.summary,
        )

        generated_policy_result: PrivacyPolicyResult | None = None
        generated_policy_check: PDPLCheckResult | None = None
        if input_data.generate_policy_draft:
            generated_policy_result = await self._client.compliance.agenerate_privacy_policy(
                company_name=input_data.company_name or "",
                service_type=input_data.service_type or "",
                data_collected=input_data.data_collected,
                data_purposes=input_data.data_purposes,
                third_party_sharing=input_data.third_party_sharing,
                international_transfers=input_data.international_transfers,
                dpo_contact=input_data.dpo_contact,
                _config=self._runtime_for(input_data, "compliance.generate_privacy_policy"),
            )
            builder.add_result_step(
                step_id="generate_privacy_policy",
                title="توليد مسودة سياسة خصوصية",
                result=generated_policy_result,
                summary="تم توليد مسودة سياسة خصوصية علاجية للمراجعة الداخلية.",
            )
            builder.add_generated_artifact(
                name="policy_draft",
                text=generated_policy_result.policy_text,
            )

            generated_policy_check = await self._client.compliance.apdpl_check(
                document_text=generated_policy_result.policy_text,
                processing_context=input_data.processing_context,
                cross_border_transfers=input_data.cross_border_transfers,
                _config=self._runtime_for(input_data, "compliance.pdpl_check"),
            )
            builder.add_result_step(
                step_id="pdpl_check_generated",
                title="فحص المسودة المولدة",
                result=generated_policy_check,
                summary=generated_policy_check.summary,
            )
        else:
            builder.add_skipped_step(
                step_id="generate_privacy_policy",
                title="توليد مسودة سياسة خصوصية",
                summary="تم تجاوز توليد المسودة لأن generate_policy_draft غير مفعّل.",
            )

        remediation_priorities = self._build_remediation_priorities(
            pdpl_result=pdpl_result,
            generated_policy_check=generated_policy_check,
        )
        builder.add_synthesis_step(
            step_id="privacy_remediation_plan",
            title="خطة المعالجة",
            summary=f"تم ترتيب {len(remediation_priorities)} أولويات معالجة خصوصية.",
            output_payload={"remediation_priorities": remediation_priorities},
        )

        final_state = builder.build()
        return PrivacyComplianceReviewWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                original_score=pdpl_result.compliance_score,
                generated_policy_check=generated_policy_check,
            ),
            compliance_score=(
                generated_policy_check.compliance_score
                if generated_policy_check is not None
                else pdpl_result.compliance_score
            ),
            key_gaps=pdpl_result.gaps,
            remediation_priorities=remediation_priorities,
            policy_draft_text=(
                generated_policy_result.policy_text if generated_policy_result is not None else None
            ),
        )

    def _build_remediation_priorities(
        self,
        *,
        pdpl_result: PDPLCheckResult,
        generated_policy_check: PDPLCheckResult | None,
    ) -> list[str]:
        priorities = list(pdpl_result.required_actions)
        if generated_policy_check is not None:
            priorities.extend(generated_policy_check.required_actions)
        return self._unique_strings(priorities)

    def _build_executive_summary(
        self,
        *,
        original_score: float,
        generated_policy_check: PDPLCheckResult | None,
    ) -> str:
        if generated_policy_check is None:
            return (
                f"فحص الخصوصية الحالي سجّل {original_score:.0f}/100، وتم تجميع فجوات "
                "وتوصيات علاجية قابلة للتنفيذ دون توليد سياسة بديلة."
            )
        return (
            f"فحص الخصوصية بدأ بدرجة {original_score:.0f}/100 ثم أعاد تقييم المسودة المولدة "
            f"بدرجة {generated_policy_check.compliance_score:.0f}/100، ما يجعل workflow "
            "أقوى من check منفرد أو generator منفرد."
        )

    def _unique_strings(self, values: list[str]) -> list[str]:
        unique_values: list[str] = []
        value: str
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in unique_values:
                continue
            unique_values.append(normalized)
        return unique_values
