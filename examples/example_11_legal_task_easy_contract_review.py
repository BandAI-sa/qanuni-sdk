"""Human-test one easy legal task for the agent: standalone contract review."""
# ruff: noqa: E402

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path
from _common import (
    build_context,
    emit_agent_plan,
    emit_agent_result_summary,
    emit_agent_state,
    emit_agent_workflow_breakdown,
    emit_document_excerpt,
    emit_environment,
    emit_legal_task_brief,
    emit_model,
    emit_observability,
    parse_standard_args,
)

ensure_project_root_on_path()

from qanuni.agent.models import AgentScenario
from qanuni.models.common import ToolRuntimeConfig


def main() -> None:
    """Run an easy contract-review legal task through the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run an easy legal task where the agent only reviews one service agreement."
    )
    context = build_context(title="Example 11 - Legal Task Easy Contract Review", args=args)

    documents = [
        {
            "name": "عقد خدمات بسيط",
            "text": emit_document_text(),
            "document_type": "service_agreement",
            "role": "primary",
        }
    ]
    request = {
        "goal": "راجع هذا العقد وحدد الثغرات الجوهرية والمخاطر الرئيسية واقترح تعديلات أولية.",
        "scenario_hint": AgentScenario.CONTRACT_REVIEW_ONLY,
        "documents": documents,
        "facts": {},
        "shared_runtime": ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            max_output_tokens=2600,
            api_retries=0,
        ),
    }

    emit_environment(context)
    emit_legal_task_brief(
        difficulty="easy",
        legal_question="هل عقد الخدمات الحالي منظم بشكل كافٍ أم توجد ثغرات تستدعي التعديل؟",
        scenario_hint=AgentScenario.CONTRACT_REVIEW_ONLY,
        documents=[
            {
                "name": "عقد خدمات بسيط",
                "document_type": "service_agreement",
                "source": "scenario_easy_contract_review_contract_ar.md",
            }
        ],
        facts={},
        what_to_watch=[
            "هل يختار الـ agent مسار workflow.contract_review فقط دون أدوات عشوائية.",
            "هل تظهر مراحل التصنيف والاستخراج وتحليل الثغرات وتقييم المخاطر داخل الـ workflow.",
            "هل تكون التوصيات النهائية مرتبطة بنتيجة المراجعة وليست نصًا عامًا فقط.",
        ],
        acceptance_criteria=[
            "الخطة تحتوي capability واحدة فقط وهي workflow.contract_review.",
            "النتيجة النهائية تتضمن ملخصًا ومخاطر أو ثغرات أو تعديلات مقترحة.",
            "حالة الـ agent تحتوي workflow state واحدة على الأقل مع step breakdown واضح.",
        ],
    )
    emit_document_excerpt("scenario_easy_contract_review_contract_ar.md")

    plan = context.client.agent.plan(request)
    result = context.client.agent.run(request)

    emit_agent_plan(plan)
    emit_agent_result_summary(result)
    emit_model("Agent run result payload", result)
    emit_agent_workflow_breakdown(result.state)
    emit_agent_state(result.state)
    emit_observability(context)


def emit_document_text() -> str:
    """Load the packaged document text for the easy contract-review task.

    Args:
        None.

    Returns:
        The packaged Arabic service-agreement text.

    Raises:
        FileNotFoundError: If the packaged sample document cannot be found.
    """
    from _common import load_sample_document

    return load_sample_document("scenario_easy_contract_review_contract_ar.md")


if __name__ == "__main__":
    main()
