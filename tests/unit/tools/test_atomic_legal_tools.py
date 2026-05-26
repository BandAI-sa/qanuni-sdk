from __future__ import annotations

from pathlib import Path

from qanuni.models.common import ToolRuntimeConfig
from qanuni.providers.base_provider import ProviderResponse, ProviderUsage
from qanuni.tools.legal.extract_clauses import ClauseExtractionTool
from qanuni.tools.legal.extract_dates import DateExtractionTool
from qanuni.tools.legal.extract_obligations import ObligationExtractionTool
from qanuni.tools.legal.extract_parties import PartyExtractionTool


def test_clause_extraction_reads_text_file(tmp_path: Path, config, provider_factory) -> None:
    document_file = tmp_path / "agreement.txt"
    document_file.write_text(
        "يتم السداد لاحقًا ويجوز إنهاء العقد عند الحاجة.",
        encoding="utf-8",
    )

    tool = ClauseExtractionTool(config, provider_factory)
    result = tool.run(document_file=str(document_file), document_type="اتفاقية خدمات")

    assert result.extracted_clause_types == ["payment", "termination"]
    assert result.clauses[0].clause_type == "payment"


def test_party_extraction_returns_structured_parties(config, provider_factory) -> None:
    tool = PartyExtractionTool(config, provider_factory)
    result = tool.run(
        document_text="اتفق الطرف الأول شركة ألف مع الطرف الثاني شركة باء.",
        document_type="اتفاقية خدمات",
    )

    assert [party.name for party in result.parties] == ["شركة ألف", "شركة باء"]


def test_date_extraction_returns_normalized_values(config, provider_factory) -> None:
    tool = DateExtractionTool(config, provider_factory)
    result = tool.run(
        document_text="يبدأ نفاذ الاتفاقية في 1 يناير 2026 ويتم السداد خلال 15 يومًا من الفاتورة.",
        document_type="اتفاقية خدمات",
    )

    assert result.dates[0].normalized_value == "2026-01-01"
    assert result.dates[1].date_type == "deadline"


def test_obligation_extraction_returns_directional_records(config, provider_factory) -> None:
    tool = ObligationExtractionTool(config, provider_factory)
    result = tool.run(
        document_text=(
            "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية وفق الجدول الزمني المعتمد. "
            "ويلتزم الطرف الأول بسداد المقابل خلال 15 يومًا بعد استلام الفاتورة."
        ),
        document_type="اتفاقية خدمات",
    )

    assert len(result.obligations) == 2
    assert result.obligations[0].obligated_party == "شركة باء"
    assert result.obligations[1].due_trigger == "خلال 15 يومًا"


def test_obligation_extraction_clamps_runtime_for_compact_structured_output(
    monkeypatch,
    config,
    provider_factory,
) -> None:
    """Atomic extraction should stabilize runtime settings before provider calls.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        config: Shared SDK configuration fixture.
        provider_factory: Mocked provider factory fixture.

    Returns:
        None.

    Raises:
        AssertionError: If runtime stabilization does not clamp verbosity and budgets.
    """
    tool = ObligationExtractionTool(config, provider_factory)
    captured_runtime: ToolRuntimeConfig | None = None

    def fake_call_structured_model(input_data, *, runtime):
        nonlocal captured_runtime
        captured_runtime = runtime
        return ProviderResponse(
            data=tool.OUTPUT_MODEL(obligations=[], summary="ملخص موجز."),
            model="gpt-5-mini",
            usage=ProviderUsage(total_tokens=42),
        )

    monkeypatch.setattr(tool, "_call_structured_model", fake_call_structured_model)

    tool.run(
        document_text="يلتزم الطرف الثاني بالتنفيذ ويلتزم الطرف الأول بالسداد.",
        document_type="اتفاقية خدمات",
        runtime=ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            reasoning_effort="high",
            max_output_tokens=900,
        ),
    )

    assert captured_runtime is not None
    assert captured_runtime.model == "gpt-5-mini"
    assert captured_runtime.verbosity == "low"
    assert captured_runtime.reasoning_effort == "low"
    assert captured_runtime.max_output_tokens == 1800
