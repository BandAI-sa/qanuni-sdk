"""Load packaged Arabic sample documents for acceptance experiments."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def list_sample_documents() -> list[str]:
    """Return the packaged acceptance-document names.

    Args:
        None.

    Returns:
        Sorted list of packaged sample-document names.

    Raises:
        None.
    """
    documents_root = files("qanuni").joinpath("acceptance_data", "documents")
    return sorted(item.name for item in documents_root.iterdir() if item.is_file())


def sample_document_path(name: str) -> Path:
    """Return the on-disk path of one packaged acceptance document.

    Args:
        name: Packaged document file name such as `service_agreement_ar.md`.

    Returns:
        Absolute file-system path to the packaged sample document.

    Raises:
        FileNotFoundError: If the requested document does not exist.
    """
    document_path = files("qanuni").joinpath("acceptance_data", "documents", name)
    if not document_path.is_file():
        raise FileNotFoundError(name)
    return Path(str(document_path))


def load_sample_document(name: str) -> str:
    """Return the text of one packaged acceptance document.

    Args:
        name: Packaged document file name such as `service_agreement_ar.md`.

    Returns:
        UTF-8 document text.

    Raises:
        FileNotFoundError: If the requested document does not exist.
    """
    document_path = sample_document_path(name)
    return document_path.read_text(encoding="utf-8")
