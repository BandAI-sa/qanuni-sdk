"""Exercise the atomic legal tools with one Arabic service-agreement sample."""

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_document_excerpt,
    emit_environment,
    emit_model,
    emit_observability,
    emit_tool_catalog,
    load_sample_document,
    parse_standard_args,
)

ensure_project_root_on_path()


def main() -> None:
    """Run the atomic legal-extraction human-testing example.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Inspect classification and atomic extraction outputs in full detail."
    )
    context = build_context(title="Example 02 - Atomic Legal Extraction", args=args)
    document_text = load_sample_document("service_agreement_ar.md")

    emit_environment(context)
    emit_tool_catalog(context.client, namespace="legal")
    emit_document_excerpt("service_agreement_ar.md")

    classification = context.client.legal.classify_document_type(
        document_text=document_text,
        document_type="service_agreement",
    )
    clauses = context.client.legal.extract_clauses(
        document_text=document_text,
        document_type="service_agreement",
    )
    parties = context.client.legal.extract_parties(
        document_text=document_text,
        document_type="service_agreement",
    )
    dates = context.client.legal.extract_dates(
        document_text=document_text,
        document_type="service_agreement",
    )
    amounts = context.client.legal.extract_amounts(
        document_text=document_text,
        document_type="service_agreement",
    )
    obligations = context.client.legal.extract_obligations(
        document_text=document_text,
        document_type="service_agreement",
    )
    termination_terms = context.client.legal.extract_termination_terms(
        document_text=document_text,
        document_type="service_agreement",
    )
    dispute_resolution = context.client.legal.extract_dispute_resolution(
        document_text=document_text,
        document_type="service_agreement",
    )

    emit_model("Document classification", classification)
    emit_model("Clause extraction", clauses)
    emit_model("Party extraction", parties)
    emit_model("Date extraction", dates)
    emit_model("Amount extraction", amounts)
    emit_model("Obligation extraction", obligations)
    emit_model("Termination-term extraction", termination_terms)
    emit_model("Dispute-resolution extraction", dispute_resolution)
    emit_observability(context)


if __name__ == "__main__":
    main()
