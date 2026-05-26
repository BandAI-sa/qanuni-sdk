from __future__ import annotations

import os
from typing import Any

import pytest

from qanuni.core.config import QanuniConfig
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.compliance import (
    DemandLetterResult,
    PDPLCheckResult,
    PrivacyPolicyResult,
    VATCheckResult,
)
from qanuni.models.contracts import (
    ContractRiskScoreResult,
    GapAnalysisResult,
    MOUResult,
    NDAResult,
)
from qanuni.models.drafting import SimplifyResult, SummaryResult, TextImprovementResult
from qanuni.models.labor import EmploymentContractGenerationResult
from qanuni.models.legal import (
    AmountExtractionResult,
    ClauseExtractionResult,
    DateExtractionResult,
    DisputeResolutionExtractionResult,
    DocumentTypeClassificationResult,
    ObligationExtractionResult,
    PartyExtractionResult,
    TerminationTermExtractionResult,
)
from qanuni.models.policies import HRPolicyResult, JobDescriptionResult
from qanuni.providers.base_provider import BaseProvider, ProviderResponse, ProviderUsage


class FakeProvider(BaseProvider):
    """Deterministic provider used by unit tests."""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Return canned structured responses keyed by the requested schema."""
        del system_prompt, user_prompt
        return ProviderResponse(
            data=self._build_response(response_model),
            model=runtime.model or "fake-model",
            usage=ProviderUsage(input_tokens=123, output_tokens=198, total_tokens=321),
            raw_text="{}",
        )

    async def agenerate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
        runtime: ToolRuntimeConfig,
    ) -> ProviderResponse[Any]:
        """Async wrapper around the deterministic test provider behavior."""
        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
            runtime=runtime,
        )

    @staticmethod
    def _build_response(response_model: type[Any]) -> Any:
        """Map response models to deterministic fake payloads."""
        canonical_model: type[Any] = getattr(
            response_model,
            "__qanuni_output_model__",
            response_model,
        )
        if canonical_model is GapAnalysisResult:
            return GapAnalysisResult(
                gaps=[
                    {
                        "clause": "غياب حد أقصى للمسؤولية.",
                        "severity": "high",
                        "recommendation": "أضف بندا واضحا يحدد سقف المسؤولية.",
                    }
                ],
                overall_risk_level="high",
                missing_mandatory_clauses=["إنهاء العقد", "القانون الحاكم"],
                ambiguous_clauses=[
                    {
                        "excerpt": "يتم السداد لاحقا",
                        "reason": "لا يوجد تحديد زمني واضح للسداد.",
                        "suggested_rewrite": "يستحق السداد خلال 15 يوما من تاريخ استلام الفاتورة.",
                    }
                ],
                compliance_score=63.0,
                summary="الحمايات التجارية الأساسية ما تزال غير مكتملة.",
            )
        if canonical_model is ClauseExtractionResult:
            return ClauseExtractionResult(
                clauses=[
                    {
                        "clause_id": "clause_payment_1",
                        "clause_type": "payment",
                        "heading": "السداد",
                        "summary": "ينظم النص آلية السداد بشكل عام دون أجل محدد.",
                        "excerpt": "يتم السداد لاحقًا وفق الفاتورة.",
                        "importance": "high",
                        "is_mandatory_context": True,
                    },
                    {
                        "clause_id": "clause_termination_1",
                        "clause_type": "termination",
                        "heading": "إنهاء العقد",
                        "summary": "يسمح النص بإنهاء العلاقة عند الحاجة.",
                        "excerpt": "ويجوز إنهاء العقد عند الحاجة.",
                        "importance": "medium",
                        "is_mandatory_context": True,
                    },
                ],
                extracted_clause_types=["payment", "termination"],
                summary="تم العثور على بنود دفع وإنهاء بصياغة موجزة تحتاج لاحقًا إلى تقييم أعمق.",
            )
        if canonical_model is PartyExtractionResult:
            return PartyExtractionResult(
                parties=[
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
                summary="تم تحديد طرفين تعاقديين رئيسيين في المستند.",
            )
        if canonical_model is DateExtractionResult:
            return DateExtractionResult(
                dates=[
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
                summary="تم العثور على تاريخ نفاذ ومهلة سداد تشغيلية.",
            )
        if canonical_model is ObligationExtractionResult:
            return ObligationExtractionResult(
                obligations=[
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
                summary="تم توزيع الالتزامات الأساسية بين التنفيذ والسداد.",
            )
        if canonical_model is AmountExtractionResult:
            return AmountExtractionResult(
                amounts=[
                    {
                        "amount_id": "amount_1",
                        "amount_type": "fee",
                        "raw_amount": "25,000 ريال",
                        "numeric_value": 25000.0,
                        "currency": "SAR",
                        "source_excerpt": "يلتزم الطرف الأول بسداد مبلغ 25,000 ريال مقابل الخدمات.",
                    },
                    {
                        "amount_id": "amount_2",
                        "amount_type": "tax",
                        "raw_amount": "3,750 ريال",
                        "numeric_value": 3750.0,
                        "currency": "SAR",
                        "source_excerpt": "تضاف ضريبة القيمة المضافة بمبلغ 3,750 ريال.",
                    },
                ],
                summary="تم استخراج المقابل المالي الأساسي وقيمة الضريبة المرتبطة به.",
            )
        if canonical_model is TerminationTermExtractionResult:
            return TerminationTermExtractionResult(
                termination_terms=[
                    {
                        "term_id": "term_1",
                        "trigger": "إخلال جوهري بالالتزامات",
                        "notice_period": "30 يومًا",
                        "consequence": "يجوز للطرف المتضرر إنهاء العقد دون تعويض إضافي.",
                        "source_excerpt": (
                            "يجوز لأي طرف إنهاء العقد عند الإخلال الجوهري بعد إشعار مدته 30 يومًا."
                        ),
                        "risk_note": "يستحسن تعريف الإخلال الجوهري بصورة أكثر ضبطًا.",
                    }
                ],
                summary="تم استخراج شرط إنهاء رئيسي مع مهلة إشعار وأثر قانوني واضحين.",
            )
        if canonical_model is DisputeResolutionExtractionResult:
            return DisputeResolutionExtractionResult(
                dispute_resolution_terms=[
                    {
                        "resolution_id": "dispute_1",
                        "resolution_type": "arbitration",
                        "venue": "الرياض",
                        "governing_law_reference": "نظام التحكيم السعودي",
                        "escalation_steps": ["تفاوض ودي", "إشعار خطي", "تحكيم"],
                        "source_excerpt": (
                            "تُحال النزاعات بعد التفاوض الودي إلى التحكيم في الرياض "
                            "وفق نظام التحكيم السعودي."
                        ),
                    }
                ],
                summary="تم تحديد مسار تفاوض ثم تحكيم في الرياض لحل النزاعات.",
            )
        if canonical_model is DocumentTypeClassificationResult:
            return DocumentTypeClassificationResult(
                primary_document_type="service_agreement",
                alternative_document_types=["mou"],
                rationale=(
                    "المستند ينظم نطاق خدمات ومقابلًا ماليًا وآلية إنهاء، ما يرجح "
                    "كونه اتفاقية خدمات."
                ),
                confidence_band="high",
                summary="الوثيقة أقرب إلى اتفاقية خدمات منها إلى مذكرة تفاهم.",
            )
        if canonical_model is TextImprovementResult:
            return TextImprovementResult(
                improved_text=(
                    "يلتزم الطرف الأول بسداد المقابل خلال خمسة عشر يوما من تاريخ الفاتورة."
                ),
                changes=[
                    {
                        "original": "يدفع المبلغ عند الإنجاز",
                        "improved": (
                            "يلتزم الطرف الأول بسداد المقابل خلال خمسة عشر يوما من تاريخ "
                            "الفاتورة."
                        ),
                        "reason": "أضيفت مدة زمنية محددة وصياغة أكثر رسمية وإلزاما.",
                    }
                ],
                overall_assessment="أصبحت الصياغة أكثر دقة وقابلية للتنفيذ.",
                improvement_score=88.0,
            )
        if canonical_model is SummaryResult:
            return SummaryResult(
                summary=(
                    "الملخص التنفيذي: يركز الاتفاق على تقديم الخدمات وآلية السداد وأحكام "
                    "الإنهاء."
                ),
                key_obligations=["تقديم الخدمات", "سداد الفواتير"],
                key_rights=["استحقاق المقابل", "إنهاء العقد عند الإخلال"],
                key_dates=[{"label": "تجديد", "value": "2026-12-31"}],
                financial_terms=["25,000 ريال شهريا"],
                risk_highlights=["آلية الإنهاء الحالية تحتاج إلى مزيد من الوضوح."],
            )
        if canonical_model is SimplifyResult:
            return SimplifyResult(
                simplified_text=(
                    "هذا النص يعني أنه لا يجوز لك منافسة الطرف الآخر خلال المدة المحددة في العقد."
                ),
                preserved_terms=["عدم المنافسة", "المدة"],
                reader_warnings=[
                    "ما تزال قابلية التطبيق النهائية مرتبطة بظروف النظام السعودي وحالة العقد."
                ],
            )
        if canonical_model is PrivacyPolicyResult:
            return PrivacyPolicyResult(
                policy_text="سياسة الخصوصية...",
                pdpl_compliance_score=91.0,
                sections_included=["الهوية", "الحقوق", "الاحتفاظ"],
                legal_notes=[
                    "أضف قناة تشغيلية واضحة لاستقبال شكاوى أو طلبات الخصوصية إن كانت متاحة."
                ],
            )
        if canonical_model is NDAResult:
            return NDAResult(
                nda_text="اتفاقية عدم إفصاح...",
                key_clauses_summary=["تعريف المعلومات السرية", "المدة", "الجزاءات"],
                legal_notes=[
                    "قد يكون من الأفضل تضييق تعريف المعلومات السرية إذا كان نطاق الإفصاح محدودا."
                ],
            )
        if canonical_model is MOUResult:
            return MOUResult(
                mou_text="مذكرة تفاهم...",
                binding_clauses=["السرية", "القانون الحاكم"],
                caution_notes=["ينبغي نقل الالتزامات التجارية النهائية إلى اتفاقية تفصيلية ملزمة."],
            )
        if canonical_model is DemandLetterResult:
            return DemandLetterResult(
                letter_text="خطاب مطالبة قانونية...",
                legal_notice_elements=["الأطراف", "الوقائع", "المطالبة", "المهلة"],
                strategic_notes=["يستحسن أن يراجع محام الأدلة المرفقة قبل الإرسال النهائي."],
            )
        if canonical_model is PDPLCheckResult:
            return PDPLCheckResult(
                compliance_score=72.0,
                compliant_items=["تحديد أغراض المعالجة", "ذكر وسيلة التواصل الأساسية"],
                gaps=["غياب تفصيل مدد الاحتفاظ", "لا توجد آلية واضحة لطلبات أصحاب البيانات"],
                required_actions=[
                    "أضف مدة أو معيارًا واضحًا للاحتفاظ بالبيانات.",
                    "أنشئ قناة تشغيلية واضحة لاستقبال طلبات أصحاب البيانات.",
                ],
                summary="المستند يغطي بعض المتطلبات الأساسية لكن ما زالت هناك فجوات تشغيلية مهمة.",
            )
        if canonical_model is VATCheckResult:
            return VATCheckResult(
                compliance_score=68.0,
                vat_treatment=(
                    "المستند يذكر الضريبة ولكن يحتاج مزيدًا من الوضوح حول نسبة "
                    "التطبيق وآلية الفوترة."
                ),
                detected_amounts=["25,000 ريال", "3,750 ريال"],
                gaps=["لا يحدد ما إذا كانت الأسعار شاملة أو غير شاملة لضريبة القيمة المضافة."],
                required_actions=[
                    "حدد بوضوح ما إذا كان المقابل شاملًا أو غير شامل لضريبة القيمة المضافة.",
                    "اذكر نسبة الضريبة المطبقة وآلية إضافتها إلى الفواتير.",
                ],
                summary="هناك معالجة ضريبية أولية لكن الصياغة الحالية قد تسبب نزاعًا ماليًا لاحقًا.",
            )
        if canonical_model is ContractRiskScoreResult:
            return ContractRiskScoreResult(
                risk_score=78.0,
                risk_level="high",
                primary_risk_drivers=["آلية السداد فضفاضة", "بند الإنهاء غير منضبط"],
                missing_safeguards=["حد أقصى للمسؤولية", "قانون حاكم"],
                mitigation_priorities=[
                    "اضبط موعد السداد والجزاءات التأخيرية.",
                    "أضف بند قانون حاكم وآلية نزاع صريحة.",
                ],
                summary=(
                    "المستند قابل للتنفيذ مبدئيًا لكنه يحمل مخاطر تعاقدية مرتفعة "
                    "في الحماية والوضوح."
                ),
            )
        if canonical_model is EmploymentContractGenerationResult:
            return EmploymentContractGenerationResult(
                contract_text="عقد عمل سعودي...",
                included_clauses=["الأجر", "العمل ومكانه", "فترة التجربة", "الإجازات", "الإنهاء"],
                compliance_notes=[
                    "راجع توافق ساعات العمل الفعلية مع طبيعة النشاط واللوائح الداخلية.",
                    "تأكد من مواءمة المزايا الإضافية مع السياسة الداخلية للمنشأة.",
                ],
                configurable_points=["فترة التجربة", "المزايا الإضافية", "مكان العمل", "البدلات"],
            )
        if canonical_model is HRPolicyResult:
            return HRPolicyResult(
                policy_text="سياسة الموارد البشرية...",
                saudi_law_compliance_notes=[
                    "أضف مسارًا واضحًا للتدرج التأديبي والمسؤوليات المعتمدة."
                ],
                mandatory_inclusions_met=True,
                recommended_additions=["حدّد جهة الاعتماد النهائية داخل الشركة."],
            )
        if canonical_model is JobDescriptionResult:
            return JobDescriptionResult(
                job_description_text="الوصف الوظيفي...",
                discriminatory_language_flags=[],
                saudization_statement=(
                    "يفضل شغل الوظيفة ضمن مستهدفات التوطين متى انطبقت المتطلبات النظامية."
                ),
                legal_compliance_notes=["تجنب أي اشتراط عمري ما لم يوجد مبرر نظامي واضح."],
            )
        raise AssertionError(f"Unhandled fake response model: {canonical_model}")


@pytest.fixture()
def config() -> QanuniConfig:
    """Return a basic SDK config for unit tests."""
    return QanuniConfig(_env_file=None, api_key="sk-test", tool_overrides={})


@pytest.fixture(autouse=True)
def isolate_qanuni_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove live SDK environment variables so tests stay deterministic.

    Args:
        monkeypatch: Pytest helper used to isolate environment variables per test.

    Returns:
        None.

    Raises:
        None.
    """
    environment_key: str
    for environment_key in list(os.environ):
        if environment_key == "OPENAI_API_KEY" or environment_key.startswith("QANUNI_"):
            monkeypatch.delenv(environment_key, raising=False)


@pytest.fixture()
def provider_factory() -> Any:
    """Return a factory that creates the deterministic fake provider."""

    def _factory() -> BaseProvider:
        return FakeProvider()

    return _factory
