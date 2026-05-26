from __future__ import annotations

from qanuni import LegalClient
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.workflows import ContractReviewWorkflowInput, PreLitigationNoticeWorkflowInput


def test_client_exposes_workflow_namespace(provider_factory) -> None:
    """The client should expose the new workflow namespace lazily."""
    client = LegalClient(provider_factory=provider_factory)

    result = client.workflow.contract_review(
        document_text="يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        contract_type="service_agreement",
    )

    assert result.state.steps


def test_contract_review_workflow_is_stronger_than_gap_analysis(provider_factory) -> None:
    """Contract review should orchestrate more signal than gap analysis alone."""
    client = LegalClient(provider_factory=provider_factory)
    document_text = """
    يلتزم الطرف الثاني بتنفيذ الأعمال،
    ويتم السداد لاحقًا وفق ما يراه الطرف الأول مناسبًا،
    ويجوز إنهاء العقد عند الحاجة.
    """

    gap_result = client.contracts.gap_analysis(
        contract_text=document_text,
        contract_type="service_agreement",
    )
    workflow_result = client.workflow.contract_review(
        document_text=document_text,
        contract_type="service_agreement",
        include_redlines=True,
    )

    assert len(workflow_result.state.steps) >= 12
    assert workflow_result.state.primary_document_type is not None
    assert workflow_result.amendment_recommendations
    assert workflow_result.optional_redlines
    assert len(workflow_result.state.findings) > len(gap_result.findings)
    assert "extract_obligations" in {step.step_id for step in workflow_result.state.steps}
    assert "risk_score" in {step.step_id for step in workflow_result.state.steps}


def test_contract_review_clamps_internal_analysis_runtime(provider_factory) -> None:
    """Shared runtime should not inflate internal structured-analysis tool calls.

    Args:
        provider_factory: Mocked provider factory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If internal runtime policy stops forcing compact analysis settings.
    """
    client = LegalClient(provider_factory=provider_factory)
    workflow = client.workflow._contract_review
    input_data = ContractReviewWorkflowInput(
        document_text="يتضمن العقد سدادًا وإنهاءً والتزامات تشغيلية.",
        shared_runtime=ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            reasoning_effort="high",
            max_output_tokens=900,
        ),
    )

    legal_runtime = workflow._runtime_for(input_data, "legal.extract_obligations")
    gap_runtime = workflow._runtime_for(input_data, "contracts.gap_analysis")
    generator_runtime = workflow._runtime_for(input_data, "compliance.demand_letter")

    assert legal_runtime is not None
    assert legal_runtime.verbosity == "low"
    assert legal_runtime.reasoning_effort == "low"
    assert legal_runtime.max_output_tokens == 1800

    assert gap_runtime is not None
    assert gap_runtime.verbosity == "low"
    assert gap_runtime.reasoning_effort == "low"
    assert gap_runtime.max_output_tokens == 1800

    assert generator_runtime is not None
    assert generator_runtime.verbosity == "high"
    assert generator_runtime.reasoning_effort == "high"
    assert generator_runtime.max_output_tokens == 900


def test_pre_litigation_notice_clamps_internal_improvement_runtime(provider_factory) -> None:
    """Shared runtime should not inflate internal drafting-improvement calls.

    Args:
        provider_factory: Mocked provider factory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If internal drafting hardening stops applying.
    """
    client = LegalClient(provider_factory=provider_factory)
    workflow = client.workflow._pre_litigation_notice
    input_data = PreLitigationNoticeWorkflowInput(
        sender_name="شركة ألف",
        recipient_name="شركة باء",
        claim_type="مستحقات تعاقدية",
        incident_description="تأخر السداد رغم المطالبات السابقة.",
        deadline_days=7,
        threat_of_action="سيتم اتخاذ الإجراءات القانونية المناسبة.",
        shared_runtime=ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            reasoning_effort="high",
            max_output_tokens=1200,
        ),
    )

    improvement_runtime = workflow._runtime_for(input_data, "drafting.improve")
    generator_runtime = workflow._runtime_for(input_data, "compliance.demand_letter")

    assert improvement_runtime is not None
    assert improvement_runtime.verbosity == "low"
    assert improvement_runtime.reasoning_effort == "low"
    assert improvement_runtime.max_output_tokens == 2600

    assert generator_runtime is not None
    assert generator_runtime.verbosity == "high"
    assert generator_runtime.reasoning_effort == "high"
    assert generator_runtime.max_output_tokens == 1200


