"""Deterministic provider used by the acceptance pack."""

from __future__ import annotations

from typing import Any

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
from qanuni.providers import StaticProvider
from qanuni.providers.base_provider import ProviderUsage


def build_acceptance_provider() -> StaticProvider:
    """Return a deterministic provider for offline acceptance scenarios.

    Args:
        None.

    Returns:
        A static provider populated with Arabic acceptance payloads.

    Raises:
        None.
    """
    return StaticProvider(
        default_model="static://qanuni-acceptance",
        usage=ProviderUsage(input_tokens=123, output_tokens=198, total_tokens=321),
        responses=_acceptance_responses(),
    )


def _acceptance_responses() -> dict[type[Any], dict[str, Any]]:
    """Build the deterministic acceptance responses by output model.

    Args:
        None.

    Returns:
        Mapping of output models to static structured payloads.

    Raises:
        None.
    """
    return {
        GapAnalysisResult: {
            "gaps": [
                {
                    "clause": "بند حدود المسؤولية غير محدد.",
                    "severity": "high",
                    "recommendation": "أضف بندًا يحدد سقف المسؤولية والاستثناءات بوضوح.",
                }
            ],
            "overall_risk_level": "high",
            "missing_mandatory_clauses": ["القانون الحاكم", "آلية الإشعار", "سقف المسؤولية"],
            "ambiguous_clauses": [
                {
                    "excerpt": "يتم السداد لاحقًا",
                    "reason": "لا يوجد أجل سداد واضح أو نقطة بداية دقيقة.",
                    "suggested_rewrite": (
                        "يتم السداد خلال 15 يومًا من تاريخ استلام الفاتورة النظامية."
                    ),
                }
            ],
            "compliance_score": 62.0,
            "summary": "المستند يحتاج ضبطًا تعاقديًا أوضح قبل اعتماده في بيئة تشغيلية حساسة.",
        },
        ContractRiskScoreResult: {
            "risk_score": 78.0,
            "risk_level": "high",
            "primary_risk_drivers": ["آلية السداد فضفاضة", "الإشعار والإنهاء غير منضبطين"],
            "missing_safeguards": ["سقف المسؤولية", "قانون حاكم صريح"],
            "mitigation_priorities": [
                "اضبط أجل السداد والغرامات المرتبطة بالتأخير.",
                "أضف بند قانون حاكم وآلية نزاع صريحة.",
            ],
            "summary": "العقد قابل للمراجعة لكن مخاطر الصياغة الحالية مرتفعة.",
        },
        ClauseExtractionResult: {
            "clauses": [
                {
                    "clause_id": "clause_scope_1",
                    "clause_type": "scope",
                    "heading": "نطاق العمل",
                    "summary": "يحدد التزام مقدم الخدمة بالأعمال المطلوبة.",
                    "excerpt": "يلتزم الطرف الثاني بتنفيذ الأعمال الفنية المطلوبة.",
                    "importance": "high",
                    "is_mandatory_context": True,
                },
                {
                    "clause_id": "clause_payment_1",
                    "clause_type": "payment",
                    "heading": "السداد",
                    "summary": "يعالج المقابل المالي دون جدول زمني كاف.",
                    "excerpt": "يتم السداد لاحقًا وفق الفاتورة.",
                    "importance": "high",
                    "is_mandatory_context": True,
                },
            ],
            "extracted_clause_types": ["scope", "payment"],
            "summary": "تم تحديد بنود نطاق العمل والسداد كأساس للمراجعة التعاقدية.",
        },
        PartyExtractionResult: {
            "parties": [
                {
                    "party_id": "party_sender",
                    "name": "شركة ألف",
                    "normalized_role": "party_a",
                    "role_label": "الطرف الأول",
                    "source_excerpt": "أبرمت شركة ألف هذا العقد مع شركة باء.",
                },
                {
                    "party_id": "party_recipient",
                    "name": "شركة باء",
                    "normalized_role": "party_b",
                    "role_label": "الطرف الثاني",
                    "source_excerpt": "أبرمت شركة ألف هذا العقد مع شركة باء.",
                },
            ],
            "summary": "تم تمييز الطرفين الرئيسيين في المستند وربطهما بالأدوار التعاقدية.",
        },
        DateExtractionResult: {
            "dates": [
                {
                    "date_id": "date_effective",
                    "date_type": "effective_date",
                    "label": "تاريخ السريان",
                    "raw_value": "1 يناير 2026",
                    "normalized_value": "2026-01-01",
                    "source_excerpt": "يبدأ العقد في 1 يناير 2026.",
                }
            ],
            "summary": "تم استخراج تاريخ سريان واضح يمكن البناء عليه في المراجعة.",
        },
        AmountExtractionResult: {
            "amounts": [
                {
                    "amount_id": "amount_invoice",
                    "amount_type": "invoice",
                    "raw_amount": "85000 ريال",
                    "numeric_value": 85000,
                    "currency": "SAR",
                    "source_excerpt": "يلتزم العميل بسداد مبلغ 85000 ريال.",
                }
            ],
            "summary": "تم استخراج المقابل المالي الرئيسي مع العملة والسياق.",
        },
        ObligationExtractionResult: {
            "obligations": [
                {
                    "obligation_id": "obligation_vendor_delivery",
                    "direction": "owed_by",
                    "obligated_party": "شركة باء",
                    "beneficiary_party": "شركة ألف",
                    "action": "تنفيذ الأعمال الفنية",
                    "due_trigger": "بعد توقيع العقد",
                    "source_excerpt": "يلتزم الطرف الثاني بتنفيذ الأعمال الفنية المطلوبة.",
                }
            ],
            "summary": "تم استخراج التزام تنفيذي رئيسي يمكن تمريره إلى مسارات المخاطر والنزاع.",
        },
        TerminationTermExtractionResult: {
            "termination_terms": [
                {
                    "term_id": "termination_notice",
                    "trigger": "إنهاء لاحتياج تشغيلي أو إخلال",
                    "notice_period": "30 يومًا",
                    "consequence": "إنهاء العلاقة بعد انقضاء مهلة الإشعار",
                    "source_excerpt": "يجوز لأي طرف إنهاء العقد بعد إشعار مدته ثلاثون يومًا.",
                    "risk_note": "صياغة الإنهاء تحتاج ربطًا أوضح بحالات الإخلال.",
                }
            ],
            "summary": "تم استخراج بند الإنهاء مع مدة الإشعار والمخاطر الصياغية المصاحبة.",
        },
        DisputeResolutionExtractionResult: {
            "dispute_resolution_terms": [
                {
                    "resolution_id": "dispute_arbitration",
                    "resolution_type": "arbitration",
                    "venue": "الرياض",
                    "governing_law_reference": "الأنظمة السعودية",
                    "escalation_steps": ["تسوية ودية", "تحكيم"],
                    "source_excerpt": "في حال النزاع تتم التسوية وديًا ثم التحكيم في الرياض.",
                }
            ],
            "summary": "تم تمييز مسار النزاع على أنه تسوية ودية يتبعها تحكيم في الرياض.",
        },
        DocumentTypeClassificationResult: {
            "primary_document_type": "service_agreement",
            "alternative_document_types": ["mou"],
            "rationale": "المستند ينظم تنفيذ أعمال ومقابلًا ماليًا والتزامات تشغيلية.",
            "confidence_band": "high",
            "summary": "تم تصنيف المستند كعقد خدمات مع ثقة مرتفعة.",
        },
        DemandLetterResult: {
            "letter_text": (
                "نخاطبكم بصفتكم الطرف المدين بمبلغ 85000 ريال ونطلب السداد خلال سبعة أيام "
                "من تاريخ استلام هذا الخطاب، وإلا فسيتم اتخاذ الإجراءات القانونية المناسبة."
            ),
            "legal_notice_elements": [
                "تحديد الأطراف",
                "بيان المطالبة",
                "المهلة",
                "التحذير بالإجراء",
            ],
            "strategic_notes": ["أرفق نسخة العقد والفاتورة الأخيرة مع الخطاب النهائي."],
        },
        TextImprovementResult: {
            "improved_text": (
                "نخاطبكم بصفتكم مدينين بمبلغ 85000 ريال ناشئ عن عقد خدمات تقنية، ونطلب "
                "السداد خلال سبعة أيام من تاريخ استلام هذا الخطاب، وإلا فسيتم اتخاذ "
                "الإجراءات القانونية المناسبة وفق الأنظمة المعمول بها."
            ),
            "changes": [
                {
                    "original": "نطلب السداد خلال سبعة أيام",
                    "improved": "نطلب السداد خلال سبعة أيام من تاريخ استلام هذا الخطاب",
                    "reason": "تحديد نقطة بداية المهلة بشكل أدق.",
                }
            ],
            "overall_assessment": "الصياغة المعدلة أوضح وأكثر رسمية وصلابة.",
            "improvement_score": 88.0,
        },
        SummaryResult: {
            "summary": "المستند يقرر التزامات تقديم خدمة وسداد مقابل مالي ضمن إطار تعاقدي مختصر.",
            "key_obligations": ["تقديم الخدمة", "السداد خلال المهلة"],
            "key_rights": ["استحقاق المقابل", "طلب التنفيذ وفق العقد"],
            "key_dates": [{"label": "تاريخ السريان", "value": "2026-01-01"}],
            "financial_terms": ["85000 ريال"],
            "risk_highlights": ["أجل السداد يحتاج ضبطًا أوضح."],
        },
        SimplifyResult: {
            "simplified_text": "المقصود أن على الطرفين تنفيذ ما اتفقا عليه بحسن نية وبشكل واضح.",
            "preserved_terms": ["حسن النية"],
            "reader_warnings": ["هذه الصياغة المبسطة لا تغني عن مراجعة النص الأصلي عند النزاع."],
        },
        PDPLCheckResult: {
            "compliance_score": 58.0,
            "compliant_items": ["ذكر جمع البيانات", "الإشارة إلى مشاركة بعض البيانات"],
            "gaps": ["حقوق أصحاب البيانات غير موضحة", "النقل الخارجي غير مفصل"],
            "required_actions": ["أضف فقرة حقوق أصحاب البيانات", "وضح ضوابط النقل الدولي"],
            "summary": "المستند يذكر الممارسات الأساسية لكنه لا يحقق تغطية امتثالية كافية.",
        },
        PrivacyPolicyResult: {
            "policy_text": (
                "توضح هذه السياسة كيفية جمع شركة ألف للبيانات الشخصية واستخدامها ومشاركتها "
                "بما يتوافق مع متطلبات الحماية السارية داخل المملكة العربية السعودية."
            ),
            "pdpl_compliance_score": 82.0,
            "sections_included": ["الأغراض", "المشاركة", "الاحتفاظ", "الحقوق"],
            "legal_notes": [
                "راجع آلية النقل الدولي إذا كانت الخدمة تعتمد على مزودين خارج المملكة."
            ],
        },
        VATCheckResult: {
            "compliance_score": 66.0,
            "vat_treatment": "المعاملة الضريبية غير موضحة بشكل كاف.",
            "detected_amounts": ["100000 ريال"],
            "gaps": ["لم يوضح النص ما إذا كان المقابل شاملًا لضريبة القيمة المضافة."],
            "required_actions": ["أضف نصًا صريحًا بشأن شمول المقابل للضريبة أو عدمه."],
            "summary": "هناك حاجة إلى ضبط الصياغة الضريبية لتقليل النزاع المالي.",
        },
        NDAResult: {
            "nda_text": (
                "اتفاقية عدم إفصاح عربية بين شركة ألف وشركة باء لأغراض دراسة الشراكة التشغيلية."
            ),
            "key_clauses_summary": ["تعريف المعلومات السرية", "الاستثناءات", "مدة السرية"],
            "legal_notes": ["راجع ما إذا كانت هناك حاجة لبند جزائي أو اختصاص قضائي محدد."],
        },
        MOUResult: {
            "mou_text": (
                "مذكرة تفاهم عربية أولية بين شركة ألف وشركة باء لتحديد إطار التعاون التقني."
            ),
            "binding_clauses": ["السرية", "القانون الحاكم"],
            "caution_notes": ["وضح بشكل صريح البنود الملزمة وغير الملزمة."],
        },
        EmploymentContractGenerationResult: {
            "contract_text": (
                "عقد عمل سعودي يتضمن الأجر ومكان العمل وفترة التجربة والإجازات وأحكام الإنهاء."
            ),
            "included_clauses": ["الأجر", "مكان العمل", "فترة التجربة", "الإجازات", "الإنهاء"],
            "compliance_notes": ["راجع ساعات العمل الفعلية والبدلات وفق سياسة المنشأة."],
            "configurable_points": ["فترة التجربة", "المزايا الإضافية", "مكان العمل"],
        },
        HRPolicyResult: {
            "policy_text": (
                "سياسة موارد بشرية عربية لبيئة عمل سعودية تشمل الالتزام والانضباط والإجازات."
            ),
            "saudi_law_compliance_notes": ["أضف مسارًا واضحًا للتدرج التأديبي والمسؤوليات."],
            "mandatory_inclusions_met": True,
            "recommended_additions": ["حدد جهة الاعتماد النهائية داخل الشركة."],
        },
        JobDescriptionResult: {
            "job_description_text": (
                "وصف وظيفي عربي يوضح المهام الرئيسية والمتطلبات التعليمية والمهارية."
            ),
            "discriminatory_language_flags": [],
            "saudization_statement": (
                "يفضل شغل الوظيفة ضمن مستهدفات التوطين متى انطبقت الشروط النظامية."
            ),
            "legal_compliance_notes": ["تجنب الاشتراطات التمييزية غير المبررة نظاميًا."],
        },
    }
