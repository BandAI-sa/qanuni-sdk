"""Comprehensive runnable examples for the free Qanuni SDK distribution."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qanuni import LegalClient
from qanuni.core.exceptions import QanuniError
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.compliance import DemandLetterResult, PrivacyPolicyResult
from qanuni.models.contracts import GapAnalysisResult, MOUResult, NDAResult
from qanuni.models.drafting import SimplifyResult, SummaryResult, TextImprovementResult
from qanuni.models.legal import (
    ClauseExtractionResult,
    DateExtractionResult,
    ObligationExtractionResult,
    PartyExtractionResult,
)
from qanuni.models.policies import HRPolicyResult, JobDescriptionResult
from qanuni.providers import StaticProvider

PROJECT_ROOT: Path = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_dotenv_file() -> None:
    """Populate process environment variables from a local `.env` file when present.

    Args:
        None.

    Returns:
        None.

    Raises:
        OSError: If a discovered `.env` file cannot be read.
    """
    candidate_paths: tuple[Path, ...] = (
        Path.cwd() / ".env",
        PROJECT_ROOT / ".env",
    )
    for candidate_path in candidate_paths:
        if not candidate_path.exists():
            continue
        for raw_line in candidate_path.read_text(encoding="utf-8").splitlines():
            line: str = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv_file()


@dataclass(frozen=True, slots=True)
class ExampleSpec:
    """Describe a single example or experiment in this file.

    Args:
        name: Stable example identifier used from the CLI.
        category: High-level grouping label for discovery output.
        description: Human-readable explanation of what the example demonstrates.
        runner: Zero-argument callable that executes the example.
        requires_openai: Whether the example requires `OPENAI_API_KEY`.

    Returns:
        None.

    Raises:
        None.
    """

    name: str
    category: str
    description: str
    runner: Callable[[], None]
    requires_openai: bool = False


def _print_header(title: str) -> None:
    """Print a readable section title.

    Args:
        title: Section title to print.

    Returns:
        None.

    Raises:
        None.
    """
    separator: str = "=" * len(title)
    print(f"\n{title}\n{separator}")


def _print_payload(label: str, payload: Any) -> None:
    """Pretty-print example output in JSON-friendly form.

    Args:
        label: Output section title.
        payload: Serializable payload or Pydantic model instance to display.

    Returns:
        None.

    Raises:
        TypeError: If the payload contains values that cannot be serialized.
    """
    _print_header(label)
    normalized_payload: Any = (
        payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    )
    print(json.dumps(normalized_payload, ensure_ascii=False, indent=2, default=str))


def _print_error(label: str, error: QanuniError) -> None:
    """Print a structured Qanuni error payload.

    Args:
        label: Output section title.
        error: Structured SDK error instance.

    Returns:
        None.

    Raises:
        TypeError: If error details contain non-serializable values.
    """
    _print_payload(
        label,
        {
            "error_code": str(error.error_code),
            "message": str(error),
            "details": error.details,
        },
    )


def _require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error.

    Args:
        name: Environment-variable name to read.

    Returns:
        The resolved environment-variable value.

    Raises:
        RuntimeError: If the requested variable is missing or blank.
    """
    value: str = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable '{name}' is required for this example.")
    return value


@contextmanager
def without_openai_api_key() -> Iterator[None]:
    """Temporarily remove `OPENAI_API_KEY` and hide local `.env` files.

    Args:
        None.

    Returns:
        An iterator context used by `with`.

    Raises:
        None.
    """
    original_cwd: Path = Path.cwd()
    original_value: str | None = os.environ.get("OPENAI_API_KEY")
    had_key: bool = "OPENAI_API_KEY" in os.environ
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ.pop("OPENAI_API_KEY", None)
        os.chdir(temp_dir)
        try:
            yield
        finally:
            os.chdir(original_cwd)
            if had_key and original_value is not None:
                os.environ["OPENAI_API_KEY"] = original_value
            else:
                os.environ.pop("OPENAI_API_KEY", None)


