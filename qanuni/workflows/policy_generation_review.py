"""Policy-generation review workflow orchestration."""

from __future__ import annotations

from collections.abc import Iterable

from qanuni.models.compliance import PDPLCheckResult, PrivacyPolicyResult
from qanuni.models.drafting import SummaryResult
from qanuni.models.policies import HRPolicyResult
from qanuni.models.workflows import (
    PolicyGenerationReviewInput,
    PolicyGenerationReviewWorkflowResult,
)
from qanuni.workflows.base import BaseWorkflow
from qanuni.workflows.state import WorkflowStateBuilder


class PolicyGenerationReviewWorkflow(
    BaseWorkflow[PolicyGenerationReviewInput, PolicyGenerationReviewWorkflowResult]
):
    """Compose policy generation with one or more structured review steps."""

    WORKFLOW_ID = "workflow.policy_generation_review"
    INPUT_MODEL = PolicyGenerationReviewInput
    OUTPUT_MODEL = PolicyGenerationReviewWorkflowResult

    def _run(
        self,
        input_data: PolicyGenerationReviewInput,
    ) -> PolicyGenerationReviewWorkflowResult:
        """Execute the policy-generation review workflow synchronously.

        Args:
            input_data: Parsed workflow input for the selected policy-review path.

        Returns:
            A structured policy-generation review result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        builder = WorkflowStateBuilder(self.WORKFLOW_ID)
        generated_text, review_notes, follow_up_actions = self._run_policy_flow(
            input_data=input_data,
            builder=builder,
        )
        final_state = builder.build()
        return PolicyGenerationReviewWorkflowResult(
            state=final_state,
            policy_kind=input_data.policy_kind,
            executive_summary=self._build_executive_summary(
                policy_kind=input_data.policy_kind,
                review_note_count=len(review_notes),
                action_count=len(follow_up_actions),
            ),
            generated_text=generated_text,
            review_notes=review_notes,
            follow_up_actions=follow_up_actions,
        )

    async def _arun(
        self,
        input_data: PolicyGenerationReviewInput,
    ) -> PolicyGenerationReviewWorkflowResult:
        """Execute the policy-generation review workflow asynchronously.

        Args:
            input_data: Parsed workflow input for the selected policy-review path.

        Returns:
            A structured policy-generation review result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        builder = WorkflowStateBuilder(self.WORKFLOW_ID)
        generated_text, review_notes, follow_up_actions = await self._arun_policy_flow(
            input_data=input_data,
            builder=builder,
        )
        final_state = builder.build()
        return PolicyGenerationReviewWorkflowResult(
            state=final_state,
            policy_kind=input_data.policy_kind,
            executive_summary=self._build_executive_summary(
                policy_kind=input_data.policy_kind,
                review_note_count=len(review_notes),
                action_count=len(follow_up_actions),
            ),
            generated_text=generated_text,
            review_notes=review_notes,
            follow_up_actions=follow_up_actions,
        )

    def _run_policy_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Dispatch the synchronous workflow branch for the selected policy kind.

        Args:
            input_data: Parsed workflow input for the current policy review.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated text, review notes, and follow-up actions.

        Raises:
            None.
        """
        if input_data.policy_kind == "hr_policy":
            return self._run_hr_policy_flow(input_data=input_data, builder=builder)
        if input_data.policy_kind == "job_description":
            return self._run_job_description_flow(input_data=input_data, builder=builder)
        return self._run_privacy_policy_flow(input_data=input_data, builder=builder)

    async def _arun_policy_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Dispatch the asynchronous workflow branch for the selected policy kind.

        Args:
            input_data: Parsed workflow input for the current policy review.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated text, review notes, and follow-up actions.

        Raises:
            None.
        """
        if input_data.policy_kind == "hr_policy":
            return await self._arun_hr_policy_flow(input_data=input_data, builder=builder)
        if input_data.policy_kind == "job_description":
            return await self._arun_job_description_flow(input_data=input_data, builder=builder)
        return await self._arun_privacy_policy_flow(input_data=input_data, builder=builder)

    def _run_hr_policy_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Generate and review an HR policy in the synchronous branch.

        Args:
            input_data: Parsed workflow input for the HR-policy branch.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated policy text, review notes, and follow-up actions.

        Raises:
            None.
        """
        policy_result = self._client.policies.generate_hr_policy(
            policy_type=input_data.policy_type or "",
            company_name=input_data.company_name or "",
            industry=input_data.industry or "",
            employee_count=input_data.employee_count or 1,
            custom_requirements=input_data.custom_requirements,
            _config=self._runtime_for(input_data, "policies.generate_hr_policy"),
        )
        builder.add_result_step(
            step_id="generate_hr_policy",
            title="توليد سياسة الموارد البشرية",
            result=policy_result,
            summary="تم توليد سياسة موارد بشرية مبدئية.",
        )
        builder.add_generated_artifact(name="policy_text", text=policy_result.policy_text)

        clause_result = self._client.drafting.extract_clauses(
            document_text=policy_result.policy_text,
            document_type="سياسة موارد بشرية",
            _config=self._runtime_for(input_data, "drafting.extract_clauses"),
        )
        builder.add_result_step(
            step_id="extract_policy_clauses",
            title="تحليل بنية السياسة",
            result=clause_result,
            summary=clause_result.summary,
        )

        summary_result = self._client.drafting.summarize(
            document_text=policy_result.policy_text,
            summary_length="brief",
            focus_on=["obligations", "risks"],
            _config=self._runtime_for(input_data, "drafting.summarize"),
        )
        builder.add_result_step(
            step_id="summarize_policy",
            title="تلخيص السياسة",
            result=summary_result,
            summary="تم تلخيص السياسة لإبراز الحقوق والالتزامات والمخاطر.",
        )

        review_notes = self._build_hr_policy_review_notes(
            policy_result=policy_result,
            summary_result=summary_result,
        )
        follow_up_actions = self._unique_strings(
            policy_result.recommended_additions + summary_result.risk_highlights
        )
        builder.add_synthesis_step(
            step_id="review_hr_policy",
            title="مراجعة السياسة المولدة",
            summary=(
                f"تم اشتقاق {len(review_notes)} ملاحظات و"
                f"{len(follow_up_actions)} إجراءات متابعة."
            ),
            output_payload={
                "review_notes": review_notes,
                "follow_up_actions": follow_up_actions,
            },
        )
        return policy_result.policy_text, review_notes, follow_up_actions

    async def _arun_hr_policy_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Generate and review an HR policy in the asynchronous branch.

        Args:
            input_data: Parsed workflow input for the HR-policy branch.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated policy text, review notes, and follow-up actions.

        Raises:
            None.
        """
        policy_result = await self._client.policies.agenerate_hr_policy(
            policy_type=input_data.policy_type or "",
            company_name=input_data.company_name or "",
            industry=input_data.industry or "",
            employee_count=input_data.employee_count or 1,
            custom_requirements=input_data.custom_requirements,
            _config=self._runtime_for(input_data, "policies.generate_hr_policy"),
        )
        builder.add_result_step(
            step_id="generate_hr_policy",
            title="توليد سياسة الموارد البشرية",
            result=policy_result,
            summary="تم توليد سياسة موارد بشرية مبدئية.",
        )
        builder.add_generated_artifact(name="policy_text", text=policy_result.policy_text)

        clause_result = await self._client.drafting.aextract_clauses(
            document_text=policy_result.policy_text,
            document_type="سياسة موارد بشرية",
            _config=self._runtime_for(input_data, "drafting.extract_clauses"),
        )
        builder.add_result_step(
            step_id="extract_policy_clauses",
            title="تحليل بنية السياسة",
            result=clause_result,
            summary=clause_result.summary,
        )

        summary_result = await self._client.drafting.asummarize(
            document_text=policy_result.policy_text,
            summary_length="brief",
            focus_on=["obligations", "risks"],
            _config=self._runtime_for(input_data, "drafting.summarize"),
        )
        builder.add_result_step(
            step_id="summarize_policy",
            title="تلخيص السياسة",
            result=summary_result,
            summary="تم تلخيص السياسة لإبراز الحقوق والالتزامات والمخاطر.",
        )

        review_notes = self._build_hr_policy_review_notes(
            policy_result=policy_result,
            summary_result=summary_result,
        )
        follow_up_actions = self._unique_strings(
            policy_result.recommended_additions + summary_result.risk_highlights
        )
        builder.add_synthesis_step(
            step_id="review_hr_policy",
            title="مراجعة السياسة المولدة",
            summary=(
                f"تم اشتقاق {len(review_notes)} ملاحظات و"
                f"{len(follow_up_actions)} إجراءات متابعة."
            ),
            output_payload={
                "review_notes": review_notes,
                "follow_up_actions": follow_up_actions,
            },
        )
        return policy_result.policy_text, review_notes, follow_up_actions

    def _run_job_description_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Generate and review a job description in the synchronous branch.

        Args:
            input_data: Parsed workflow input for the job-description branch.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated job-description text, review notes, and follow-up actions.

        Raises:
            None.
        """
        job_result = self._client.policies.job_description(
            job_title=input_data.job_title or "",
            department=input_data.department or "",
            required_experience_years=input_data.required_experience_years or 0,
            required_education=input_data.required_education or "",
            key_responsibilities=input_data.key_responsibilities,
            required_skills=input_data.required_skills,
            saudization_preferred=input_data.saudization_preferred,
            salary_range=input_data.salary_range,
            _config=self._runtime_for(input_data, "policies.job_description"),
        )
        builder.add_result_step(
            step_id="generate_job_description",
            title="توليد الوصف الوظيفي",
            result=job_result,
            summary="تم توليد وصف وظيفي مبدئي للمراجعة.",
        )

        improve_result = self._client.drafting.improve(
            original_text=job_result.job_description_text,
            improvement_goals=["clarity", "formality"],
            context="وصف وظيفي",
            _config=self._runtime_for(input_data, "drafting.improve"),
        )
        builder.add_result_step(
            step_id="improve_job_description",
            title="تحسين الوصف الوظيفي",
            result=improve_result,
            summary=improve_result.overall_assessment,
        )
        builder.add_generated_artifact(name="job_description", text=improve_result.improved_text)

        review_notes = self._unique_strings(
            list(job_result.legal_compliance_notes) + list(job_result.discriminatory_language_flags)
        )
        follow_up_actions = self._unique_strings(change.reason for change in improve_result.changes)
        builder.add_synthesis_step(
            step_id="review_job_description",
            title="مراجعة الوصف الوظيفي",
            summary=(
                f"تم اشتقاق {len(review_notes)} ملاحظات و"
                f"{len(follow_up_actions)} إجراءات متابعة."
            ),
            output_payload={
                "review_notes": review_notes,
                "follow_up_actions": follow_up_actions,
            },
        )
        return improve_result.improved_text, review_notes, follow_up_actions

    async def _arun_job_description_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Generate and review a job description in the asynchronous branch.

        Args:
            input_data: Parsed workflow input for the job-description branch.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated job-description text, review notes, and follow-up actions.

        Raises:
            None.
        """
        job_result = await self._client.policies.ajob_description(
            job_title=input_data.job_title or "",
            department=input_data.department or "",
            required_experience_years=input_data.required_experience_years or 0,
            required_education=input_data.required_education or "",
            key_responsibilities=input_data.key_responsibilities,
            required_skills=input_data.required_skills,
            saudization_preferred=input_data.saudization_preferred,
            salary_range=input_data.salary_range,
            _config=self._runtime_for(input_data, "policies.job_description"),
        )
        builder.add_result_step(
            step_id="generate_job_description",
            title="توليد الوصف الوظيفي",
            result=job_result,
            summary="تم توليد وصف وظيفي مبدئي للمراجعة.",
        )

        improve_result = await self._client.drafting.aimprove(
            original_text=job_result.job_description_text,
            improvement_goals=["clarity", "formality"],
            context="وصف وظيفي",
            _config=self._runtime_for(input_data, "drafting.improve"),
        )
        builder.add_result_step(
            step_id="improve_job_description",
            title="تحسين الوصف الوظيفي",
            result=improve_result,
            summary=improve_result.overall_assessment,
        )
        builder.add_generated_artifact(name="job_description", text=improve_result.improved_text)

        review_notes = self._unique_strings(
            list(job_result.legal_compliance_notes) + list(job_result.discriminatory_language_flags)
        )
        follow_up_actions = self._unique_strings(change.reason for change in improve_result.changes)
        builder.add_synthesis_step(
            step_id="review_job_description",
            title="مراجعة الوصف الوظيفي",
            summary=(
                f"تم اشتقاق {len(review_notes)} ملاحظات و"
                f"{len(follow_up_actions)} إجراءات متابعة."
            ),
            output_payload={
                "review_notes": review_notes,
                "follow_up_actions": follow_up_actions,
            },
        )
        return improve_result.improved_text, review_notes, follow_up_actions

    def _run_privacy_policy_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Generate and review a privacy policy in the synchronous branch.

        Args:
            input_data: Parsed workflow input for the privacy-policy branch.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated privacy-policy text, review notes, and follow-up actions.

        Raises:
            None.
        """
        policy_result = self._client.compliance.generate_privacy_policy(
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
            title="توليد سياسة الخصوصية",
            result=policy_result,
            summary="تم توليد سياسة خصوصية مبدئية.",
        )

        pdpl_check_result = self._client.compliance.pdpl_check(
            document_text=policy_result.policy_text,
            processing_context=input_data.service_type,
            cross_border_transfers=input_data.international_transfers,
            _config=self._runtime_for(input_data, "compliance.pdpl_check"),
        )
        builder.add_result_step(
            step_id="review_privacy_policy",
            title="فحص السياسة المولدة",
            result=pdpl_check_result,
            summary=pdpl_check_result.summary,
        )
        builder.add_generated_artifact(name="policy_text", text=policy_result.policy_text)

        review_notes = self._build_privacy_policy_review_notes(
            policy_result=policy_result,
            pdpl_check_result=pdpl_check_result,
        )
        follow_up_actions = self._unique_strings(pdpl_check_result.required_actions)
        builder.add_synthesis_step(
            step_id="privacy_policy_review_summary",
            title="تلخيص مراجعة السياسة",
            summary=(
                f"تم اشتقاق {len(review_notes)} ملاحظات و"
                f"{len(follow_up_actions)} إجراءات متابعة."
            ),
            output_payload={
                "review_notes": review_notes,
                "follow_up_actions": follow_up_actions,
            },
        )
        return policy_result.policy_text, review_notes, follow_up_actions

    async def _arun_privacy_policy_flow(
        self,
        *,
        input_data: PolicyGenerationReviewInput,
        builder: WorkflowStateBuilder,
    ) -> tuple[str, list[str], list[str]]:
        """Generate and review a privacy policy in the asynchronous branch.

        Args:
            input_data: Parsed workflow input for the privacy-policy branch.
            builder: Shared workflow-state accumulator for the current execution.

        Returns:
            The generated privacy-policy text, review notes, and follow-up actions.

        Raises:
            None.
        """
        policy_result = await self._client.compliance.agenerate_privacy_policy(
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
            title="توليد سياسة الخصوصية",
            result=policy_result,
            summary="تم توليد سياسة خصوصية مبدئية.",
        )

        pdpl_check_result = await self._client.compliance.apdpl_check(
            document_text=policy_result.policy_text,
            processing_context=input_data.service_type,
            cross_border_transfers=input_data.international_transfers,
            _config=self._runtime_for(input_data, "compliance.pdpl_check"),
        )
        builder.add_result_step(
            step_id="review_privacy_policy",
            title="فحص السياسة المولدة",
            result=pdpl_check_result,
            summary=pdpl_check_result.summary,
        )
        builder.add_generated_artifact(name="policy_text", text=policy_result.policy_text)

        review_notes = self._build_privacy_policy_review_notes(
            policy_result=policy_result,
            pdpl_check_result=pdpl_check_result,
        )
        follow_up_actions = self._unique_strings(pdpl_check_result.required_actions)
        builder.add_synthesis_step(
            step_id="privacy_policy_review_summary",
            title="تلخيص مراجعة السياسة",
            summary=(
                f"تم اشتقاق {len(review_notes)} ملاحظات و"
                f"{len(follow_up_actions)} إجراءات متابعة."
            ),
            output_payload={
                "review_notes": review_notes,
                "follow_up_actions": follow_up_actions,
            },
        )
        return policy_result.policy_text, review_notes, follow_up_actions

    def _build_hr_policy_review_notes(
        self,
        *,
        policy_result: HRPolicyResult,
        summary_result: SummaryResult,
    ) -> list[str]:
        """Collect review notes for the HR-policy branch.

        Args:
            policy_result: Generated HR-policy result.
            summary_result: Summary result produced from the generated policy.

        Returns:
            A deduplicated list of review notes for the branch.

        Raises:
            None.
        """
        return self._unique_strings(
            policy_result.saudi_law_compliance_notes + summary_result.risk_highlights
        )

    def _build_privacy_policy_review_notes(
        self,
        *,
        policy_result: PrivacyPolicyResult,
        pdpl_check_result: PDPLCheckResult,
    ) -> list[str]:
        """Collect review notes for the privacy-policy branch.

        Args:
            policy_result: Generated privacy-policy result.
            pdpl_check_result: PDPL review result for the generated text.

        Returns:
            A deduplicated list of review notes for the branch.

        Raises:
            None.
        """
        return self._unique_strings(policy_result.legal_notes + pdpl_check_result.gaps)

    def _build_executive_summary(
        self,
        *,
        policy_kind: str,
        review_note_count: int,
        action_count: int,
    ) -> str:
        """Summarize the selected policy workflow branch in one paragraph.

        Args:
            policy_kind: Selected policy branch identifier.
            review_note_count: Number of synthesized review notes.
            action_count: Number of synthesized follow-up actions.

        Returns:
            A concise Arabic executive summary for the workflow result.

        Raises:
            None.
        """
        return (
            f"هذا workflow أنشأ مخرجًا من نوع {policy_kind} ثم مرّره على خطوات مراجعة إضافية، "
            f"فنتجت {review_note_count} ملاحظات و{action_count} إجراءات متابعة."
        )

    def _unique_strings(self, values: Iterable[object]) -> list[str]:
        """Deduplicate iterable values after normalizing them into strings.

        Args:
            values: Raw values collected from multiple workflow steps.

        Returns:
            A stable list of unique non-empty string representations.

        Raises:
            None.
        """
        unique_values: list[str] = []
        value: object
        for value in values:
            normalized = str(value).strip()
            if not normalized or normalized in unique_values:
                continue
            unique_values.append(normalized)
        return unique_values
