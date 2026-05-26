"""Prompt and legal-reference governance models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class GovernedAssetRecord(BaseModel):
    """Represent one governed prompt or legal-reference file.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    asset_kind: Literal["prompt", "legal_reference"]
    relative_path: str
    asset_id: str
    version: str | None = None
    tool_ids: list[str] = Field(default_factory=list)
    sha256: str


class AssetManifest(BaseModel):
    """Represent the checked-in lock file for governed assets.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    manifest_version: str = "1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fingerprint: str
    assets: list[GovernedAssetRecord]
