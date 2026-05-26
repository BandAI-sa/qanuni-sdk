"""Saudi probation period legality checker."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.jurisdictions.sa_labor import max_probation_days
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.labor import ProbationCheckInput, ProbationCheckResult


class ProbationCheckTool(BaseTool[ProbationCheckInput, ProbationCheckResult]):
    """Validate Saudi probation-period legality deterministically."""

    TOOL_ID = "labor.probation_check"
    INPUT_MODEL = ProbationCheckInput
    OUTPUT_MODEL = ProbationCheckResult
    LEGAL_REFERENCE_FILE = "sa/labor/employment_baseline.yaml"

    def _run(
        self,
        input_data: ProbationCheckInput,
        runtime: ToolRuntimeConfig | None,
    ) -> ProbationCheckResult:
        """Check probation legality synchronously."""
        del runtime
        allowed_days = max_probation_days(written_extension=input_data.written_extension)
        is_legal = input_data.probation_duration_days <= allowed_days

        violations: list[str] = []
        if not is_legal:
            violations.append(
                "مدة التجربة تتجاوز الحد المسموح به وهو "
                f"{allowed_days} يوما في الحالة المعروضة."
            )
        if input_data.contract_text_snippet and (
            "اختبار" not in input_data.contract_text_snippet
            and "تجربة" not in input_data.contract_text_snippet
        ):
            violations.append(
                "المقتطف العقدي المقدم قد لا ينص صراحة على بند فترة التجربة."
            )

        explanation = (
            "يشترط نظام العمل السعودي أن تُذكر فترة التجربة صراحة في العقد. والحد الأساسي هو "
            "90 يوما، ويجوز رفع الإجمالي إلى 180 يوما إذا وُجد تمديد كتابي صحيح."
        )

        return ProbationCheckResult(
            is_legal=is_legal,
            max_allowed_days=allowed_days,
            violations=violations,
            employee_rights_during_probation=[
                "ينبغي أن يكون بند فترة التجربة منصوصا عليه صراحة في العقد.",
                "من المهم أن يكون العامل على بينة مما إذا كان حق الإنهاء متبادلا أو من طرف واحد.",
            ],
            employer_rights_during_probation=[
                "يجوز لصاحب العمل الإنهاء خلال فترة التجربة وفقا لما يجيزه العقد والنظام.",
                "يشترط وجود تمديد كتابي للفترات التي تتجاوز الحد الأساسي البالغ 90 يوما.",
            ],
            legal_explanation=explanation,
            model_used="deterministic",
            tokens_used=0,
        )
