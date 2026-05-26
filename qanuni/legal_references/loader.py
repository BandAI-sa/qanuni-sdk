"""Load packaged or external legal-reference profiles for prompt enforcement."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.legal_references.models import LegalReferenceProfile


class LegalReferenceLoader:
    """Load YAML legal-reference profiles from packaged resources or override folders.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    @staticmethod
    def load(
        relative_path: str,
        *,
        external_catalog_dir: Path | None = None,
    ) -> LegalReferenceProfile:
        """Load and validate a legal-reference profile from YAML.

        Args:
            relative_path: Slash-delimited path relative to `qanuni/legal_references_data/`.
            external_catalog_dir: Optional override directory searched before packaged data.

        Returns:
            A validated legal-reference profile.

        Raises:
            QanuniValidationError: If the file is missing or the YAML schema is invalid.
        """
        cache_key: str | None = None
        if external_catalog_dir is not None:
            cache_key = str(external_catalog_dir.resolve())
        return _load_reference_profile(relative_path, cache_key)


@lru_cache(maxsize=128)
def _load_reference_profile(
    relative_path: str,
    external_catalog_dir: str | None,
) -> LegalReferenceProfile:
    """Load and validate a legal-reference profile with LRU caching.

    Args:
        relative_path: Slash-delimited path relative to the packaged reference directory.
        external_catalog_dir: Optional resolved override directory as a string cache key.

    Returns:
        A validated legal-reference profile.

    Raises:
        QanuniValidationError: If the file is missing or the YAML schema is invalid.
    """
    source_path: Path | None = None
    if external_catalog_dir is not None:
        candidate_path: Path = Path(external_catalog_dir) / relative_path
        if candidate_path.exists():
            source_path = candidate_path

    raw_payload: Any
    if source_path is not None:
        raw_payload = _read_yaml_path(source_path)
    else:
        packaged_path = files("qanuni").joinpath(
            "legal_references_data",
            *relative_path.split("/"),
        )
        try:
            raw_payload = yaml.safe_load(packaged_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise QanuniValidationError(
                f"Legal reference file '{relative_path}' was not found.",
                error_code=ErrorCode.LEGAL_REFERENCE_FILE_MISSING,
                details={"relative_path": relative_path},
            ) from exc

    try:
        return LegalReferenceProfile.model_validate(raw_payload)
    except ValidationError as exc:
        raise QanuniValidationError(
            "The legal reference profile is invalid.",
            error_code=ErrorCode.LEGAL_REFERENCE_INVALID,
            details={"relative_path": relative_path},
        ) from exc


def _read_yaml_path(path: Path) -> Any:
    """Read a YAML file from disk and return its parsed payload.

    Args:
        path: File-system path to the YAML reference profile.

    Returns:
        The parsed YAML payload.

    Raises:
        QanuniValidationError: If the file cannot be read.
    """
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise QanuniValidationError(
            f"Could not read the legal reference file at '{path}'.",
            error_code=ErrorCode.LEGAL_REFERENCE_FILE_MISSING,
            details={"path": str(path)},
        ) from exc
