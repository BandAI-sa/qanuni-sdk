"""Human-test a medium legal task for the agent: employment rights review."""
# ruff: noqa: E402, E501

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
    load_sample_document,
    parse_standard_args,
)

ensure_project_root_on_path()

from qanuni.agent.models import AgentScenario
from qanuni.models.common import ToolRuntimeConfig


def main() -> None:
    """Run an employment-rights legal task through the agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
    """
    args = parse_standard_args(
        "Run a medium legal task where the agent assesses employment risks and financial entitlements."
    )
    context = build_context(
        title="Example 13 - Legal Task Medium Employment Rights",
        args=args,
    )

    request = {
        "goal": "أريد تقييم وضعي العمالي من حيث فترة التجربة ومكافأة نهاية الخدمة والمخاطر النظامية.",
        "scenario_hint": AgentScenario.EMPLOYMENT_RIGHTS_REVIEW,
        "documents": [
            {
                "name": "عقد عمل",
                "text": load_sample_document("scenario_medium_employment_contract_ar.md"),
                "document_type": "employment_contract",
                "role": "primary",
            }
        ],
        "facts": {
            "contract_type": "indefinite",
            "probation_days": 120,
            "extension_in_writing": False,
            "monthly_salary": 9000,
            "years_of_service": 3.5,
            "termination_reason": "termination_by_employer",
        },
        "shared_runtime": ToolRuntimeConfig(
            model="gpt-5-mini",
            verbosity="high",
            max_output_tokens=2600,
            api_retries=0,
        ),
    }

    emit_environment(context)
    emit_legal_task_brief(
        difficulty="medium",
        legal_question="هل الوضع العمالي الحالي يتضمن مخالفة في فترة التجربة وما الحقوق المالية المتوقعة؟",
        scenario_hint=AgentScenario.EMPLOYMENT_RIGHTS_REVIEW,
        documents=[
            {
                "name": "عقد عمل",
                "document_type": "employment_contract",
                "source": "scenario_medium_employment_contract_ar.md",
            }
        ],
        facts=request["facts"],
        what_to_watch=[
            "هل يستخرج الـ workflow البيانات الأساسية من عقد العمل قبل تطبيق الفحوص النظامية.",
            "هل يظهر في النتيجة أثر كل من probation_check و end_of_service داخل صورة واحدة متماسكة.",
            "هل يترجم الـ agent النتائج إلى جواب عربي مفهوم لصاحب المشكلة.",
        ],
        acceptance_criteria=[
            "الخطة تحتوي workflow.employment_review.",
            "النتيجة النهائية تتضمن probation_status أو ما يعادله، ومبلغ نهاية خدمة أو تفسيرًا لعدم احتسابه.",
            "حالة الـ workflow تعرض مخاطر عمالية وإجراءات متابعة مقترحة.",
        ],
    )
    emit_document_excerpt("scenario_medium_employment_contract_ar.md")

    plan = context.client.agent.plan(request)
    result = context.client.agent.run(request)

    emit_agent_plan(plan)
    emit_agent_result_summary(result)
    emit_model("Agent run result payload", result)
    emit_agent_workflow_breakdown(result.state)
    emit_agent_state(result.state)
    emit_observability(context)


if __name__ == "__main__":
    main()