def _build_static_provider() -> StaticProvider:
    """Return a deterministic local provider used by mocked examples.

    Args:
        None.

    Returns:
        A deterministic provider with canned Arabic outputs.

    Raises:
        None.
    """
    return StaticProvider(
        responses={
            GapAnalysisResult: {
                "gaps": [
                    {
                        "clause": "بند حدود المسؤولية غير مذكور.",
                        "severity": "high",
                        "recommendation": "أضف بندًا يحدد سقف المسؤولية والاستثناءات بوضوح.",
                    }
                ],
                "overall_risk_level": "high",
                "missing_mandatory_clauses": ["القانون الحاكم", "آلية فض النزاع"],
                "ambiguous_clauses": [
                    {
                        "excerpt": "يتم السداد لاحقًا.",
                        "reason": "العبارة لا تحدد موعدًا واضحًا للسداد.",
                        "suggested_rewrite": "يتم السداد خلال 15 يومًا من تاريخ الفاتورة.",
                    }
                ],
                "compliance_score": 63.0,
                "summary": "العقد يحتاج إلى حماية أوضح في الدفع والمسؤولية وتسوية النزاعات.",
            },
            ClauseExtractionResult: {
                "clauses": [
                    {
                        "clause_id": "clause_payment_1",
                        "clause_type": "payment",
                        "heading": "السداد",
                        "summary": "يتناول النص آلية السداد بصورة مختصرة.",
                        "excerpt": "يتم السداد لاحقًا وفق الفاتورة.",
                        "importance": "high",
                        "is_mandatory_context": True,
                    },
                    {
                        "clause_id": "clause_termination_1",
                        "clause_type": "termination",
                        "heading": "إنهاء العقد",
                        "summary": "يسمح النص بإنهاء التعاقد عند الحاجة.",
                        "excerpt": "ويجوز إنهاء العقد عند الحاجة.",
                        "importance": "medium",
                        "is_mandatory_context": True,
                    },
                ],
                "extracted_clause_types": ["payment", "termination"],
                "summary": "تم التقاط بندي السداد والإنهاء كمحاور رئيسية في النص.",
            },
            PartyExtractionResult: {
                "parties": [
                    {
                        "party_id": "party_1",
                        "name": "شركة ألف",
                        "normalized_role": "party_a",
                        "role_label": "الطرف الأول",
                        "source_excerpt": "اتفق الطرف الأول شركة ألف مع الطرف الثاني شركة باء.",
                    },
                    {
                        "party_id": "party_2",
                        "name": "شركة باء",
                        "normalized_role": "party_b",
                        "role_label": "الطرف الثاني",
                        "source_excerpt": "اتفق الطرف الأول شركة ألف مع الطرف الثاني شركة باء.",
                    },
                ],
                "summary": "تم تحديد طرفين رئيسيين في المستند.",
            },
            DateExtractionResult: {
                "dates": [
                    {
                        "date_id": "date_1",
                        "date_type": "effective_date",
                        "label": "تاريخ النفاذ",
                        "raw_value": "1 يناير 2026",
                        "normalized_value": "2026-01-01",
                        "source_excerpt": "يبدأ نفاذ الاتفاقية في 1 يناير 2026.",
                    },
                    {
                        "date_id": "date_2",
                        "date_type": "deadline",
                        "label": "مهلة السداد",
                        "raw_value": "خلال 15 يومًا",
                        "normalized_value": None,
                        "source_excerpt": "يتم السداد خلال 15 يومًا من الفاتورة.",
                    },
                ],
                "summary": "تم استخراج تاريخ نفاذ ومهلة سداد تشغيلية.",
            },
            ObligationExtractionResult: {
                "obligations": [
                    {
                        "obligation_id": "obl_1",
                        "direction": "owed_by",
                        "obligated_party": "شركة باء",
                        "beneficiary_party": "شركة ألف",
                        "action": "تنفيذ الأعمال التقنية المتفق عليها",
                        "condition": None,
                        "due_trigger": "وفق الجدول الزمني المعتمد",
                        "source_excerpt": (
                            "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية وفق الجدول الزمني المعتمد."
                        ),
                    },
                    {
                        "obligation_id": "obl_2",
                        "direction": "owed_by",
                        "obligated_party": "شركة ألف",
                        "beneficiary_party": "شركة باء",
                        "action": "سداد المقابل المالي",
                        "condition": "بعد استلام الفاتورة",
                        "due_trigger": "خلال 15 يومًا",
                        "source_excerpt": (
                            "يلتزم الطرف الأول بسداد المقابل خلال 15 يومًا بعد استلام الفاتورة."
                        ),
                    },
                ],
                "summary": "تم توزيع الالتزامات الأساسية بين التنفيذ والسداد.",
            },
            NDAResult: {
                "nda_text": "اتفاقية عدم إفصاح عربية متوازنة بين الطرفين.",
                "key_clauses_summary": ["التعريفات", "مدة السرية", "الاستثناءات"],
                "legal_notes": ["يفضل تضييق تعريف المعلومات السرية إذا كان نطاق المشروع محددًا."],
            },
            MOUResult: {
                "mou_text": "مذكرة تفاهم عربية توضح الأهداف والنطاق والأحكام غير الملزمة.",
                "binding_clauses": ["السرية", "القانون الحاكم"],
                "caution_notes": ["الالتزامات النهائية يجب نقلها إلى عقد تفصيلي ملزم."],
            },
            TextImprovementResult: {
                "improved_text": (
                    "يلتزم الطرف الأول بسداد المقابل خلال خمسة عشر يومًا "
                    "من تاريخ الفاتورة."
                ),
                "changes": [
                    {
                        "original": "يدفع الطرف الأول عند الإنجاز.",
                        "improved": (
                            "يلتزم الطرف الأول بسداد المقابل خلال خمسة عشر يومًا "
                            "من تاريخ الفاتورة."
                        ),
                        "reason": "إضافة مدة محددة وصياغة أكثر قابلية للتنفيذ.",
                    }
                ],
                "overall_assessment": "الصياغة أصبحت أوضح وأكثر دقة.",
                "improvement_score": 89.0,
            },
            SummaryResult: {
                "summary": "الملخص التنفيذي: المستند يركز على الالتزامات المالية والإنهاء.",
                "key_obligations": ["تنفيذ الخدمة", "سداد الفواتير"],
                "key_rights": ["إنهاء العقد عند الإخلال"],
                "key_dates": [{"label": "التجديد", "value": "2026-12-31"}],
                "financial_terms": ["12000 ريال شهريًا"],
                "risk_highlights": ["لا توجد آلية تفصيلية لإدارة التغيير."],
            },
            SimplifyResult: {
                "simplified_text": (
                    "هذا البند يعني أنك لا تستطيع منافسة الطرف الآخر "
                    "خلال المدة المذكورة في العقد."
                ),
                "preserved_terms": ["عدم المنافسة", "المدة"],
                "reader_warnings": ["قد تبقى قابلية التطبيق مرتبطة بظروف العقد والنظام السعودي."],
            },
            PrivacyPolicyResult: {
                "policy_text": "سياسة خصوصية عربية تراعي الغرض من المعالجة وحقوق أصحاب البيانات.",
                "pdpl_compliance_score": 91.0,
                "sections_included": ["جمع البيانات", "أغراض المعالجة", "الحقوق", "الاحتفاظ"],
                "legal_notes": ["أضف قناة تشغيلية واضحة لاستقبال طلبات الخصوصية إن كانت متاحة."],
            },
            DemandLetterResult: {
                "letter_text": "خطاب مطالبة قانونية عربي قبل اتخاذ إجراءات تصعيدية.",
                "legal_notice_elements": ["الأطراف", "الوقائع", "المطالبة", "المهلة"],
                "strategic_notes": ["يفضل إرفاق ما يثبت أصل الالتزام قبل الإرسال النهائي."],
            },
            HRPolicyResult: {
                "policy_text": "سياسة موارد بشرية عربية ملائمة لبيئة عمل سعودية.",
                "saudi_law_compliance_notes": [
                    "أضف مسارًا واضحًا للتدرج التأديبي والاعتماد الداخلي."
                ],
                "mandatory_inclusions_met": True,
                "recommended_additions": ["حدد جهة الاعتماد النهائية داخل الشركة."],
            },
            JobDescriptionResult: {
                "job_description_text": "وصف وظيفي عربي مهني يوضح المسؤوليات والمتطلبات.",
                "discriminatory_language_flags": [],
                "saudization_statement": (
                    "تخضع الوظيفة لمتطلبات التوطين متى انطبقت المعايير النظامية."
                ),
                "legal_compliance_notes": ["تجنب أي اشتراط تمييزي غير مبرر نظاميًا."],
            },
        },
        default_model="static://examples",
    )


