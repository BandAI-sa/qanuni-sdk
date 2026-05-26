from __future__ import annotations

import ast
from pathlib import Path


def test_public_package_definitions_have_docstrings() -> None:
    """Public classes and callables in the package should carry docstrings."""
    package_root = Path("qanuni")
    missing: list[str] = []

    for path in package_root.rglob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("__"):
                    continue
                if ast.get_docstring(node) is None:
                    missing.append(f"{path.as_posix()}::{node.name}")
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name.startswith("__") or child.name.startswith("_"):
                            continue
                        if ast.get_docstring(child) is None:
                            missing.append(f"{path.as_posix()}::{node.name}.{child.name}")

    assert missing == []


def test_public_callables_follow_google_style_sections() -> None:
    """Public functions and methods should use summary, args, returns, and raises sections."""
    package_root = Path("qanuni")
    violations: list[str] = []

    for path in package_root.rglob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            is_public_callable = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                not node.name.startswith("__")
            )
            if is_public_callable:
                _collect_callable_docstring_violations(
                    node=node,
                    label=f"{path.as_posix()}::{node.name}",
                    violations=violations,
                )
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name.startswith("__") or child.name.startswith("_"):
                            continue
                        _collect_callable_docstring_violations(
                            node=child,
                            label=f"{path.as_posix()}::{node.name}.{child.name}",
                            violations=violations,
                        )

    assert violations == []


def test_public_callables_have_explicit_type_annotations() -> None:
    """Public functions and methods should declare explicit parameter and return annotations."""
    package_root = Path("qanuni")
    violations: list[str] = []

    for path in package_root.rglob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            is_public_callable = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                not node.name.startswith("__")
            )
            if is_public_callable:
                _collect_annotation_violations(
                    node=node,
                    label=f"{path.as_posix()}::{node.name}",
                    violations=violations,
                )
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name.startswith("__") or child.name.startswith("_"):
                            continue
                        _collect_annotation_violations(
                            node=child,
                            label=f"{path.as_posix()}::{node.name}.{child.name}",
                            violations=violations,
                        )

    assert violations == []


def _collect_callable_docstring_violations(
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    label: str,
    violations: list[str],
) -> None:
    """Collect Google-style docstring violations for a callable."""
    docstring = ast.get_docstring(node)
    if docstring is None:
        return
    if not docstring.strip():
        violations.append(f"{label}::empty-docstring")
        return
    if "Args:" not in docstring:
        violations.append(f"{label}::missing-args")
    if "Returns:" not in docstring:
        violations.append(f"{label}::missing-returns")
    if "Raises:" not in docstring:
        violations.append(f"{label}::missing-raises")


def _collect_annotation_violations(
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    label: str,
    violations: list[str],
) -> None:
    """Collect typing-annotation violations for a callable."""
    if node.returns is None:
        violations.append(f"{label}::missing-return-annotation")

    positional_args = [*node.args.posonlyargs, *node.args.args]
    keyword_only_args = list(node.args.kwonlyargs)

    for arg in [*positional_args, *keyword_only_args]:
        if arg.arg in {"self", "cls"}:
            continue
        if arg.annotation is None:
            violations.append(f"{label}::missing-annotation:{arg.arg}")

    if node.args.vararg is not None and node.args.vararg.annotation is None:
        violations.append(f"{label}::missing-annotation:*{node.args.vararg.arg}")

    if node.args.kwarg is not None and node.args.kwarg.annotation is None:
        violations.append(f"{label}::missing-annotation:**{node.args.kwarg.arg}")
