from __future__ import annotations

from qanuni.tools.labor.end_of_service import EndOfServiceTool
from qanuni.tools.labor.probation_check import ProbationCheckTool


def test_end_of_service_tool(config, provider_factory) -> None:
    tool = EndOfServiceTool(config, provider_factory)
    result = tool.run(
        monthly_salary=12000,
        years_of_service=7.5,
        termination_reason="resignation",
        contract_type="indefinite",
    )
    assert result.total_amount == 40000.0
    assert result.tool_id == "labor.end_of_service"
    assert result.model_used == "deterministic"


def test_probation_tool_rejects_excess_without_extension(config, provider_factory) -> None:
    tool = ProbationCheckTool(config, provider_factory)
    result = tool.run(
        probation_duration_days=120,
        contract_type="indefinite",
        written_extension=False,
    )
    assert result.is_legal is False
    assert result.max_allowed_days == 90


def test_probation_tool_accepts_ergonomic_aliases(config, provider_factory) -> None:
    tool = ProbationCheckTool(config, provider_factory)
    result = tool.run(
        probation_days=120,
        extension_in_writing=True,
        prior_service_months=0,
    )
    assert result.is_legal is True
    assert result.max_allowed_days == 180