# هذا العميل مناسب للأدوات الحتمية مثل حساب مكافأة نهاية الخدمة.
# أهميته أنه يوضح أن بعض أدوات المكتبة تعمل بالكامل دون OpenAI أو أي خدمة خارجية.
def build_local_client() -> LegalClient:
    """Return a client for deterministic local tools.

    Args:
        None.

    Returns:
        A client configured with default local settings.

    Raises:
        QanuniConfigError: If the default configuration is invalid.
    """
    return LegalClient()


# هذا العميل هو المسار الطبيعي للأدوات المعتمدة على النماذج اللغوية.
# أهميته أنه يحاكي تجربة المستخدم الحقيقية بعد تثبيت الحزمة وإضافة مفتاح OpenAI فقط.
def build_openai_client() -> LegalClient:
    """Return a client configured for live OpenAI-backed examples.

    Args:
        None.

    Returns:
        A client configured with the user's OpenAI API key.

    Raises:
        RuntimeError: If `OPENAI_API_KEY` is missing.
        QanuniConfigError: If the SDK configuration is invalid.
    """
    return LegalClient(api_key=_require_env("OPENAI_API_KEY"))


# هذا العميل يتيح تجربة معظم الأدوات محليًا دون تكلفة.
# أهميته كبيرة لصاحب المنتج أو المطور الذي يريد استعراض السلوك وبناء الشروحات والاختبارات.
def build_mocked_client() -> LegalClient:
    """Return a client backed by a local deterministic provider.

    Args:
        None.

    Returns:
        A client using `StaticProvider` for predictable Arabic responses.

    Raises:
        QanuniConfigError: If the SDK configuration is invalid.
    """
    return LegalClient(provider_factory=_build_static_provider)


