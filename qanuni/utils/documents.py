"""Document input normalization helpers."""

from __future__ import annotations

from pathlib import Path

from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.utils.pdf_parser import extract_pdf_text


def resolve_document_text(*, text: str | None, file_path: str | None) -> str:
    """Resolve raw text directly or load it from a supported file path.

    Args:
        text: Raw text payload supplied directly by the caller.
        file_path: Optional file-system path to a text or PDF document.

    Returns:
        The resolved document text.

    Raises:
        QanuniValidationError: If neither a text payload nor a valid file path is supplied.
        QanuniConfigError: If PDF support is requested without optional dependencies.
    """
    if text:
        return text
    if not file_path:
        raise QanuniValidationError(
            "A text payload or file path is required.",
            error_code=ErrorCode.VALIDATION_DOCUMENT_SOURCE_MISSING,
        )

    path: Path = Path(file_path)
    if not path.exists():
        raise QanuniValidationError(
            f"Document path does not exist: {path}",
            error_code=ErrorCode.VALIDATION_DOCUMENT_PATH_MISSING,
            details={"file_path": str(path)},
        )
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path)
    return path.read_text(encoding="utf-8")
