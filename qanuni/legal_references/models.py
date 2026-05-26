"""Typed legal-reference models injected into Qanuni prompts and audit metadata."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LegalReferenceMode(StrEnum):
    """Describe how strongly a reference packet constrains prompt execution."""

    DISABLED = "disabled"
    ADVISORY = "advisory"
    STRICT = "strict"


class LegalReferencePriority(StrEnum):
    """Describe the practical priority of a single legal-reference rule."""

    MANDATORY = "mandatory"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LegalReferenceSourceType(StrEnum):
    """Describe the origin category of a legal-reference source."""

    STATUTE = "statute"
    REGULATION = "regulation"
    REGULATORY_GUIDANCE = "regulatory_guidance"
    INTERNAL_STANDARD = "internal_standard"
    POLICY = "policy"


class LegalReferenceRule(BaseModel):
    """Represent one reusable legal rule enforced by a reference profile.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    rule_id: str
    priority: LegalReferencePriority = LegalReferencePriority.MANDATORY
    directive: str
    applicability: str | None = None
    rationale: str | None = None


class LegalReferenceSource(BaseModel):
    """Represent one authority document included in a reference profile.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    source_id: str
    title: str
    authority: str
    citation: str
    source_type: LegalReferenceSourceType = LegalReferenceSourceType.INTERNAL_STANDARD
    jurisdiction: str
    url: str | None = None
    notes: str | None = None
    rules: tuple[LegalReferenceRule, ...] = ()


class LegalReferenceProfile(BaseModel):
    """Represent the full reference packet attached to one or more tools.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    profile_id: str
    title: str
    jurisdiction: str
    mode: LegalReferenceMode = LegalReferenceMode.STRICT
    tool_ids: tuple[str, ...] = ()
    application_instructions: str = Field(min_length=10)
    sources: tuple[LegalReferenceSource, ...] = ()

    def source_ids(self) -> tuple[str, ...]:
        """Return the stable source identifiers included in the profile.

        Args:
            None.

        Returns:
            A tuple of included source identifiers.

        Raises:
            None.
        """
        return tuple(source.source_id for source in self.sources)

    def rule_ids(self) -> tuple[str, ...]:
        """Return the stable rule identifiers included in the profile.

        Args:
            None.

        Returns:
            A tuple of included rule identifiers.

        Raises:
            None.
        """
        return tuple(
            rule.rule_id
            for source in self.sources
            for rule in source.rules
        )

    def mandatory_rule_ids(self) -> tuple[str, ...]:
        """Return the identifiers for rules marked as mandatory.

        Args:
            None.

        Returns:
            A tuple of mandatory rule identifiers.

        Raises:
            None.
        """
        return tuple(
            rule.rule_id
            for source in self.sources
            for rule in source.rules
            if rule.priority == LegalReferencePriority.MANDATORY
        )

    def render_system_block(self) -> str:
        """Render the profile into a strict system-side guidance block.

        Args:
            None.

        Returns:
            A normalized string suitable for system-prompt injection.

        Raises:
            None.
        """
        lines: list[str] = [
            f"ملف المراجع: {self.profile_id}",
            f"الاختصاص: {self.jurisdiction}",
            f"وضع الإلزام: {_mode_label(self.mode)}",
            "قواعد التطبيق:",
            "- اعتبر كل قاعدة تحمل أولوية MANDATORY قاعدة ملزمة يجب التقيد بها.",
            "- لا تخالف أي مرجع وارد في هذه الحزمة من أجل تلبية الطلب.",
            (
                "- إذا احتاجت النتيجة المطلوبة إلى افتراضات تتجاوز المراجع الموردة، "
                "فاذكر هذا القيد صراحة."
            ),
            f"- التزم بهذا التوجيه التطبيقي: {self.application_instructions}",
            "حزمة المصادر والمعايير:",
        ]
        source: LegalReferenceSource
        for source in self.sources:
            lines.append(
                f"- [{source.source_id}] {source.title} | {source.authority} | {source.citation}"
            )
            if source.notes:
                lines.append(f"  ملاحظات: {source.notes}")
            rule: LegalReferenceRule
            for rule in source.rules:
                lines.append(
                    f"  - ({_priority_label(rule.priority)}) {rule.rule_id}: {rule.directive}"
                )
                if rule.applicability:
                    lines.append(f"    نطاق التطبيق: {rule.applicability}")
                if rule.rationale:
                    lines.append(f"    سبب الأهمية: {rule.rationale}")
        return "\n".join(lines)

    def render_user_block(self) -> str:
        """Render the profile into a compact user-side context summary.

        Args:
            None.

        Returns:
            A normalized string suitable for user-prompt injection.

        Raises:
            None.
        """
        lines: list[str] = [
            f"ملف المراجع: {self.profile_id}",
            f"عنوان الحزمة: {self.title}",
            "المراجع والمعايير الواجب مراعاتها:",
        ]
        source: LegalReferenceSource
        for source in self.sources:
            lines.append(f"- [{source.source_id}] {source.title} ({source.citation})")
        return "\n".join(lines)


def _mode_label(mode: LegalReferenceMode) -> str:
    """Return the Arabic display label for a legal-reference enforcement mode.

    Args:
        mode: Internal legal-reference enforcement mode.

    Returns:
        The Arabic label suitable for prompt rendering.

    Raises:
        None.
    """
    if mode == LegalReferenceMode.DISABLED:
        return "معطل"
    if mode == LegalReferenceMode.ADVISORY:
        return "استرشادي"
    return "ملزم"


def _priority_label(priority: LegalReferencePriority) -> str:
    """Return the Arabic display label for a legal-reference rule priority.

    Args:
        priority: Internal priority level for the rule.

    Returns:
        The Arabic label suitable for prompt rendering.

    Raises:
        None.
    """
    labels: dict[LegalReferencePriority, str] = {
        LegalReferencePriority.MANDATORY: "ملزم",
        LegalReferencePriority.HIGH: "مرتفع",
        LegalReferencePriority.MEDIUM: "متوسط",
        LegalReferencePriority.LOW: "منخفض",
    }
    return labels[priority]