def example_list_tools() -> None:
    """List all shipped tools in the free distribution.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    client: LegalClient = build_local_client()
    payload: list[dict[str, Any]] = [
        tool.model_dump() if hasattr(tool, "model_dump") else tool.__dict__
        for tool in client.list_tools()
    ]
    _print_payload("كل الأدوات المتاحة", payload)


def example_list_tool_access() -> None:
    """List tool availability states for the free distribution.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    client: LegalClient = build_local_client()
    payload: list[dict[str, Any]] = [
        status.model_dump() if hasattr(status, "model_dump") else status.__dict__
        for status in client.list_tool_access()
    ]
    _print_payload("حالة الوصول إلى الأدوات", payload)


def example_labor_end_of_service() -> None:
    """Run the deterministic end-of-service calculator.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_local_client()
    result = client.labor.end_of_service(
        monthly_salary=12000,
        years_of_service=7.5,
        termination_reason="resignation",
        contract_type="indefinite",
    )
    _print_payload("مكافأة نهاية الخدمة", result)


def example_labor_probation_check() -> None:
    """Validate a Saudi probation-period scenario.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_local_client()
    result = client.labor.probation_check(
        probation_days=120,
        extension_in_writing=True,
    )
    _print_payload("فحص فترة التجربة", result)


# هذا المثال يوضح كيف نستخرج خريطة البنود قبل أي تقييم مخاطر أو توليد لاحق.
# أهميته أنه يمثل لبنة أولية سيعتمد عليها الـ agent لاحقًا بدل قراءة النص الخام كل مرة.
def example_legal_extract_clauses_mocked() -> None:
    """Extract clause units with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.legal.extract_clauses(
        document_text="يتم السداد لاحقًا وفق الفاتورة، ويجوز إنهاء العقد عند الحاجة.",
        document_type="اتفاقية خدمات",
    )
    _print_payload("استخراج البنود - محلي", result)


# هذا المثال يوضح كيف نحدد الأطراف ككائنات مستقلة قابلة لإعادة الاستخدام.
# أهميته كبيرة في workflows المقارنة، وتوليد الخطابات، وربط الالتزامات بالأطراف الصحيحة.
def example_legal_extract_parties_mocked() -> None:
    """Extract parties with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.legal.extract_parties(
        document_text="اتفق الطرف الأول شركة ألف مع الطرف الثاني شركة باء على تنفيذ الأعمال.",
        document_type="اتفاقية خدمات",
    )
    _print_payload("استخراج الأطراف - محلي", result)


