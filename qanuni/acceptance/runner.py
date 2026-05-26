"""CLI runner for black-box user acceptance experiments."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from qanuni import LegalClient
from qanuni.acceptance.documents import (
    list_sample_documents,
    load_sample_document,
    sample_document_path,
)
from qanuni.acceptance.mock_provider import build_acceptance_provider
from qanuni.agent.models import AgentScenario
from qanuni.core.config import QanuniConfig
from qanuni.core.exceptions import QanuniError


@dataclass(frozen=True, slots=True)
class AcceptanceArtifactPaths:
    """Collect reusable artifact paths for one acceptance run.

    Args:
        root_dir: Root directory used by the acceptance pack.
        cache_dir: Directory used by selective caching during the run.
        observability_log_path: JSONL file used when observability persistence is enabled.
        mcp_audit_log_path: JSONL file used by the MCP smoke test.

    Returns:
        None.

    Raises:
        None.
    """

    root_dir: Path
    cache_dir: Path
    observability_log_path: Path
    mcp_audit_log_path: Path

    def as_json(self) -> dict[str, str]:
        """Return the artifact paths as JSON-friendly strings.

        Args:
            None.

        Returns:
            Dictionary of absolute artifact paths.

        Raises:
            None.
        """
        return {
            "root_dir": str(self.root_dir),
            "cache_dir": str(self.cache_dir),
            "observability_log_path": str(self.observability_log_path),
            "mcp_audit_log_path": str(self.mcp_audit_log_path),
        }


@dataclass(frozen=True, slots=True)
class AcceptanceScenarioSpec:
    """Describe one user-facing acceptance scenario.

    Args:
        name: Stable scenario identifier used by the CLI.
        description: Short human-readable description of the experiment.
        runner: Callable that executes the scenario and returns a serializable payload.
        requires_live_model: Whether the scenario requires a real OpenAI-backed provider.

    Returns:
        None.

    Raises:
        None.
    """

    name: str
    description: str
    runner: Callable[[LegalClient], Any]
    requires_live_model: bool = False


def resolve_acceptance_artifact_paths(
    working_dir: Path | None = None,
) -> AcceptanceArtifactPaths:
    """Resolve the directory layout used by the acceptance pack.

    Args:
        working_dir: Optional root directory for acceptance artifacts.

    Returns:
        Fully resolved artifact paths.

    Raises:
        OSError: If the selected working directory cannot be created.
    """
    root_dir = working_dir or Path(tempfile.mkdtemp(prefix="qanuni-acceptance-"))
    resolved_root = root_dir.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    return AcceptanceArtifactPaths(
        root_dir=resolved_root,
        cache_dir=resolved_root / ".qanuni_cache",
        observability_log_path=resolved_root / ".qanuni_observability" / "events.jsonl",
        mcp_audit_log_path=resolved_root / ".qanuni_audit" / "mcp_audit.jsonl",
    )


def build_acceptance_client(
    *,
    mode: Literal["mocked", "live"] = "mocked",
    cache_enabled: bool = True,
    observability_persist: bool = False,
    working_dir: Path | None = None,
) -> LegalClient:
    """Build a client suited to user-acceptance experiments.

    Args:
        mode: Whether to use a deterministic mocked provider or the live OpenAI provider.
        cache_enabled: Whether selective caching should be enabled during the run.
        observability_persist: Whether observability events should be written to disk.
        working_dir: Optional directory for cache and observability artifacts.

    Returns:
        Configured acceptance client.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
        OSError: If the selected working directory cannot be created.
    """
    artifact_paths = resolve_acceptance_artifact_paths(working_dir)
    common_kwargs: dict[str, Any] = {
        "cache_enabled": cache_enabled,
        "cache_dir": artifact_paths.cache_dir,
        "observability_persist": observability_persist,
        "observability_log_path": artifact_paths.observability_log_path,
        "agent_logging_enabled": True,
        "agent_log_dir": artifact_paths.root_dir / "logs" / "agent",
    }
    if mode == "live":
        _ensure_live_api_key_available()
        return LegalClient(**common_kwargs)
    return LegalClient(provider_factory=build_acceptance_provider, **common_kwargs)


def _ensure_live_api_key_available() -> None:
    """Ensure live acceptance runs can resolve an OpenAI key.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If no OpenAI key is available from the environment or `.env`.
    """
    direct_key = os.getenv("OPENAI_API_KEY", "").strip()
    if direct_key:
        return

    resolved_key = QanuniConfig().api_key_value()
    if resolved_key:
        os.environ["OPENAI_API_KEY"] = resolved_key
        return

    raise RuntimeError("OPENAI_API_KEY is required for live acceptance runs.")


def scenario_labor_basics(client: LegalClient) -> dict[str, Any]:
    """Run deterministic labor-tool acceptance scenarios.

    Args:
        client: Acceptance client used to execute the scenarios.

    Returns:
        Serializable summary of deterministic labor results.

    Raises:
        QanuniError: If one of the deterministic tools fails unexpectedly.
    """
    end_of_service = client.labor.end_of_service(
        monthly_salary=12000,
        years_of_service=7.5,
        termination_reason="resignation",
        contract_type="indefinite",
    )
    probation = client.labor.probation_check(
        probation_days=120,
        extension_in_writing=False,
        contract_type="indefinite",
    )
    return {
        "end_of_service": end_of_service.model_dump(mode="json"),
        "probation": probation.model_dump(mode="json"),
    }


def scenario_atomic_extraction(client: LegalClient) -> dict[str, Any]:
    """Run a focused acceptance pass over the atomic legal tools.

    Args:
        client: Acceptance client used to execute the atomic tools.

    Returns:
        Serializable summary of classification and extraction outputs.

    Raises:
        QanuniError: If one of the atomic tools fails unexpectedly.
    """
    document_text = load_sample_document("service_agreement_ar.md")
    classification = client.legal.classify_document_type(
        document_text=document_text,
        document_type="service_agreement",
    )
    clauses = client.legal.extract_clauses(
        document_text=document_text,
        document_type="service_agreement",
    )
    parties = client.legal.extract_parties(
        document_text=document_text,
        document_type="service_agreement",
    )
    dates = client.legal.extract_dates(
        document_text=document_text,
        document_type="service_agreement",
    )
    amounts = client.legal.extract_amounts(
        document_text=document_text,
        document_type="service_agreement",
    )
    obligations = client.legal.extract_obligations(
        document_text=document_text,
        document_type="service_agreement",
    )
    termination_terms = client.legal.extract_termination_terms(
        document_text=document_text,
        document_type="service_agreement",
    )
    dispute_resolution = client.legal.extract_dispute_resolution(
        document_text=document_text,
        document_type="service_agreement",
    )
    return {
        "classification": classification.model_dump(mode="json"),
        "clauses": clauses.model_dump(mode="json"),
        "parties": parties.model_dump(mode="json"),
        "dates": dates.model_dump(mode="json"),
        "amounts": amounts.model_dump(mode="json"),
        "obligations": obligations.model_dump(mode="json"),
        "termination_terms": termination_terms.model_dump(mode="json"),
        "dispute_resolution": dispute_resolution.model_dump(mode="json"),
    }


def scenario_contract_review(client: LegalClient) -> dict[str, Any]:
    """Run a contract-review workflow on the packaged sample agreement.

    Args:
        client: Acceptance client used to execute the workflow.

    Returns:
        Serializable workflow result.

    Raises:
        QanuniError: If the workflow fails unexpectedly.
    """
    result = client.workflow.contract_review(
        document_text=load_sample_document("service_agreement_ar.md"),
        contract_type="service_agreement",
        include_redlines=True,
    )
    return result.model_dump(mode="json")


def scenario_employment_review(client: LegalClient) -> dict[str, Any]:
    """Run an employment-review workflow on the packaged sample contract.

    Args:
        client: Acceptance client used to execute the workflow.

    Returns:
        Serializable workflow result.

    Raises:
        QanuniError: If the workflow fails unexpectedly.
    """
    result = client.workflow.employment_review(
        document_text=load_sample_document("employment_contract_ar.md"),
        document_type="employment_contract",
        contract_type="indefinite",
        probation_days=120,
        extension_in_writing=False,
        monthly_salary=10000,
        years_of_service=2,
        termination_reason="termination_by_employer",
    )
    return result.model_dump(mode="json")


def scenario_privacy_review(client: LegalClient) -> dict[str, Any]:
    """Run a privacy-compliance workflow on the packaged sample notice.

    Args:
        client: Acceptance client used to execute the workflow.

    Returns:
        Serializable workflow result.

    Raises:
        QanuniError: If the workflow fails unexpectedly.
    """
    result = client.workflow.privacy_compliance_review(
        document_text=load_sample_document("privacy_notice_ar.md"),
        processing_context="تطبيق توصيل",
        cross_border_transfers=True,
        generate_policy_draft=True,
        company_name="شركة ألف",
        service_type="منصة تقنية",
        data_collected=["الاسم", "رقم الجوال", "البريد الإلكتروني"],
        data_purposes=["تقديم الخدمة", "التواصل", "الدعم الفني"],
        third_party_sharing=True,
        international_transfers=True,
    )
    return result.model_dump(mode="json")


def scenario_agent_notice(client: LegalClient) -> dict[str, Any]:
    """Run the legal agent end to end for a contract-dispute notice scenario.

    Args:
        client: Acceptance client used to execute the agent.

    Returns:
        Serializable agent result.

    Raises:
        QanuniError: If the agent runtime fails unexpectedly.
    """
    result = client.agent.run(
        goal="أريد مراجعة العقد ثم تجهيز مسودة مطالبة قبل النزاع.",
        scenario_hint=AgentScenario.CONTRACT_DISPUTE_NOTICE,
        documents=[
            {
                "name": "عقد خدمات",
                "text": load_sample_document("service_agreement_ar.md"),
                "document_type": "service_agreement",
                "role": "primary",
            },
            {
                "name": "مستند داعم للمطالبة",
                "text": load_sample_document("prelitigation_support_ar.md"),
                "document_type": "demand_support",
                "role": "supporting",
            },
        ],
        facts={
            "sender_name": "شركة ألف",
            "recipient_name": "شركة باء",
            "claim_type": "مستحقات تعاقدية",
            "claim_amount": 85000,
            "incident_description": "تأخر في سداد مستحقات عقد خدمات تقنية.",
            "deadline_days": 7,
            "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
        },
    )
    return result.model_dump(mode="json")


def scenario_cache_and_observability(client: LegalClient) -> dict[str, Any]:
    """Show cache reuse and observability events on a review-style tool.

    Args:
        client: Acceptance client used to execute the tool.

    Returns:
        Serializable cache and observability summary.

    Raises:
        QanuniError: If the tool fails unexpectedly.
    """
    client.observability.clear()
    cache_probe_text = (
        load_sample_document("service_agreement_ar.md")
        + "\n\n[acceptance-cache-probe:v1]"
    )
    first = client.contracts.risk_score(
        contract_text=cache_probe_text,
        contract_type="service_agreement",
    )
    second = client.contracts.risk_score(
        contract_text=cache_probe_text,
        contract_type="service_agreement",
    )
    events = [event.model_dump(mode="json") for event in client.observability.snapshot()]
    cache_statuses = [event.get("cache_status") for event in events if event.get("scope_id")]
    return {
        "first_call": first.model_dump(mode="json"),
        "second_call": second.model_dump(mode="json"),
        "event_count": len(events),
        "cache_statuses": cache_statuses,
        "events": events,
    }


def scenario_faulty_input(client: LegalClient) -> dict[str, Any]:
    """Trigger one expected validation error to verify user-facing failures.

    Args:
        client: Acceptance client used to execute the faulty call.

    Returns:
        Structured error payload describing the expected failure.

    Raises:
        AssertionError: If the faulty call unexpectedly succeeds.
    """
    try:
        client.contracts.gap_analysis(contract_type="service_agreement")
    except QanuniError as error:
        return {
            "error_code": str(error.error_code),
            "message": str(error),
            "details": error.details,
        }
    raise AssertionError("The faulty acceptance scenario unexpectedly succeeded.")


SCENARIOS: tuple[AcceptanceScenarioSpec, ...] = (
    AcceptanceScenarioSpec(
        name="labor_basics",
        description="يشغل الأدوات الحتمية الأساسية الخاصة بالعمل.",
        runner=scenario_labor_basics,
    ),
    AcceptanceScenarioSpec(
        name="atomic_extraction",
        description="يشغل التصنيف والاستخراج الذري على عقد خدمات عربي نموذجي.",
        runner=scenario_atomic_extraction,
    ),
    AcceptanceScenarioSpec(
        name="contract_review",
        description="يشغل workflow مراجعة عقد كامل على مستند عربي نموذجي.",
        runner=scenario_contract_review,
    ),
    AcceptanceScenarioSpec(
        name="employment_review",
        description="يشغل workflow مراجعة عمالية على عقد عمل نموذجي.",
        runner=scenario_employment_review,
    ),
    AcceptanceScenarioSpec(
        name="privacy_review",
        description="يشغل workflow امتثال الخصوصية مع توليد مسودة علاجية.",
        runner=scenario_privacy_review,
    ),
    AcceptanceScenarioSpec(
        name="agent_notice",
        description="يشغل الـ agent من مراجعة العقد حتى تلخيص مسار المطالبة.",
        runner=scenario_agent_notice,
    ),
    AcceptanceScenarioSpec(
        name="cache_observability",
        description="يثبت عمل الكاش الانتقائي وسجل observability من منظور مستخدم.",
        runner=scenario_cache_and_observability,
    ),
    AcceptanceScenarioSpec(
        name="faulty_input",
        description="يعرض مثال خطأ متوقع مع error_code واضح.",
        runner=scenario_faulty_input,
    ),
)


def run_acceptance_scenarios(
    *,
    mode: Literal["mocked", "live"] = "mocked",
    scenario_names: Iterable[str] | None = None,
    working_dir: Path | None = None,
    cache_enabled: bool = True,
    observability_persist: bool = False,
) -> dict[str, Any]:
    """Run one or more acceptance scenarios and return a structured report.

    Args:
        mode: Whether to use the offline mocked provider or the live OpenAI provider.
        scenario_names: Optional subset of scenario names. Defaults to all scenarios.
        working_dir: Optional root directory for acceptance artifacts.
        cache_enabled: Whether selective caching should be enabled during the run.
        observability_persist: Whether observability events should be written to disk.

    Returns:
        Structured acceptance report with artifacts and scenario outputs.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
        ValueError: If one of the requested scenarios does not exist.
        OSError: If the selected working directory cannot be created.
    """
    selected_names = list(scenario_names or [item.name for item in SCENARIOS])
    selected_specs = [item for item in SCENARIOS if item.name in selected_names]
    if len(selected_specs) != len(selected_names):
        unknown = sorted(set(selected_names) - {item.name for item in SCENARIOS})
        raise ValueError(f"Unknown acceptance scenarios: {', '.join(unknown)}")

    artifact_paths = resolve_acceptance_artifact_paths(working_dir)
    client = build_acceptance_client(
        mode=mode,
        cache_enabled=cache_enabled,
        observability_persist=observability_persist,
        working_dir=artifact_paths.root_dir,
    )
    outputs: dict[str, Any] = {}
    spec: AcceptanceScenarioSpec
    for spec in selected_specs:
        outputs[spec.name] = spec.runner(client)

    return {
        "mode": mode,
        "artifact_paths": artifact_paths.as_json(),
        "scenarios": outputs,
    }


def _emit_json(payload: dict[str, Any]) -> None:
    """Write JSON to stdout with a UTF-8-safe fallback for Windows consoles.

    Args:
        payload: JSON-serializable payload to print.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
        TypeError: If the payload is not JSON-serializable.
    """
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(rendered.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        return
    sys.stdout.write(rendered)
    sys.stdout.write("\n")


def main() -> None:
    """Run the acceptance-pack CLI.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: If CLI parsing fails.
    """
    parser = argparse.ArgumentParser(description="Run Qanuni free-edition acceptance experiments.")
    parser.add_argument(
        "--mode",
        choices=("mocked", "live"),
        default="mocked",
        help="Whether to use the offline mocked provider or the live OpenAI provider.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Scenario name to run. Use multiple times. Omit to run all scenarios.",
    )
    parser.add_argument(
        "--working-dir",
        help="Optional directory for cache, observability, and MCP artifacts.",
    )
    parser.add_argument(
        "--persist-observability",
        action="store_true",
        help="Persist observability events to disk inside the acceptance working directory.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios and packaged sample documents.",
    )
    args = parser.parse_args()

    if args.list:
        _emit_json(
            {
                "scenarios": [
                    {"name": item.name, "description": item.description}
                    for item in SCENARIOS
                ],
                "sample_documents": [
                    {"name": name, "path": str(sample_document_path(name))}
                    for name in list_sample_documents()
                ],
            }
        )
        return

    report = run_acceptance_scenarios(
        mode=args.mode,
        scenario_names=args.scenario,
        working_dir=Path(args.working_dir) if args.working_dir else None,
        observability_persist=args.persist_observability,
    )
    _emit_json(report)


if __name__ == "__main__":
    main()
