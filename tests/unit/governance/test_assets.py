"""Tests for prompt and legal-reference governance assets."""

from __future__ import annotations

from qanuni.client import LegalClient
from qanuni.governance import (
    load_packaged_asset_manifest,
    resolve_logic_asset_hash,
    resolve_prompt_asset_hash,
    validate_asset_manifest,
)


def test_packaged_asset_manifest_matches_current_assets() -> None:
    """Ensure the checked-in asset manifest is current.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If the checked-in manifest is missing governed assets.
    """
    current_manifest = validate_asset_manifest()
    packaged_manifest = load_packaged_asset_manifest()
    assert current_manifest.fingerprint == packaged_manifest.fingerprint
    assert current_manifest.assets


def test_asset_hash_helpers_return_values() -> None:
    """Resolve prompt and logic hashes for governed runtime surfaces.

    Args:
        None.

    Returns:
        None.

    Raises:
        AssertionError: If any governed hash cannot be resolved.
    """
    assert resolve_prompt_asset_hash("contracts/gap_analysis.yaml") is not None
    assert resolve_logic_asset_hash(LegalClient) is not None
