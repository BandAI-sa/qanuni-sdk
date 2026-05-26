"""CLI helpers for governed prompt and legal-reference assets."""

from __future__ import annotations

import argparse

from qanuni.governance.assets import validate_asset_manifest, write_asset_manifest


def main() -> None:
    """Run the governance utility CLI.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: If CLI parsing fails or manifest validation fails.
    """
    parser = argparse.ArgumentParser(description="Qanuni governed asset utilities.")
    parser.add_argument(
        "command",
        choices=("validate-assets", "write-assets"),
        help="Governed-asset command to execute.",
    )
    args = parser.parse_args()
    if args.command == "validate-assets":
        manifest = validate_asset_manifest()
        print(manifest.fingerprint)
        return
    manifest = write_asset_manifest()
    print(manifest.fingerprint)


if __name__ == "__main__":
    main()
