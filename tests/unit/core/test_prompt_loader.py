from __future__ import annotations

import ast
from pathlib import Path

from qanuni.core.prompt_loader import PromptLoader
from qanuni.legal_references import LegalReferenceLoader, LegalReferenceMode


def test_prompt_loader_renders_sectioned_prompt() -> None:
    """Section-based prompts should load and render into titled text blocks."""
    prompt = PromptLoader.load("contracts/gap_analysis.yaml")
    rendered = prompt.render({"contract_type": "خدمات", "contract_text": "نص عقد تجريبي"})
    assert "# الدور" in rendered.system_prompt
    assert "# المخرجات المطلوبة" in rendered.user_prompt
    assert "# سياسة اللغة" in rendered.system_prompt


def test_prompt_loader_appends_legal_reference_packet_when_requested() -> None:
    """Strict prompt metadata should append the matching legal-reference packet."""
    prompt = PromptLoader.load("drafting/improve.yaml")
    profile = LegalReferenceLoader.load("sa/drafting/legal_language_baseline.yaml")

    rendered = prompt.render(
        {
            "context": "اتفاقية خدمات",
            "improvement_goals": ["clarity", "precision"],
            "original_text": "يدفع المبلغ عند الإنجاز.",
        },
        legal_reference_profile=profile,
    )

    assert rendered.legal_reference_mode == LegalReferenceMode.STRICT
    assert rendered.legal_reference_profile_id == "sa.drafting.legal_language_baseline"
    assert "حزمة المراجع القانونية الملزمة" in rendered.system_prompt
    assert "drafting-preserve-material-meaning" in rendered.system_prompt
    assert "سياق المراجع القانونية" in rendered.user_prompt


def test_all_packaged_prompts_use_sectioned_schema() -> None:
    """Every packaged prompt should declare the richer section-based prompt format."""
    prompt_dir = Path("qanuni/prompts")
    for prompt_file in prompt_dir.rglob("*.yaml"):
        data = ast.literal_eval(
            str(
                {
                    "path": prompt_file.as_posix(),
                    "content": prompt_file.read_text(encoding="utf-8"),
                }
            )
        )
        text = data["content"]
        assert "system_sections:" in text, prompt_file.as_posix()
        assert "user_sections:" in text, prompt_file.as_posix()
