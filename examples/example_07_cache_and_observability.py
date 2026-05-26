"""Demonstrate cache reuse and observability events with repeated tool calls."""

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_document_excerpt,
    emit_environment,
    emit_json,
    emit_model,
    emit_observability,
    load_sample_document,
    parse_standard_args,
)

ensure_project_root_on_path()


def main() -> None:
    """Run the cache-and-observability human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Show how the selective cache and observability recorder behave across repeated calls."
    )
    context = build_context(title="Example 07 - Cache and Observability", args=args)
    cache_probe_text = (
        load_sample_document("service_agreement_ar.md")
        + "\n\n[human-example-cache-probe:v1]"
    )

    emit_environment(context)
    emit_document_excerpt("service_agreement_ar.md")

    context.client.observability.clear()
    first = context.client.contracts.risk_score(
        contract_text=cache_probe_text,
        contract_type="service_agreement",
    )
    second = context.client.contracts.risk_score(
        contract_text=cache_probe_text,
        contract_type="service_agreement",
    )

    emit_model("First risk-score call", first)
    emit_model("Second risk-score call", second)
    emit_json(
        "Cache directory snapshot",
        {
            "cache_dir": str(context.artifact_paths.cache_dir),
            "cache_files": [
                str(path)
                for path in sorted(context.artifact_paths.cache_dir.rglob("*.json"))
            ],
        },
    )
    emit_observability(context)


if __name__ == "__main__":
    main()