# هذا المثال يوضح تحويل المهل والتواريخ إلى عناصر زمنية قابلة للمعالجة.
# أهميته أنه يجهز مرحلة لاحقة مثل متابعة الاستحقاقات أو بناء timeline للنزاع.
def example_legal_extract_dates_mocked() -> None:
    """Extract dates with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.legal.extract_dates(
        document_text="يبدأ نفاذ الاتفاقية في 1 يناير 2026 ويتم السداد خلال 15 يومًا من الفاتورة.",
        document_type="اتفاقية خدمات",
    )
    _print_payload("استخراج التواريخ - محلي", result)


# هذا المثال يوضح استخراج الالتزامات ككائنات atomic بدل نصوص عامة.
# أهميته أنه يمهد مباشرة لأدوات risk scoring أو dispute analysis أو redrafting لاحقًا.
def example_legal_extract_obligations_mocked() -> None:
    """Extract obligations with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.legal.extract_obligations(
        document_text=(
            "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية وفق الجدول الزمني المعتمد، "
            "ويلتزم الطرف الأول بسداد المقابل خلال 15 يومًا بعد استلام الفاتورة."
        ),
        document_type="اتفاقية خدمات",
    )
    _print_payload("استخراج الالتزامات - محلي", result)


def example_contract_gap_mocked() -> None:
    """Run local mocked contract gap analysis.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.contracts.gap_analysis(
        contract_text="يلتزم الطرف الأول بالدفع لاحقًا بعد إنجاز العمل.",
        contract_type="service_agreement",
    )
    _print_payload("تحليل ثغرات العقد - محلي", result)


def example_generate_nda_mocked() -> None:
    """Generate a mocked Arabic NDA.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.contracts.generate_nda(
        nda_type="mutual",
        disclosing_party="شركة ألف",
        receiving_party="شركة باء",
        purpose="مناقشة شراكة تشغيلية",
        confidentiality_period_years=3,
    )
    _print_payload("اتفاقية عدم إفصاح - محلي", result)


def example_generate_mou_mocked() -> None:
    """Generate a mocked Arabic memorandum of understanding.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.contracts.generate_mou(
        party_a="شركة ألف",
        party_b="شركة باء",
        objectives=["تطوير منصة قانونية مشتركة"],
        responsibilities=["تبادل المتطلبات", "تجهيز خطة تنفيذ أولية"],
        duration_months=6,
        binding_sections=["السرية", "القانون الحاكم"],
    )
    _print_payload("مذكرة تفاهم - محلي", result)


def example_drafting_improve_mocked() -> None:
    """Improve legal drafting with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.drafting.improve(
        original_text="يدفع الطرف الأول عند الإنجاز.",
        improvement_goals=["precision", "clarity"],
        context="service agreement",
    )
    _print_payload("تحسين الصياغة - محلي", result)


def example_drafting_summarize_mocked() -> None:
    """Summarize a legal document with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.drafting.summarize(
        document_text="يتعهد الطرف الأول بتقديم الخدمات وسداد الرسوم وفق الفواتير المتفق عليها.",
        summary_length="executive",
    )
    _print_payload("تلخيص المستند - محلي", result)


def example_drafting_simplify_mocked() -> None:
    """Simplify legal Arabic with the local mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.drafting.simplify(
        legal_text="يلتزم الموظف بعدم منافسة صاحب العمل خلال المدة المنصوص عليها تعاقديًا."
    )
    _print_payload("تبسيط النص القانوني - محلي", result)


