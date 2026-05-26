"""Prompt loading and rendering utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml  # type: ignore[import-untyped]
from jinja2 import Environment, StrictUndefined

from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.legal_references.models import LegalReferenceMode, LegalReferenceProfile

_env = Environment(
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(slots=True)
class PromptRender:
    """Represent a fully rendered prompt ready for provider submission.

    Args:
        tool_id: Stable tool identifier associated with the prompt.
        version: Prompt version string.
        system_prompt: Rendered system prompt content.
        user_prompt: Rendered user prompt content.
        defaults: Provider defaults extracted from the prompt file.
        metadata: Additional prompt metadata used for validation or tooling.
        legal_reference_profile_id: Optional legal-reference profile applied to the render.
        legal_reference_mode: Prompt-level legal-reference enforcement mode.

    Returns:
        None.

    Raises:
        None.
    """

    tool_id: str
    version: str
    system_prompt: str
    user_prompt: str
    defaults: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    legal_reference_profile_id: str | None = None
    legal_reference_mode: LegalReferenceMode = LegalReferenceMode.DISABLED


@dataclass(slots=True)
class PromptSection:
    """Represent a reusable titled prompt section.

    Args:
        title: Human-readable section title rendered into the prompt.
        body: Section body content that may include template variables.

    Returns:
        None.

    Raises:
        None.
    """

    title: str
    body: str


@dataclass(slots=True)
class PromptTemplate:
    """Represent a loaded prompt template before variable rendering.

    Args:
        tool_id: Stable tool identifier associated with the prompt.
        version: Prompt version string.
        system_sections: Structured sections for the system prompt.
        user_sections: Structured sections for the user prompt.
        defaults: Provider defaults extracted from the prompt file.
        metadata: Additional prompt metadata used for validation or tooling.
        legal_reference_mode: Prompt-level legal-reference enforcement mode.

    Returns:
        None.

    Raises:
        None.
    """

    tool_id: str
    version: str
    system_sections: list[PromptSection]
    user_sections: list[PromptSection]
    defaults: dict[str, Any]
    metadata: dict[str, Any]
    legal_reference_mode: LegalReferenceMode

    def render(
        self,
        context: dict[str, Any],
        *,
        legal_reference_profile: LegalReferenceProfile | None = None,
    ) -> PromptRender:
        """Render the template sections with the supplied context.

        Args:
            context: Template variables injected into system and user prompt sections.
            legal_reference_profile: Optional structured legal-reference packet applied
                to the render.

        Returns:
            A rendered prompt object ready for provider submission.

        Raises:
            jinja2.exceptions.TemplateError: If the prompt cannot be rendered with the context.
        """
        system_prompt = _render_sections(self.system_sections, context)
        language_section = _render_language_system_section(self.metadata.get("language"))
        if language_section is not None:
            system_prompt = "\n\n".join([system_prompt, language_section]).strip()
        user_prompt = _render_sections(self.user_sections, context)
        if (
            self.legal_reference_mode != LegalReferenceMode.DISABLED
            and legal_reference_profile is not None
        ):
            system_prompt = "\n\n".join(
                [
                    system_prompt,
                    _render_legal_reference_system_section(
                        legal_reference_profile,
                        legal_reference_mode=self.legal_reference_mode,
                    ),
                ]
            ).strip()
            user_prompt = "\n\n".join(
                [
                    user_prompt,
                    _render_legal_reference_user_section(legal_reference_profile),
                ]
            ).strip()
        return PromptRender(
            tool_id=self.tool_id,
            version=self.version,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            defaults=self.defaults,
            metadata=self.metadata,
            legal_reference_profile_id=(
                legal_reference_profile.profile_id if legal_reference_profile is not None else None
            ),
            legal_reference_mode=self.legal_reference_mode,
        )


class PromptLoader:
    """Load YAML prompt templates from packaged resources.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    @staticmethod
    @lru_cache(maxsize=128)
    def load(relative_path: str) -> PromptTemplate:
        """Load, normalize, and validate a packaged YAML prompt template.

        Args:
            relative_path: Slash-delimited prompt path relative to `qanuni/prompts/`.

        Returns:
            A normalized prompt template object.

        Raises:
            FileNotFoundError: If the prompt file does not exist.
            QanuniValidationError: If the prompt schema or content is invalid.
        """
        path = files("qanuni").joinpath("prompts", *relative_path.split("/"))
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        system_sections = _normalize_sections(raw, field_name="system")
        user_sections = _normalize_sections(raw, field_name="user")
        _validate_sections(system_sections, field_name="system")
        _validate_sections(user_sections, field_name="user")
        return PromptTemplate(
            tool_id=raw["tool_id"],
            version=str(raw["version"]),
            system_sections=system_sections,
            user_sections=user_sections,
            defaults=raw.get("defaults", {}),
            metadata=raw.get("metadata", {}),
            legal_reference_mode=_normalize_legal_reference_mode(raw.get("metadata", {})),
        )


def _normalize_legal_reference_mode(metadata: dict[str, Any]) -> LegalReferenceMode:
    """Normalize the prompt-level legal-reference mode from metadata.

    Args:
        metadata: Prompt metadata dictionary loaded from YAML.

    Returns:
        The normalized legal-reference mode declared by the prompt metadata.

    Raises:
        QanuniValidationError: If the prompt metadata contains an unsupported mode.
    """
    raw_mode: object = metadata.get("legal_reference_mode", LegalReferenceMode.DISABLED.value)
    if not isinstance(raw_mode, str):
        raise QanuniValidationError(
            "Prompt metadata field 'legal_reference_mode' must be a string.",
            error_code=ErrorCode.PROMPT_SCHEMA_INVALID,
            details={"field_name": "legal_reference_mode"},
        )
    try:
        return LegalReferenceMode(raw_mode)
    except ValueError as exc:
        raise QanuniValidationError(
            "Prompt metadata field 'legal_reference_mode' is invalid.",
            error_code=ErrorCode.PROMPT_SCHEMA_INVALID,
            details={"field_name": "legal_reference_mode", "value": raw_mode},
        ) from exc


