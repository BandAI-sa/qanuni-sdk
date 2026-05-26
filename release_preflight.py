"""Release preflight checks for serious Qanuni package publishing."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qanuni._version import __version__

MODULE_ROOT: Path = Path(__file__).resolve().parent
PACKAGE_NAME: str = "qanuni-sdk"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    """Store the result of a single release preflight check.

    Args:
        name: Stable machine-readable check identifier.
        status: Final status for the check.
        details: Structured metadata explaining the observed state.

    Returns:
        None.

    Raises:
        None.
    """

    name: str
    status: str
    details: dict[str, Any]


def _run_git(args: list[str]) -> str:
    """Run a git command and return trimmed stdout.

    Args:
        args: Git arguments excluding the `git` executable itself.

    Returns:
        Trimmed command stdout.

    Raises:
        RuntimeError: If the git command fails.
    """
    completed = subprocess.run(
        ["git", *args],
        cwd=_require_source_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Git command failed.")
    return completed.stdout.strip()


def _discover_source_root() -> Path | None:
    """Locate a source checkout root when the command runs inside a repository.

    Args:
        None.

    Returns:
        The source root containing `pyproject.toml`, or `None` when unavailable.

    Raises:
        None.
    """
    candidate_paths: list[Path] = []
    candidate_paths.extend([Path.cwd(), *Path.cwd().parents])
    candidate_paths.extend([MODULE_ROOT, *MODULE_ROOT.parents])

    seen_paths: set[Path] = set()
    for candidate_path in candidate_paths:
        if candidate_path in seen_paths:
            continue
        seen_paths.add(candidate_path)
        if (candidate_path / "pyproject.toml").exists():
            return candidate_path
    return None


SOURCE_ROOT: Path | None = _discover_source_root()


def _require_source_root() -> Path:
    """Return the repository root or raise when the command runs outside a checkout.

    Args:
        None.

    Returns:
        The repository root path.

    Raises:
        RuntimeError: If no source checkout root can be located.
    """
    if SOURCE_ROOT is None:
        raise RuntimeError(
            "No source checkout was found. This check requires running from a repository clone."
        )
    return SOURCE_ROOT


def _load_pyproject() -> dict[str, Any]:
    """Load the current project metadata from `pyproject.toml`.

    Args:
        None.

    Returns:
        The parsed TOML payload.

    Raises:
        OSError: If the file cannot be read.
        tomllib.TOMLDecodeError: If the file contains invalid TOML.
    """
    return tomllib.loads((_require_source_root() / "pyproject.toml").read_text(encoding="utf-8"))


def _load_installed_metadata() -> importlib.metadata.PackageMetadata | None:
    """Load installed package metadata when the command runs from an installed wheel.

    Args:
        None.

    Returns:
        The installed package metadata, or `None` when unavailable.

    Raises:
        None.
    """
    try:
        return importlib.metadata.metadata(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return None


def _pass(name: str, **details: Any) -> CheckOutcome:
    """Build a passing check result.

    Args:
        name: Stable machine-readable check identifier.
        **details: Structured metadata for the check.

    Returns:
        A passing check outcome.

    Raises:
        None.
    """
    return CheckOutcome(name=name, status="PASS", details=details)


def _warn(name: str, **details: Any) -> CheckOutcome:
    """Build a warning check result.

    Args:
        name: Stable machine-readable check identifier.
        **details: Structured metadata for the check.

    Returns:
        A warning check outcome.

    Raises:
        None.
    """
    return CheckOutcome(name=name, status="WARN", details=details)


def _fail(name: str, **details: Any) -> CheckOutcome:
    """Build a failing check result.

    Args:
        name: Stable machine-readable check identifier.
        **details: Structured metadata for the check.

    Returns:
        A failing check outcome.

    Raises:
        None.
    """
    return CheckOutcome(name=name, status="FAIL", details=details)


def check_version_format() -> CheckOutcome:
    """Ensure the package version looks publishable for PyPI.

    Args:
        None.

    Returns:
        A check outcome describing version validity.

    Raises:
        None.
    """
    pattern: re.Pattern[str] = re.compile(r"^\d+\.\d+\.\d+(?:[abrc]\d+)?$")
    if pattern.match(__version__):
        return _pass("version_format", version=__version__)
    return _fail(
        "version_format",
        version=__version__,
        reason="Version does not match the expected release pattern.",
    )


def check_core_files() -> CheckOutcome:
    """Ensure required release files exist in the repository root.

    Args:
        None.

    Returns:
        A check outcome describing whether the expected files are present.

    Raises:
        None.
    """
    required_files: tuple[str, ...] = (
        "LICENSE",
        "CHANGELOG.md",
        "README.md",
        "README_PYPI.md",
        "docs/guides/README_PUBLISHING.md",
    )
    if SOURCE_ROOT is None:
        return _warn(
            "core_files",
            reason=(
                "Source checkout not found. Root release files cannot be "
                "inspected from installed mode."
            ),
        )
    missing_files: list[str] = [
        file_name
        for file_name in required_files
        if not (_require_source_root() / file_name).exists()
    ]
    if not missing_files:
        return _pass("core_files", files=list(required_files))
    return _fail("core_files", missing=missing_files)


def check_pyproject_metadata() -> CheckOutcome:
    """Inspect release-sensitive metadata in `pyproject.toml`.

    Args:
        None.

    Returns:
        A check outcome describing metadata completeness.

    Raises:
        None.
    """
    if SOURCE_ROOT is not None:
        pyproject: dict[str, Any] = _load_pyproject()
        project: dict[str, Any] = pyproject.get("project", {})
    else:
        installed_metadata = _load_installed_metadata()
        if installed_metadata is None:
            return _fail(
                "pyproject_metadata",
                reason="Neither source pyproject.toml nor installed package metadata is available.",
            )
        project = {
            "name": installed_metadata.get("Name"),
            "readme": installed_metadata.get("Description-Content-Type"),
            "requires-python": installed_metadata.get("Requires-Python"),
            "license": installed_metadata.get("License-Expression")
            or installed_metadata.get("License"),
            "license-files": installed_metadata.get_all("License-File") or [],
            "urls": {
                url_entry.split(", ", 1)[0]: url_entry.split(", ", 1)[1]
                for url_entry in installed_metadata.get_all("Project-URL") or []
                if ", " in url_entry
            },
        }
    warnings: list[str] = []

    if not project.get("name"):
        return _fail("pyproject_metadata", reason="Missing project.name.")
    if not project.get("readme"):
        return _fail("pyproject_metadata", reason="Missing project.readme.")
    if not project.get("requires-python"):
        return _fail("pyproject_metadata", reason="Missing project.requires-python.")
    if not project.get("license"):
        return _fail("pyproject_metadata", reason="Missing project.license.")
    if not project.get("license-files"):
        return _fail("pyproject_metadata", reason="Missing project.license-files.")

    project_urls: dict[str, Any] = project.get("urls", {})
    if not project_urls:
        warnings.append("project.urls is not configured yet.")

    if warnings:
        return _warn(
            "pyproject_metadata",
            package_name=project.get("name"),
            warnings=warnings,
        )
    return _pass(
        "pyproject_metadata",
        package_name=project.get("name"),
        has_urls=True,
    )


def check_git_remote() -> CheckOutcome:
    """Check whether the repository has at least one configured git remote.

    Args:
        None.

    Returns:
        A check outcome describing the current remote configuration.

    Raises:
        None.
    """
    if SOURCE_ROOT is None:
        return _warn(
            "git_remote",
            reason=(
                "No source checkout was found. Git remotes cannot be inspected "
                "from installed mode."
            ),
        )

    try:
        remote_lines: list[str] = [
            line for line in _run_git(["remote", "-v"]).splitlines() if line.strip()
        ]
    except RuntimeError as exc:
        return _fail("git_remote", reason=str(exc))

    if not remote_lines:
        return _warn(
            "git_remote",
            reason="No git remote is configured. project.urls and release push steps stay manual.",
        )
    return _pass("git_remote", remotes=remote_lines)


def check_worktree_clean(*, allow_dirty: bool) -> CheckOutcome:
    """Check whether the current worktree is clean for release work.

    Args:
        allow_dirty: Whether to downgrade a dirty worktree from failure to warning.

    Returns:
        A check outcome describing the repository cleanliness.

    Raises:
        None.
    """
    if SOURCE_ROOT is None:
        return _warn(
            "worktree_clean",
            reason="No source checkout was found. Worktree cleanliness cannot be inspected.",
        )

    try:
        status_output: str = _run_git(["status", "--short"])
    except RuntimeError as exc:
        return _fail("worktree_clean", reason=str(exc))

    entries: list[str] = [line for line in status_output.splitlines() if line.strip()]
    if not entries:
        return _pass("worktree_clean")

    if allow_dirty:
        return _warn(
            "worktree_clean",
            entries=entries,
            reason="Dirty worktree allowed by caller override.",
        )
    return _fail(
        "worktree_clean",
        entries=entries,
        reason="Release publishing should start from a clean worktree.",
    )


def check_tag_alignment(*, expected_tag: str | None) -> CheckOutcome:
    """Validate an expected release tag against the package version.

    Args:
        expected_tag: Optional explicit tag expected for the release.

    Returns:
        A check outcome describing whether tag expectations are aligned.

    Raises:
        None.
    """
    suggested_tag: str = f"v{__version__}"
    if expected_tag is None:
        return _warn(
            "tag_alignment",
            suggested_tag=suggested_tag,
            reason="No explicit release tag was provided to validate.",
        )

    if expected_tag == suggested_tag:
        return _pass("tag_alignment", expected_tag=expected_tag, version=__version__)
    return _fail(
        "tag_alignment",
        expected_tag=expected_tag,
        suggested_tag=suggested_tag,
        version=__version__,
    )


def check_publish_workflow() -> CheckOutcome:
    """Ensure the publish workflow file exists in the expected location.

    Args:
        None.

    Returns:
        A check outcome describing workflow availability.

    Raises:
        None.
    """
    if SOURCE_ROOT is None:
        return _warn(
            "publish_workflow",
            reason=(
                "No source checkout was found. Workflow files cannot be "
                "inspected from installed mode."
            ),
        )
    workflow_path: Path = _require_source_root() / ".github" / "workflows" / "publish.yml"
    if workflow_path.exists():
        return _pass("publish_workflow", path=str(workflow_path))
    return _fail("publish_workflow", reason="Missing .github/workflows/publish.yml.")


def check_distribution_artifacts() -> CheckOutcome:
    """Check whether current `dist/` artifacts exist for manual release validation.

    Args:
        None.

    Returns:
        A check outcome describing distribution availability.

    Raises:
        None.
    """
    if SOURCE_ROOT is None:
        return _warn(
            "distribution_artifacts",
            reason=(
                "No source checkout was found. Local dist artifacts cannot be "
                "inspected from installed mode."
            ),
        )
    dist_dir: Path = _require_source_root() / "dist"
    wheel_files: list[str] = sorted(path.name for path in dist_dir.glob("*.whl"))
    sdist_files: list[str] = sorted(path.name for path in dist_dir.glob("*.tar.gz"))
    if wheel_files and sdist_files:
        return _pass(
            "distribution_artifacts",
            wheel_files=wheel_files,
            sdist_files=sdist_files,
        )
    return _warn(
        "distribution_artifacts",
        wheel_files=wheel_files,
        sdist_files=sdist_files,
        reason="No fresh build artifacts detected yet.",
    )


def _serialize(value: Any) -> Any:
    """Convert arbitrary check values into JSON-friendly output.

    Args:
        value: Arbitrary Python value to serialize.

    Returns:
        A JSON-friendly representation.

    Raises:
        None.
    """
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _print_human_report(outcomes: list[CheckOutcome]) -> None:
    """Print a human-readable release preflight report.

    Args:
        outcomes: Ordered list of check results to display.

    Returns:
        None.

    Raises:
        None.
    """
    print("Qanuni Release Preflight")
    print("========================")
    for outcome in outcomes:
        print(f"[{outcome.status}] {outcome.name}")
        print(json.dumps(_serialize(outcome.details), ensure_ascii=False, indent=2))
    failed_count: int = sum(1 for outcome in outcomes if outcome.status == "FAIL")
    warning_count: int = sum(1 for outcome in outcomes if outcome.status == "WARN")
    print("\nSummary")
    print("-------")
    print(f"Failed: {failed_count}")
    print(f"Warnings: {warning_count}")


def main() -> int:
    """Run release-preflight checks for a serious package publication.

    Args:
        None.

    Returns:
        Process exit code where `0` means no failures and `1` means at least one failure.

    Raises:
        None.
    """
    parser = argparse.ArgumentParser(
        description="Run release-preflight checks before publishing qanuni-sdk."
    )
    parser.add_argument(
        "--tag",
        help="Expected release tag, for example v0.1.0.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Downgrade dirty-worktree failures to warnings.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the human report.",
    )
    args = parser.parse_args()

    outcomes: list[CheckOutcome] = [
        check_version_format(),
        check_core_files(),
        check_pyproject_metadata(),
        check_git_remote(),
        check_worktree_clean(allow_dirty=args.allow_dirty),
        check_tag_alignment(expected_tag=args.tag),
        check_publish_workflow(),
        check_distribution_artifacts(),
    ]

    if args.json:
        print(
            json.dumps(
                [_serialize(asdict(outcome)) for outcome in outcomes],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_human_report(outcomes)

    return 1 if any(outcome.status == "FAIL" for outcome in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
