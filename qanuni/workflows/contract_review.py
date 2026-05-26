"""Contract-review workflow orchestration."""

from __future__ import annotations

from qanuni.models.contracts import ContractRiskScoreResult, GapAnalysisResult
from qanuni.models.workflows import (
    ContractReviewWorkflowInput,
    ContractReviewWorkflowResult,
    WorkflowState,
)
from qanuni.utils.documents import resolve_document_text
from qanuni.workflows.base import BaseWorkflow
from qanuni.workflows.state import WorkflowStateBuilder


class ContractReviewWorkflow(
    BaseWorkflow[ContractReviewWorkflowInput, ContractReviewWorkflowResult]
):
    """Compose atomic tools into a stronger contract-review workflow."""

    WORKFLOW_ID = "workflow.contract_review"
    INPUT_MODEL = ContractReviewWorkflowInput
    OUTPUT_MODEL = ContractReviewWorkflowResult

    def _run(self, input_data: ContractReviewWorkflowInput) -> ContractReviewWorkflowResult:
        """Execute the contract-review workflow synchronously.

        Args:
            input_data: Parsed workflow input for the current contract-review run.

        Returns:
            A structured contract-review workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        document_text = resolve_document_text(
            text=input_data.document_text,
            file_path=input_data.document_file,
        )
        document_type_hint = input_data.document_type or "مستند تعاقدي"
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

        clause_result = self._client.legal.extract_clauses(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_clauses"),
        )
        builder.add_result_step(
            step_id="extract_clauses",
            title="استخراج البنود",
            result=clause_result,
            summary=clause_result.summary,
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
            title="استخراج المبالغ",
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

        dispute_result = self._client.legal.extract_dispute_resolution(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_dispute_resolution"),
        )
        builder.add_result_step(
            step_id="extract_dispute_resolution",
            title="استخراج مسار فض النزاع",
            result=dispute_result,
            summary=dispute_result.summary,
        )

        contract_type = self._resolve_contract_type(
            input_data=input_data,
            classified_type=classification.primary_document_type.value,
        )
        gap_result = self._client.contracts.gap_analysis(
            contract_text=document_text,
            contract_type=contract_type,
            _config=self._runtime_for(input_data, "contracts.gap_analysis"),
        )
        builder.add_result_step(
            step_id="gap_analysis",
            title="تحليل الثغرات",
            result=gap_result,
            summary=gap_result.summary,
        )

        risk_result = self._client.contracts.risk_score(
            contract_text=document_text,
            contract_type=contract_type,
            _config=self._runtime_for(input_data, "contracts.risk_score"),
        )
        builder.add_result_step(
            step_id="risk_score",
            title="تقييم المخاطر",
            result=risk_result,
            summary=risk_result.summary,
        )

        interim_state = builder.build()
        amendment_recommendations = self._build_amendment_recommendations(
            gap_result=gap_result,
            risk_result=risk_result,
        )
        builder.add_synthesis_step(
            step_id="map_legal_references",
            title="ربط النتيجة بالمراجع",
            summary=(
                f"تم تجميع {len(interim_state.legal_reference_source_ids)} مصدرًا مرجعيًا و"
                f"{len(interim_state.legal_reference_rule_ids)} قاعدة إلزامية عبر الخطوات."
            ),
            output_payload={
                "legal_reference_source_ids": interim_state.legal_reference_source_ids,
                "legal_reference_rule_ids": interim_state.legal_reference_rule_ids,
            },
        )
        builder.add_synthesis_step(
            step_id="recommend_amendments",
            title="اقتراح التعديلات",
            summary=f"تم توليد {len(amendment_recommendations)} توصية تعديل عملية.",
            output_payload={"amendment_recommendations": amendment_recommendations},
        )

        optional_redlines = self._build_optional_redlines(
            gap_result=gap_result,
            include_redlines=input_data.include_redlines,
        )
        if input_data.include_redlines:
            builder.add_synthesis_step(
                step_id="prepare_redlines",
                title="اقتراح redlines",
                summary=f"تم إعداد {len(optional_redlines)} اقتراح redline مبدئي.",
                output_payload={"optional_redlines": optional_redlines},
            )
        else:
            builder.add_skipped_step(
                step_id="prepare_redlines",
                title="اقتراح redlines",
                summary="تم تجاوز redlines لأن include_redlines غير مفعّل.",
            )

        final_state = builder.build()
        return ContractReviewWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                state=final_state,
                gap_result=gap_result,
                risk_result=risk_result,
            ),
            risk_score=risk_result.risk_score,
            risk_level=risk_result.risk_level,
            missing_mandatory_clauses=gap_result.missing_mandatory_clauses,
            amendment_recommendations=amendment_recommendations,
            optional_redlines=optional_redlines,
        )

    async def _arun(
        self,
        input_data: ContractReviewWorkflowInput,
    ) -> ContractReviewWorkflowResult:
        """Execute the contract-review workflow asynchronously.

        Args:
            input_data: Parsed workflow input for the current contract-review run.

        Returns:
            A structured contract-review workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """
        document_text = resolve_document_text(
            text=input_data.document_text,
            file_path=input_data.document_file,
        )
        document_type_hint = input_data.document_type or "مستند تعاقدي"
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

        clause_result = await self._client.legal.aextract_clauses(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_clauses"),
        )
        builder.add_result_step(
            step_id="extract_clauses",
            title="استخراج البنود",
            result=clause_result,
            summary=clause_result.summary,
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
            title="استخراج المبالغ",
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

        dispute_result = await self._client.legal.aextract_dispute_resolution(
            document_text=document_text,
            document_type=document_type_hint,
            _config=self._runtime_for(input_data, "legal.extract_dispute_resolution"),
        )
        builder.add_result_step(
            step_id="extract_dispute_resolution",
            title="استخراج مسار فض النزاع",
            result=dispute_result,
            summary=dispute_result.summary,
        )

        contract_type = self._resolve_contract_type(
            input_data=input_data,
            classified_type=classification.primary_document_type.value,
        )
        gap_result = await self._client.contracts.agap_analysis(
            contract_text=document_text,
            contract_type=contract_type,
            _config=self._runtime_for(input_data, "contracts.gap_analysis"),
        )
        builder.add_result_step(
            step_id="gap_analysis",
            title="تحليل الثغرات",
            result=gap_result,
            summary=gap_result.summary,
        )

        risk_result = await self._client.contracts.arisk_score(
            contract_text=document_text,
            contract_type=contract_type,
            _config=self._runtime_for(input_data, "contracts.risk_score"),
        )
        builder.add_result_step(
            step_id="risk_score",
            title="تقييم المخاطر",
            result=risk_result,
            summary=risk_result.summary,
        )

        interim_state = builder.build()
        amendment_recommendations = self._build_amendment_recommendations(
            gap_result=gap_result,
            risk_result=risk_result,
        )
        builder.add_synthesis_step(
            step_id="map_legal_references",
            title="ربط النتيجة بالمراجع",
            summary=(
                f"تم تجميع {len(interim_state.legal_reference_source_ids)} مصدرًا مرجعيًا و"
                f"{len(interim_state.legal_reference_rule_ids)} قاعدة إلزامية عبر الخطوات."
            ),
            output_payload={
                "legal_reference_source_ids": interim_state.legal_reference_source_ids,
                "legal_reference_rule_ids": interim_state.legal_reference_rule_ids,
            },
        )
        builder.add_synthesis_step(
            step_id="recommend_amendments",
            title="اقتراح التعديلات",
            summary=f"تم توليد {len(amendment_recommendations)} توصية تعديل عملية.",
            output_payload={"amendment_recommendations": amendment_recommendations},
        )

        optional_redlines = self._build_optional_redlines(
            gap_result=gap_result,
            include_redlines=input_data.include_redlines,
        )
        if input_data.include_redlines:
            builder.add_synthesis_step(
                step_id="prepare_redlines",
                title="اقتراح redlines",
                summary=f"تم إعداد {len(optional_redlines)} اقتراح redline مبدئي.",
                output_payload={"optional_redlines": optional_redlines},
            )
        else:
            builder.add_skipped_step(
                step_id="prepare_redlines",
                title="اقتراح redlines",
                summary="تم تجاوز redlines لأن include_redlines غير مفعّل.",
            )

        final_state = builder.build()
        return ContractReviewWorkflowResult(
            state=final_state,
            executive_summary=self._build_executive_summary(
                state=final_state,
                gap_result=gap_result,
                risk_result=risk_result,
            ),
            risk_score=risk_result.risk_score,
            risk_level=risk_result.risk_level,
            missing_mandatory_clauses=gap_result.missing_mandatory_clauses,
            amendment_recommendations=amendment_recommendations,
            optional_redlines=optional_redlines,
        )

    def _resolve_contract_type(
        self,
        *,
        input_data: ContractReviewWorkflowInput,
        classified_type: str,
    ) -> str:
        """Resolve the contract type used by downstream contract tools.

        Args:
            input_data: Parsed workflow input for the current review.
            classified_type: Normalized type inferred by the classifier step.

        Returns:
            The best contract-type label available for orchestration.

        Raises:
            None.
        """
        if input_data.contract_type:
            return input_data.contract_type
        if classified_type != "unknown":
            return classified_type
        return input_data.document_type or "service_agreement"

    def _build_amendment_recommendations(
        self,
        *,
        gap_result: GapAnalysisResult,
        risk_result: ContractRiskScoreResult,
    ) -> list[str]:
        """Merge gap and risk findings into practical amendment actions.

        Args:
            gap_result: Gap-analysis output for the current contract.
            risk_result: Risk-score output for the current contract.

        Returns:
            A deduplicated list of amendment recommendations.

        Raises:
            None.
        """
        recommendations = list(risk_result.mitigation_priorities)
        recommendations.extend(
            f"أضف بندًا صريحًا يغطي {clause_name}."
            for clause_name in gap_result.missing_mandatory_clauses
        )
        recommendations.extend(
            ambiguous_clause.suggested_rewrite
            for ambiguous_clause in gap_result.ambiguous_clauses
        )
        return self._unique_strings(recommendations)

    def _build_optional_redlines(
        self,
        *,
        gap_result: GapAnalysisResult,
        include_redlines: bool,
    ) -> list[str]:
        """Prepare lightweight redline hints when the caller asks for them.

        Args:
            gap_result: Gap-analysis output for the current contract.
            include_redlines: Whether the workflow should emit redline suggestions.

        Returns:
            A list of redline-like replacement suggestions.

        Raises:
            None.
        """
        if not include_redlines:
            return []
        return [
            f"من: {item.excerpt} | إلى: {item.suggested_rewrite}"
            for item in gap_result.ambiguous_clauses
        ]

    def _build_executive_summary(
        self,
        *,
        state: WorkflowState,
        gap_result: GapAnalysisResult,
        risk_result: ContractRiskScoreResult,
    ) -> str:
        """Summarize why the workflow result is stronger than one isolated tool.

        Args:
            state: Final shared workflow state accumulated across steps.
            gap_result: Gap-analysis output for the current contract.
            risk_result: Risk-score output for the current contract.

        Returns:
            A compact Arabic executive summary for the full review.

        Raises:
            None.
        """
        primary_type = (
            state.primary_document_type.value
            if state.primary_document_type is not None
            else "unknown"
        )
        return (
            f"تمت مراجعة مستند من نوع {primary_type} عبر {len(state.steps)} خطوة. "
            "مستوى المخاطر الحالي "
            f"{risk_result.risk_level} بدرجة {risk_result.risk_score:.0f}/100، "
            f"مع {len(gap_result.missing_mandatory_clauses)} بنود إلزامية مفقودة و"
            f"{len(state.extracted_obligations)} التزامات مستخرجة تدعم فهم التوزيع العملي للمخاطر."
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
