"""Optional PDF text extraction support."""

from __future__ import annotations

from pathlib import Path

from qanuni.core.exceptions import ErrorCode, QanuniConfigError


def extract_pdf_text(path: str | Path) -> str:
    """Extract text from a PDF file using the optional pdfplumber dependency.

    Args:
        path: File-system path to the PDF document.

    Returns:
        The extracted text content from all PDF pages.

    Raises:
        QanuniConfigError: If PDF support is unavailable in the current installation.
        OSError: If the PDF file cannot be opened or read.
    """
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError as exc:
        raise QanuniConfigError(
            "PDF support requires the 'pdf' extra. Install with `pip install qanuni-sdk[pdf]`."
            ,
            error_code=ErrorCode.CONFIG_INVALID,
            details={"missing_dependency": "pdfplumber"},
        ) from exc

    pdf_path = Path(path)
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