def example_privacy_policy_mocked() -> None:
    """Generate a mocked privacy policy.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.compliance.generate_privacy_policy(
        company_name="شركة تجريبية",
        service_type="منصة تقنية",
        data_collected=["الاسم", "البريد الإلكتروني", "بيانات الاستخدام"],
        data_purposes=["تشغيل الخدمة", "الدعم", "التحسين"],
        third_party_sharing=False,
        international_transfers=False,
    )
    _print_payload("سياسة الخصوصية - محلي", result)


def example_demand_letter_mocked() -> None:
    """Generate a mocked demand letter.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.compliance.demand_letter(
        sender_name="شركة ألف",
        recipient_name="شركة باء",
        claim_type="مستحقات تعاقدية",
        claim_amount=85000,
        incident_description="تأخر في سداد مستحقات عقد خدمات تقنية.",
        deadline_days=7,
        threat_of_action="سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
    )
    _print_payload("خطاب مطالبة - محلي", result)


def example_hr_policy_mocked() -> None:
    """Generate a mocked HR policy.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.policies.generate_hr_policy(
        policy_type="الغياب والانضباط",
        company_name="شركة تجريبية",
        industry="خدمات تقنية",
        employee_count=45,
        custom_requirements=["اعتماد التدرج التأديبي", "تحديد آلية التوثيق"],
    )
    _print_payload("سياسة موارد بشرية - محلي", result)


def example_job_description_mocked() -> None:
    """Generate a mocked job description.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the supplied input is invalid.
    """
    client: LegalClient = build_mocked_client()
    result = client.policies.job_description(
        job_title="أخصائي التزام",
        department="الشؤون القانونية",
        required_experience_years=2,
        required_education="بكالوريوس قانون",
        key_responsibilities=["إعداد التقارير", "متابعة السياسات", "مراجعة المخاطر"],
        required_skills=["التحليل", "صياغة السياسات", "المراجعة القانونية"],
        saudization_preferred=True,
    )
    _print_payload("الوصف الوظيفي - محلي", result)


def example_drafting_improve_live() -> None:
    """Run live text-improvement through OpenAI.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If `OPENAI_API_KEY` is missing.
        QanuniError: If the provider call fails.
    """
    client: LegalClient = build_openai_client()
    result = client.drafting.improve(
        original_text="يدفع الطرف الأول عند الإنجاز.",
        improvement_goals=["precision", "clarity", "formality"],
        context="service agreement",
        _config=ToolRuntimeConfig(temperature=0.1),
    )
    _print_payload("تحسين الصياغة - مباشر", result)


def example_contract_gap_live() -> None:
    """Run live contract gap analysis through OpenAI.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If `OPENAI_API_KEY` is missing.
        QanuniError: If the provider call fails.
    """
    client: LegalClient = build_openai_client()
    result = client.contracts.gap_analysis(
        contract_text=(
            "يلتزم الطرف الثاني بتنفيذ الأعمال التقنية، ويتم السداد لاحقًا وفق ما يراه الطرف الأول "
            "مناسبًا، ويجوز إنهاء العقد عند الحاجة."
        ),
        contract_type="service_agreement",
        _config=ToolRuntimeConfig(temperature=0.1),
    )
    _print_payload("تحليل ثغرات العقد - مباشر", result)


def example_privacy_policy_live() -> None:
    """Run live privacy-policy generation through OpenAI.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If `OPENAI_API_KEY` is missing.
        QanuniError: If the provider call fails.
    """
    client: LegalClient = build_openai_client()
    result = client.compliance.generate_privacy_policy(
        company_name="شركة تقنية سعودية",
        service_type="منصة SaaS",
        data_collected=["الاسم", "الهاتف", "البريد الإلكتروني", "بيانات السجل"],
        data_purposes=["تشغيل الخدمة", "التحقق", "الدعم", "الأمن"],
        third_party_sharing=False,
        international_transfers=False,
    )
    _print_payload("سياسة الخصوصية - مباشر", result)


def example_async_improve_mocked() -> None:
    """Demonstrate free async execution with the mocked provider.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniError: If tool execution fails.
    """
    asyncio.run(_run_async_improve_mocked())


async def _run_async_improve_mocked() -> None:
    """Execute the mocked async drafting example.

    Args:
        None.

    Returns:
        None.

    Raises:
        QanuniError: If tool execution fails.
    """
    client: LegalClient = build_mocked_client()
    result = await client.drafting.aimprove(
        original_text="يدفع الطرف الأول عند الإنجاز.",
        improvement_goals=["precision", "clarity"],
        context="service agreement",
    )
    _print_payload("تحسين الصياغة المتزامن - محلي", result)


def example_fault_missing_api_key() -> None:
    """Show the failure path when a live tool runs without `OPENAI_API_KEY`.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    try:
        with without_openai_api_key():
            client = LegalClient()
            client.drafting.improve(
                original_text="هذا نص يحتاج تحسينًا.",
                improvement_goals=["clarity"],
                context="contract",
            )
    except QanuniError as error:
        _print_error("خطأ غياب مفتاح OpenAI", error)


