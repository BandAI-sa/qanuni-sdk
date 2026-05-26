"""Inspect the installed package, artifact paths, sample documents, and catalog."""

from __future__ import annotations

from dataclasses import asdict

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_environment,
    emit_json,
    emit_sample_document_index,
    emit_tool_catalog,
    parse_standard_args,
)

ensure_project_root_on_path()


def main() -> None:
    """Run the environment-and-catalog human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Inspect the installed SDK surface before deeper human testing."
    )
    context = build_context(title="Example 00 - Environment and Catalog", args=args)

    emit_environment(context)
    emit_sample_document_index()
    emit_tool_catalog(context.client)
    emit_json(
        "Agent capabilities",
        [
            asdict(capability)
            for capability in context.client.agent.list_capabilities()
        ],
    )


if __name__ == "__main__":
    main()
