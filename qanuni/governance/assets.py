"""Govern prompt and legal-reference assets through a checked-in manifest."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.governance.models import AssetManifest, GovernedAssetRecord

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_ROOT = PACKAGE_ROOT / "prompts"
LEGAL_REFERENCES_ROOT = PACKAGE_ROOT / "legal_references_data"
ASSET_MANIFEST_PATH = PACKAGE_ROOT / "governance" / "asset_manifest.json"


def compute_sha256_bytes(raw_bytes: bytes) -> str:
    """Return the SHA-256 digest for arbitrary bytes.

    Args:
        raw_bytes: Raw bytes to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.

    Raises:
        None.
    """
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file on disk.

    Args:
        path: File-system path to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.

    Raises:
        OSError: If the file cannot be read.
    """
    return compute_sha256_bytes(path.read_bytes())


def collect_current_asset_manifest() -> AssetManifest:
    """Build a manifest from the current prompt and legal-reference assets.

    Args:
        None.

    Returns:
        A fresh `AssetManifest` for the current working tree.

    Raises:
        OSError: If governed assets cannot be read.
    """
    assets: list[GovernedAssetRecord] = []
    prompt_path: Path
    for prompt_path in sorted(PROMPTS_ROOT.rglob("*.yaml")):
        relative_path = prompt_path.relative_to(PROMPTS_ROOT).as_posix()
        payload = yaml.safe_load(prompt_path.read_text(encoding="utf-8")) or {}
        assets.append(
            GovernedAssetRecord(
                asset_kind="prompt",
                relative_path=relative_path,
                asset_id=str(payload.get("tool_id", relative_path)),
                version=str(payload.get("version")) if payload.get("version") is not None else None,
                tool_ids=[str(payload.get("tool_id"))] if payload.get("tool_id") else [],
                sha256=compute_sha256_file(prompt_path),
            )
        )

    reference_path: Path
    for reference_path in sorted(LEGAL_REFERENCES_ROOT.rglob("*.yaml")):
        relative_path = reference_path.relative_to(LEGAL_REFERENCES_ROOT).as_posix()
        payload = yaml.safe_load(reference_path.read_text(encoding="utf-8")) or {}
        raw_tool_ids = payload.get("tool_ids") or []
        assets.append(
            GovernedAssetRecord(
                asset_kind="legal_reference",
                relative_path=relative_path,
                asset_id=str(payload.get("profile_id", relative_path)),
                version=None,
                tool_ids=[str(tool_id) for tool_id in raw_tool_ids],
                sha256=compute_sha256_file(reference_path),
            )
        )

    fingerprint_material = json.dumps(
        [asset.model_dump(mode="json") for asset in assets],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return AssetManifest(
        fingerprint=compute_sha256_bytes(fingerprint_material),
        assets=assets,
    )


def load_packaged_asset_manifest() -> AssetManifest:
    """Load the checked-in asset manifest from disk.

    Args:
        None.

    Returns:
        The packaged `AssetManifest`.

    Raises:
        OSError: If the manifest file cannot be read.
        ValidationError: If the manifest file is malformed.
    """
    return AssetManifest.model_validate_json(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))


def validate_asset_manifest() -> AssetManifest:
    """Validate that the checked-in asset manifest matches current assets.

    Args:
        None.

    Returns:
        The fresh current manifest when validation succeeds.

    Raises:
        QanuniValidationError: If the checked-in manifest is stale or missing assets.
    """
    expected_manifest = load_packaged_asset_manifest()
    current_manifest = collect_current_asset_manifest()
    if expected_manifest.fingerprint != current_manifest.fingerprint:
        raise QanuniValidationError(
            "Prompt/legal-reference asset manifest is stale.",
            error_code=ErrorCode.CONFIG_INVALID,
            details={
                "expected_fingerprint": expected_manifest.fingerprint,
                "current_fingerprint": current_manifest.fingerprint,
                "manifest_path": str(ASSET_MANIFEST_PATH),
            },
        )
    return current_manifest


def write_asset_manifest() -> AssetManifest:
    """Regenerate and write the checked-in asset manifest.

    Args:
        None.

    Returns:
        The regenerated manifest that was written to disk.

    Raises:
        OSError: If the manifest cannot be written.
    """
    manifest = collect_current_asset_manifest()
    ASSET_MANIFEST_PATH.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


def resolve_prompt_asset_hash(relative_path: str | None) -> str | None:
    """Return the governed hash for one prompt file.

    Args:
        relative_path: Prompt path relative to `qanuni/prompts/`.

    Returns:
        The SHA-256 digest for the prompt file, or `None` when no path is supplied.

    Raises:
        OSError: If the prompt file cannot be read.
    """
    if relative_path is None:
        return None
    return compute_sha256_file(PROMPTS_ROOT.joinpath(*relative_path.split("/")))


def resolve_legal_reference_asset_hash(relative_path: str | None) -> str | None:
    """Return the governed hash for one legal-reference file.

    Args:
        relative_path: Reference path relative to `qanuni/legal_references_data/`.

    Returns:
        The SHA-256 digest for the reference file, or `None` when no path is supplied.

    Raises:
        OSError: If the reference file cannot be read.
    """
    if relative_path is None:
        return None
    return compute_sha256_file(LEGAL_REFERENCES_ROOT.joinpath(*relative_path.split("/")))


def resolve_logic_asset_hash(subject: Any) -> str | None:
    """Return a source-file hash for one tool or workflow class.

    Args:
        subject: Class or callable whose source file should be fingerprinted.

    Returns:
        The SHA-256 digest of the source file, or `None` when no file is available.

    Raises:
        OSError: If the source file cannot be read.
    """
    source_file = inspect.getsourcefile(subject)
    if source_file is None:
        return None
    return compute_sha256_file(Path(source_file))