def example_fault_mixed_input_styles() -> None:
    """Show the validation error for mixed dict and keyword input styles.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    client: LegalClient = build_mocked_client()
    try:
        client.drafting.improve(
            {"original_text": "نص أولي"},
            original_text="نص آخر",
            improvement_goals=["clarity"],
            context="memo",
        )
    except QanuniError as error:
        _print_error("خطأ تعارض أنماط الإدخال", error)


def example_fault_missing_contract_source() -> None:
    """Show the validation error when contract source text/file is omitted.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    client: LegalClient = build_mocked_client()
    try:
        client.contracts.gap_analysis()
    except QanuniError as error:
        _print_error("خطأ مصدر العقد المفقود", error)


EXAMPLES: tuple[ExampleSpec, ...] = (
    ExampleSpec("list_tools", "discovery", "عرض كل الأدوات المجانية المتاحة.", example_list_tools),
    ExampleSpec(
        "list_tool_access",
        "discovery",
        "عرض حالة الوصول الحالية لكل الأدوات في هذه النسخة المجانية.",
        example_list_tool_access,
    ),
    ExampleSpec(
        "labor_end_of_service",
        "labor",
        "تشغيل حاسبة مكافأة نهاية الخدمة الحتمية.",
        example_labor_end_of_service,
    ),
    ExampleSpec(
        "labor_probation_check",
        "labor",
        "فحص نظامية فترة التجربة حسب المدخلات.",
        example_labor_probation_check,
    ),
    ExampleSpec(
        "legal_extract_clauses_mocked",
        "mocked_local",
        "استخراج البنود الذرية من مستند قانوني محليًا.",
        example_legal_extract_clauses_mocked,
    ),
    ExampleSpec(
        "legal_extract_parties_mocked",
        "mocked_local",
        "استخراج الأطراف وأدوارهم من النص محليًا.",
        example_legal_extract_parties_mocked,
    ),
    ExampleSpec(
        "legal_extract_dates_mocked",
        "mocked_local",
        "استخراج التواريخ والمهل القانونية محليًا.",
        example_legal_extract_dates_mocked,
    ),
    ExampleSpec(
        "legal_extract_obligations_mocked",
        "mocked_local",
        "استخراج الالتزامات الأساسية وتوزيعها بين الأطراف محليًا.",
        example_legal_extract_obligations_mocked,
    ),
    ExampleSpec(
        "contract_gap_mocked",
        "mocked_local",
        "تحليل ثغرات عقد محليًا دون OpenAI.",
        example_contract_gap_mocked,
    ),
    ExampleSpec(
        "generate_nda_mocked",
        "mocked_local",
        "إنشاء NDA محليًا.",
        example_generate_nda_mocked,
    ),
    ExampleSpec(
        "generate_mou_mocked",
        "mocked_local",
        "إنشاء MOU محليًا.",
        example_generate_mou_mocked,
    ),
    ExampleSpec(
        "drafting_improve_mocked",
        "mocked_local",
        "تحسين صياغة نص قانوني محليًا.",
        example_drafting_improve_mocked,
    ),
    ExampleSpec(
        "drafting_summarize_mocked",
        "mocked_local",
        "تلخيص مستند قانوني محليًا.",
        example_drafting_summarize_mocked,
    ),
    ExampleSpec(
        "drafting_simplify_mocked",
        "mocked_local",
        "تبسيط نص قانوني محليًا.",
        example_drafting_simplify_mocked,
    ),
    ExampleSpec(
        "privacy_policy_mocked",
        "mocked_local",
        "إنشاء سياسة خصوصية محليًا.",
        example_privacy_policy_mocked,
    ),
    ExampleSpec(
        "demand_letter_mocked",
        "mocked_local",
        "إنشاء خطاب مطالبة محليًا.",
        example_demand_letter_mocked,
    ),
    ExampleSpec(
        "hr_policy_mocked",
        "mocked_local",
        "إنشاء سياسة موارد بشرية محليًا.",
        example_hr_policy_mocked,
    ),
    ExampleSpec(
        "job_description_mocked",
        "mocked_local",
        "إنشاء وصف وظيفي محليًا.",
        example_job_description_mocked,
    ),
    ExampleSpec(
        "async_improve_mocked",
        "mocked_local",
        "تجربة المسار غير المتزامن مجانًا باستخدام StaticProvider.",
        example_async_improve_mocked,
    ),
    ExampleSpec(
        "drafting_improve_live",
        "openai_live",
        "تحسين صياغة مباشر عبر OpenAI.",
        example_drafting_improve_live,
        requires_openai=True,
    ),
    ExampleSpec(
        "contract_gap_live",
        "openai_live",
        "تحليل عقد مباشر عبر OpenAI.",
        example_contract_gap_live,
        requires_openai=True,
    ),
    ExampleSpec(
        "privacy_policy_live",
        "openai_live",
        "توليد سياسة خصوصية مباشرة عبر OpenAI.",
        example_privacy_policy_live,
        requires_openai=True,
    ),
    ExampleSpec(
        "fault_missing_api_key",
        "faults",
        "إظهار خطأ غياب مفتاح OpenAI في المسارات المباشرة.",
        example_fault_missing_api_key,
    ),
    ExampleSpec(
        "fault_mixed_input_styles",
        "faults",
        "إظهار خطأ تمرير dict و kwargs معًا.",
        example_fault_mixed_input_styles,
    ),
    ExampleSpec(
        "fault_missing_contract_source",
        "faults",
        "إظهار خطأ غياب نص العقد أو ملفه.",
        example_fault_missing_contract_source,
    ),
)


