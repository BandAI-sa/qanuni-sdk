"""Central metadata registry for implemented Qanuni tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    """Describe a shipped SDK tool.

    Args:
        tool_id: Stable fully qualified tool identifier.
        namespace: Top-level namespace exposed by the client.
        category: Product category used for grouping and filtering.
        tier: Commercial tier required to access the tool.
        description: Human-readable description of the tool capability.
        implementation: Whether the tool is deterministic or prompt-backed.

    Returns:
        None.

    Raises:
        None.
    """

    tool_id: str
    namespace: str
    category: str
    tier: Literal["free", "pro"]
    description: str
    implementation: Literal["deterministic", "prompt_backed"]


@dataclass(frozen=True, slots=True)
class ToolAccessStatus:
    """Describe whether a specific tool is available in the current build.

    Args:
        tool_id: Stable fully qualified tool identifier.
        namespace: Top-level namespace exposed by the client.
        category: Product category used for grouping and filtering.
        tier: Commercial tier required to access the tool.
        description: Human-readable description of the tool capability.
        implementation: Whether the tool is deterministic or prompt-backed.
        available: Whether the current runtime can execute the tool.
        reason: Optional denial reason when the tool is not currently available.

    Returns:
        None.

    Raises:
        None.
    """

    tool_id: str
    namespace: str
    category: str
    tier: Literal["free", "pro"]
    description: str
    implementation: Literal["deterministic", "prompt_backed"]
    available: bool
    reason: str | None = None


TOOL_CATALOG: tuple[ToolMetadata, ...] = (
    ToolMetadata(
        tool_id="labor.end_of_service",
        namespace="labor",
        category="labor",
        tier="free",
        description="حساب مكافأة نهاية الخدمة وفق قواعد نظام العمل السعودي.",
        implementation="deterministic",
    ),
    ToolMetadata(
        tool_id="labor.probation_check",
        namespace="labor",
        category="labor",
        tier="free",
        description="فحص نظامية فترة التجربة وفق الحدود المعتمدة في نظام العمل السعودي.",
        implementation="deterministic",
    ),
    ToolMetadata(
        tool_id="labor.generate_contract",
        namespace="labor",
        category="labor",
        tier="free",
        description="توليد مسودة عقد عمل عربي بسياق سعودي مع نقاط المراجعة والتخصيص.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_clauses",
        namespace="legal",
        category="legal",
        tier="free",
        description=(
            "استخراج البنود الذرية من المستندات القانونية العربية مع تصنيفها "
            "ومقتطفاتها الدالة."
        ),
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_parties",
        namespace="legal",
        category="legal",
        tier="free",
        description="استخراج الأطراف المذكورين في المستند وأدوارهم المعيارية مع سند نصي واضح.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_dates",
        namespace="legal",
        category="legal",
        tier="free",
        description="استخراج التواريخ والمهل القانونية وتصنيف معناها العملي داخل النص.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_amounts",
        namespace="legal",
        category="legal",
        tier="free",
        description="استخراج المبالغ والقيم المالية من النصوص القانونية مع سياقها القريب.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_obligations",
        namespace="legal",
        category="legal",
        tier="free",
        description="استخراج الالتزامات الجوهرية وتوزيعها بين الأطراف في صيغة قابلة للتركيب.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_termination_terms",
        namespace="legal",
        category="legal",
        tier="free",
        description="استخراج أحكام الإنهاء ومدد الإشعار وآثار الخروج من المستندات القانونية.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.extract_dispute_resolution",
        namespace="legal",
        category="legal",
        tier="free",
        description="استخراج مسارات فض النزاع من حيث الآلية والمكان والتدرج الإجرائي.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="legal.classify_document_type",
        namespace="legal",
        category="legal",
        tier="free",
        description="تصنيف نوع المستند القانوني لتوجيه الـ agent إلى الأدوات الأنسب.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="contracts.gap_analysis",
        namespace="contracts",
        category="contracts",
        tier="free",
        description="تحليل العقود لاكتشاف الغموض والحمايات الناقصة والثغرات الصياغية.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="contracts.risk_score",
        namespace="contracts",
        category="contracts",
        tier="free",
        description="تحويل جودة العقد إلى درجة مخاطر عملية مع أسبابها وأولويات المعالجة.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="contracts.generate_nda",
        namespace="contracts",
        category="contracts",
        tier="free",
        description="إنشاء اتفاقيات عدم إفصاح عربية موجهة للسياق السعودي.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="contracts.generate_mou",
        namespace="contracts",
        category="contracts",
        tier="free",
        description="إنشاء مذكرات تفاهم عربية مع توضيح مواضع الإلزام.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="compliance.generate_privacy_policy",
        namespace="compliance",
        category="compliance",
        tier="free",
        description="إنشاء سياسات خصوصية عربية تراعي متطلبات حماية البيانات في السعودية.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="compliance.pdpl_check",
        namespace="compliance",
        category="compliance",
        tier="free",
        description="فحص تغطية متطلبات حماية البيانات الشخصية ورصد الفجوات والإجراءات المطلوبة.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="compliance.vat_check",
        namespace="compliance",
        category="compliance",
        tier="free",
        description="فحص وضوح المعالجة الضريبية والقيم المالية المرتبطة بـ VAT داخل المستندات.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="compliance.demand_letter",
        namespace="compliance",
        category="compliance",
        tier="free",
        description="إنشاء خطابات مطالبة قانونية عربية لمرحلة ما قبل النزاع.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="drafting.extract_clauses",
        namespace="drafting",
        category="drafting",
        tier="free",
        description="استخراج بنية البنود من الصياغة القانونية تمهيدًا للمراجعة أو إعادة التحرير.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="drafting.improve",
        namespace="drafting",
        category="drafting",
        tier="free",
        description="تحسين الصياغة القانونية العربية لتصبح أوضح وأقوى.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="drafting.summarize",
        namespace="drafting",
        category="drafting",
        tier="free",
        description="تلخيص المستندات القانونية إلى التزامات وحقوق ومخاطر.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="drafting.simplify",
        namespace="drafting",
        category="drafting",
        tier="free",
        description="تبسيط العربية القانونية الكثيفة لغير المتخصصين.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="policies.generate_hr_policy",
        namespace="policies",
        category="policies",
        tier="free",
        description="إنشاء سياسات موارد بشرية عربية بسياق عمل سعودي.",
        implementation="prompt_backed",
    ),
    ToolMetadata(
        tool_id="policies.job_description",
        namespace="policies",
        category="policies",
        tier="free",
        description="إنشاء أوصاف وظيفية عربية مهنية مناسبة للتوظيف في السعودية.",
        implementation="prompt_backed",
    ),
)


def list_tools(
    *,
    tier: Literal["free", "pro"] | None = None,
    namespace: str | None = None,
    category: str | None = None,
) -> list[ToolMetadata]:
    """Return the implemented tool catalog, optionally filtered.

    Args:
        tier: Optional commercial tier filter.
        namespace: Optional top-level namespace filter.
        category: Optional product-category filter.

    Returns:
        A list of tool metadata records that satisfy the requested filters.

    Raises:
        None.
    """
    items = list(TOOL_CATALOG)
    if tier is not None:
        items = [item for item in items if item.tier == tier]
    if namespace is not None:
        items = [item for item in items if item.namespace == namespace]
    if category is not None:
        items = [item for item in items if item.category == category]
    return items