def _normalize_sections(raw: dict[str, Any], *, field_name: str) -> list[PromptSection]:
    """Normalize raw or section-based prompt syntax into titled sections.

    Args:
        raw: Parsed YAML prompt payload.
        field_name: Prompt field being normalized, such as `system` or `user`.

    Returns:
        A normalized list of prompt sections.

    Raises:
        QanuniValidationError: If the prompt mixes incompatible schema forms.
    """
    direct_value = raw.get(field_name)
    section_key = f"{field_name}_sections"
    section_items = raw.get(section_key)

    if direct_value and section_items:
        raise QanuniValidationError(
            f"Prompt cannot define both '{field_name}' and '{section_key}'.",
            error_code=ErrorCode.PROMPT_SCHEMA_INVALID,
            details={"field_name": field_name, "section_key": section_key},
        )
    if isinstance(direct_value, str):
        title = "تعليمات النظام" if field_name == "system" else "طلب المستخدم"
        return [PromptSection(title=title, body=direct_value)]
    if isinstance(section_items, list):
        return [
            PromptSection(title=str(item["title"]), body=str(item["body"]))
            for item in section_items
        ]
    raise QanuniValidationError(
        f"Prompt must define either '{field_name}' or '{section_key}'.",
        error_code=ErrorCode.PROMPT_SCHEMA_INVALID,
        details={"field_name": field_name, "section_key": section_key},
    )


def _validate_sections(sections: list[PromptSection], *, field_name: str) -> None:
    """Validate prompt section completeness and minimum depth.

    Args:
        sections: Normalized prompt sections to validate.
        field_name: Prompt field being validated, such as `system` or `user`.

    Returns:
        None.

    Raises:
        QanuniValidationError: If the prompt sections are empty, malformed, or too shallow.
    """
    if not sections:
        raise QanuniValidationError(
            f"Prompt '{field_name}' sections cannot be empty.",
            error_code=ErrorCode.PROMPT_SCHEMA_INVALID,
            details={"field_name": field_name},
        )
    for section in sections:
        if not section.title.strip() or not section.body.strip():
            raise QanuniValidationError(
                f"Prompt '{field_name}' sections must have non-empty title and body.",
                error_code=ErrorCode.PROMPT_SCHEMA_INVALID,
                details={"field_name": field_name, "section_title": section.title},
            )
    combined_word_count = sum(len(section.body.split()) for section in sections)
    if combined_word_count < 25:
        raise QanuniValidationError(
            f"Prompt '{field_name}' content is too short to be production-ready.",
            error_code=ErrorCode.PROMPT_TOO_SHORT,
            details={"field_name": field_name, "word_count": combined_word_count},
        )


def _render_sections(sections: list[PromptSection], context: dict[str, Any]) -> str:
    """Render titled sections into a single provider-ready prompt string.

    Args:
        sections: Structured prompt sections to render.
        context: Template variables injected into each section.

    Returns:
        A single rendered prompt string suitable for provider submission.

    Raises:
        jinja2.exceptions.TemplateError: If a section cannot be rendered with the context.
    """
    rendered_sections: list[str] = []
    for section in sections:
        title = _env.from_string(section.title).render(**context)
        body = _env.from_string(section.body).render(**context)
        rendered_sections.append(f"# {title}\n{body}".strip())
    return "\n\n".join(rendered_sections)


def _render_legal_reference_system_section(
    legal_reference_profile: LegalReferenceProfile,
    *,
    legal_reference_mode: LegalReferenceMode,
) -> str:
    """Render the system-side legal-reference block appended to prompt content.

    Args:
        legal_reference_profile: Structured legal-reference packet to append.
        legal_reference_mode: Prompt-level enforcement mode declared by the prompt metadata.

    Returns:
        A provider-ready titled system section containing legal-reference rules.

    Raises:
        None.
    """
    title: str = "حزمة المراجع القانونية الملزمة"
    if legal_reference_mode == LegalReferenceMode.ADVISORY:
        title = "حزمة المراجع القانونية الاسترشادية"
    return f"# {title}\n{legal_reference_profile.render_system_block()}".strip()


def _render_legal_reference_user_section(legal_reference_profile: LegalReferenceProfile) -> str:
    """Render the user-side legal-reference summary appended to prompt content.

    Args:
        legal_reference_profile: Structured legal-reference packet to append.

    Returns:
        A provider-ready titled user section containing the reference summary.

    Raises:
        None.
    """
    return ("# سياق المراجع القانونية\n" f"{legal_reference_profile.render_user_block()}").strip()


def _render_language_system_section(language: object) -> str | None:
    """Render a normalized output-language policy when prompt metadata declares one.

    Args:
        language: Prompt metadata language value.

    Returns:
        A provider-ready language-policy section, or `None` when no policy is needed.

    Raises:
        None.
    """
    if language != "ar":
        return None
    return (
        "# سياسة اللغة\n"
        "يجب أن تكون جميع المخرجات النهائية والشرح والملاحظات والاقتراحات باللغة العربية "
        "الفصحى الواضحة.\n"
        "لا تستخدم الإنجليزية إلا عند نقل اسم منتج أو اختصار أو مصطلح ورد في الإدخال ولا "
        "توجد له ترجمة عملية دقيقة، وعندها اشرح معناه بالعربية."
    )