def _iter_selected_examples(
    *,
    category: str | None,
    name: str | None,
) -> list[ExampleSpec]:
    """Resolve the examples requested from CLI arguments.

    Args:
        category: Optional category filter.
        name: Optional exact example name.

    Returns:
        The selected example specifications.

    Raises:
        ValueError: If the requested name does not exist.
    """
    if name is not None:
        matches: list[ExampleSpec] = [spec for spec in EXAMPLES if spec.name == name]
        if not matches:
            raise ValueError(f"Unknown example '{name}'. Use --list to inspect available examples.")
        return matches
    if category is None:
        return list(EXAMPLES)
    return [spec for spec in EXAMPLES if spec.category == category]


def _print_catalog() -> None:
    """Print the available example catalog.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    rows: list[dict[str, Any]] = [
        {
            "name": spec.name,
            "category": spec.category,
            "requires_openai": spec.requires_openai,
            "description": spec.description,
        }
        for spec in EXAMPLES
    ]
    _print_payload("فهرس الأمثلة", rows)


def main(argv: list[str] | None = None) -> int:
    """Run the examples CLI.

    Args:
        argv: Optional argument list for programmatic invocation.

    Returns:
        Process-style exit status code.

    Raises:
        None.
    """
    parser = argparse.ArgumentParser(description="Run free Qanuni SDK examples.")
    parser.add_argument("name", nargs="?", help="Exact example name to run.")
    parser.add_argument("--list", action="store_true", help="List available examples.")
    parser.add_argument("--category", help="Run all examples in a category.")
    args = parser.parse_args(argv)

    if args.list:
        _print_catalog()
        return 0

    try:
        selected_examples: list[ExampleSpec] = _iter_selected_examples(
            category=args.category,
            name=args.name,
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    if not selected_examples:
        print("No examples matched the requested filter.", file=sys.stderr)
        return 2

    for spec in selected_examples:
        if spec.requires_openai and not os.getenv("OPENAI_API_KEY", "").strip():
            print(f"Skipping {spec.name}: OPENAI_API_KEY is not configured.", file=sys.stderr)
            continue
        _print_header(f"{spec.name} ({spec.category})")
        spec.runner()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