def test_employment_review_workflow_runs_probation_and_end_of_service(provider_factory) -> None:
    """Employment review should combine document analysis with labor calculators."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.workflow.employment_review(
        document_text="عقد عمل يتضمن التزامات وساعات عمل وشرط إنهاء.",
        probation_days=120,
        extension_in_writing=False,
        monthly_salary=12000.0,
        years_of_service=3.5,
        termination_reason="contract_completion",
        contract_type="indefinite",
    )

    assert result.probation_status == "violation"
    assert result.end_of_service_amount is not None
    assert "probation_check" in {step.step_id for step in result.state.steps}
    assert "end_of_service" in {step.step_id for step in result.state.steps}


def test_privacy_compliance_review_can_generate_and_recheck_policy(provider_factory) -> None:
    """Privacy review should optionally generate a remediation draft and re-check it."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.workflow.privacy_compliance_review(
        document_text="توضح السياسة أغراض المعالجة دون آلية لطلبات أصحاب البيانات.",
        processing_context="منصة خدمات رقمية",
        generate_policy_draft=True,
        company_name="شركة ألف",
        service_type="منصة تقنية",
    )

    assert result.policy_draft_text is not None
    assert "policy_draft" in result.state.generated_artifacts
    assert "pdpl_check_generated" in {step.step_id for step in result.state.steps}
    assert result.remediation_priorities


def test_pre_litigation_notice_workflow_returns_improved_letter(provider_factory) -> None:
    """Pre-litigation workflow should enrich and improve the generated demand letter."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.workflow.pre_litigation_notice(
        support_document_text=(
            "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية، "
            "ويلتزم الطرف الأول بسداد 25,000 ريال خلال 15 يومًا."
        ),
        sender_name="شركة ألف",
        recipient_name="شركة باء",
        claim_type="مستحقات تعاقدية",
        claim_amount=85000.0,
        incident_description="تأخر في سداد مستحقات عقد خدمات تقنية.",
        deadline_days=7,
        threat_of_action="سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
    )

    assert result.demand_letter_text
    assert result.claim_support_summary
    assert "improve_demand_letter" in {step.step_id for step in result.state.steps}


def test_policy_generation_review_supports_hr_policy_path(provider_factory) -> None:
    """Policy-generation review should support the HR-policy branch."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.workflow.policy_generation_review(
        policy_kind="hr_policy",
        policy_type="disciplinary_policy",
        company_name="شركة ألف",
        industry="تقنية",
        employee_count=50,
    )

    assert result.generated_text
    assert result.review_notes
    assert "summarize_policy" in {step.step_id for step in result.state.steps}


def test_policy_generation_review_supports_privacy_policy_path(provider_factory) -> None:
    """Policy-generation review should support the privacy-policy branch."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.workflow.policy_generation_review(
        policy_kind="privacy_policy",
        company_name="شركة ألف",
        service_type="منصة تقنية",
    )

    assert result.generated_text
    assert result.follow_up_actions
    assert "review_privacy_policy" in {step.step_id for step in result.state.steps}


def test_policy_generation_review_supports_job_description_path(provider_factory) -> None:
    """Policy-generation review should support the job-description branch."""
    client = LegalClient(provider_factory=provider_factory)
    result = client.workflow.policy_generation_review(
        policy_kind="job_description",
        job_title="محلل أعمال",
        department="العمليات",
        required_experience_years=3,
        required_education="بكالوريوس إدارة أعمال",
    )

    assert result.generated_text
    assert result.review_notes
    assert "improve_job_description" in {step.step_id for step in result.state.steps}


def test_phase_three_workflows_share_one_state_contract(provider_factory) -> None:
    """Every workflow should return the same normalized workflow-state shape."""
    client = LegalClient(provider_factory=provider_factory)

    results = [
        client.workflow.contract_review(
            document_text="يتم السداد خلال 15 يومًا ويجوز إنهاء العقد بعد إشعار مكتوب.",
            contract_type="service_agreement",
        ),
        client.workflow.employment_review(
            document_text="عقد عمل يحدد الراتب والمهام والإجازات وإنهاء الخدمة.",
            probation_days=90,
            contract_type="indefinite",
        ),
        client.workflow.privacy_compliance_review(
            document_text="توضح السياسة أغراض المعالجة وحقوق أصحاب البيانات.",
            processing_context="منصة رقمية",
        ),
        client.workflow.pre_litigation_notice(
            sender_name="شركة ألف",
            recipient_name="شركة باء",
            claim_type="مستحقات تعاقدية",
            incident_description="تأخر السداد رغم المطالبات السابقة.",
            deadline_days=5,
            threat_of_action="سيتم اتخاذ الإجراءات القانونية المناسبة.",
        ),
        client.workflow.policy_generation_review(
            policy_kind="privacy_policy",
            company_name="شركة ألف",
            service_type="منصة تقنية",
        ),
    ]

    result: object
    for result in results:
        state = result.state
        assert state.workflow_id.startswith("workflow.")
        assert state.steps
        assert isinstance(state.step_outputs, dict)
        assert isinstance(state.legal_reference_source_ids, list)
        assert isinstance(state.findings, list)
        assert isinstance(state.recommended_actions, list)
