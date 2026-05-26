from __future__ import annotations

from pathlib import Path

from qanuni.core.config import QanuniConfig
from qanuni.tools.compliance.demand_letter import DemandLetterTool
from qanuni.tools.compliance.privacy_policy import PrivacyPolicyGeneratorTool
from qanuni.tools.contracts.gap_analysis import ContractGapAnalysisTool
from qanuni.tools.contracts.mou_generator import MOUGeneratorTool
from qanuni.tools.contracts.nda_generator import NDAGeneratorTool
from qanuni.tools.drafting.improve import ImproveTextTool
from qanuni.tools.drafting.simplify import SimplifyLegalTextTool
from qanuni.tools.drafting.summarize import SummarizeLegalDocumentTool
from qanuni.tools.policies.hr_policy import HRPolicyGeneratorTool
from qanuni.tools.policies.job_description import JobDescriptionGeneratorTool


def test_contract_gap_analysis_reads_text_file(tmp_path: Path, config, provider_factory) -> None:
    contract_file = tmp_path / "contract.txt"
    contract_file.write_text("نص عقد عربي", encoding="utf-8")

    tool = ContractGapAnalysisTool(config, provider_factory)
    result = tool.run(contract_file=str(contract_file), contract_type="خدمات")

    assert result.overall_risk_level == "high"
    assert result.tokens_used == 321
    assert result.model_used == "gpt-5-mini"


def test_improve_text_tool_returns_structured_result(config, provider_factory) -> None:
    tool = ImproveTextTool(config, provider_factory)
    result = tool.run(
        original_text="يدفع المبلغ عند الإنجاز",
        improvement_goals=["precision", "formality"],
        context="اتفاقية خدمات",
    )
    assert result.improvement_score == 88.0
    assert len(result.changes) == 1


def test_summarize_tool_supports_text_input(config, provider_factory) -> None:
    tool = SummarizeLegalDocumentTool(config, provider_factory)
    result = tool.run(
        document_text="محتوى عقد طويل",
        summary_length="executive",
    )
    assert result.summary.startswith("الملخص التنفيذي")


def test_simplify_tool_returns_reader_warning(config, provider_factory) -> None:
    tool = SimplifyLegalTextTool(config, provider_factory)
    result = tool.run(legal_text="شرط عدم منافسة معقد")
    assert result.reader_warnings


def test_privacy_policy_tool_returns_sections(config, provider_factory) -> None:
    tool = PrivacyPolicyGeneratorTool(config, provider_factory)
    result = tool.run(
        company_name="BandAI",
        service_type="SaaS",
        data_collected=["name", "email"],
        data_purposes=["service delivery"],
        third_party_sharing=False,
        international_transfers=False,
    )
    assert "الحقوق" in result.sections_included


def test_nda_generator_returns_clause_summary(config, provider_factory) -> None:
    """The NDA tool should expose key clause summaries for downstream use."""
    tool = NDAGeneratorTool(config, provider_factory)
    result = tool.run(
        nda_type="mutual",
        disclosing_party="BandAI",
        receiving_party="ClientCo",
        purpose="مناقشة مشروع تجريبي",
        confidentiality_period_years=3,
    )
    assert result.key_clauses_summary


def test_global_model_preference_overrides_prompt_default(provider_factory) -> None:
    """A configured client model should beat prompt-file defaults for live tools."""
    config = QanuniConfig(_env_file=None, api_key="sk-test", model="gpt-5-mini", tool_overrides={})
    tool = NDAGeneratorTool(config, provider_factory)

    result = tool.run(
        nda_type="mutual",
        disclosing_party="BandAI",
        receiving_party="ClientCo",
        purpose="مراجعة التكامل",
        confidentiality_period_years=3,
    )

    assert result.model_used == "gpt-5-mini"


def test_mou_generator_returns_binding_clauses(config, provider_factory) -> None:
    """The MOU tool should identify binding sections explicitly."""
    tool = MOUGeneratorTool(config, provider_factory)
    result = tool.run(
        party_a="BandAI",
        party_b="ClientCo",
        objectives=["تعاون", "تكامل"],
        responsibilities=["مشاركة المتطلبات", "تقييم التجربة"],
    )
    assert "السرية" in result.binding_clauses


def test_demand_letter_tool_returns_notice_elements(config, provider_factory) -> None:
    """The demand-letter tool should surface included notice components."""
    tool = DemandLetterTool(config, provider_factory)
    result = tool.run(
        sender_name="BandAI",
        recipient_name="ClientCo",
        claim_type="سداد",
        claim_amount=25000.0,
        incident_description="فاتورة مستحقة غير مسددة مقابل خدمات تنفيذ.",
        deadline_days=10,
        threat_of_action="إجراءات قضائية",
    )
    assert "المهلة" in result.legal_notice_elements


def test_hr_policy_tool_returns_compliance_notes(config, provider_factory) -> None:
    tool = HRPolicyGeneratorTool(config, provider_factory)
    result = tool.run(
        policy_type="leave_policy",
        company_name="BandAI",
        industry="technology",
        employee_count=25,
    )
    assert result.mandatory_inclusions_met is True


def test_job_description_tool_returns_saudization_statement(config, provider_factory) -> None:
    tool = JobDescriptionGeneratorTool(config, provider_factory)
    result = tool.run(
        job_title="مدير مبيعات",
        department="المبيعات",
        required_experience_years=5,
        required_education="درجة البكالوريوس",
        key_responsibilities=["بناء خط مبيعات"],
        required_skills=["التفاوض"],
        saudization_preferred=True,
    )
    assert result.saudization_statement is not None
