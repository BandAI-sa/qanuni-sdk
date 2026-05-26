"""Saudi end-of-service benefit calculator."""

from __future__ import annotations

from qanuni.core.base_tool import BaseTool
from qanuni.jurisdictions.sa_labor import (
    ARTICLE_84_REFERENCE,
    apply_resignation_discount,
    calculate_base_end_of_service,
)
from qanuni.models.common import CalculationStep, ToolRuntimeConfig
from qanuni.models.labor import EndOfServiceInput, EndOfServiceResult


class EndOfServiceTool(BaseTool[EndOfServiceInput, EndOfServiceResult]):
    """Calculate Saudi end-of-service benefits deterministically."""

    TOOL_ID = "labor.end_of_service"
    INPUT_MODEL = EndOfServiceInput
    OUTPUT_MODEL = EndOfServiceResult
    LEGAL_REFERENCE_FILE = "sa/labor/employment_baseline.yaml"

    def _run(
        self,
        input_data: EndOfServiceInput,
        runtime: ToolRuntimeConfig | None,
    ) -> EndOfServiceResult:
        """Calculate end-of-service benefits synchronously."""
        del runtime
        base_award = calculate_base_end_of_service(
            monthly_salary=input_data.monthly_salary,
            years_of_service=input_data.years_of_service,
        )
        adjusted_award = base_award
        breakdown = [
            CalculationStep(
                description="المكافأة الأساسية قبل أي تخفيض مرتبط بالاستقالة",
                amount=round(base_award, 2),
            )
        ]

        if input_data.termination_reason == "resignation":
            adjusted_award = apply_resignation_discount(base_award, input_data.years_of_service)
            breakdown.append(
                CalculationStep(
                    description="المكافأة بعد تطبيق نسبة الاستحقاق في حالة الاستقالة",
                    amount=round(adjusted_award, 2),
                )
            )

        explanation = (
            "تُحسب المكافأة على أساس الأجر الشهري الأخير: نصف شهر عن كل سنة من السنوات الخمس "
            "الأولى، وشهر كامل عن كل سنة تالية. وفي حالات الاستقالة قد تُطبق نسب استحقاق مختلفة "
            "بحسب مدة الخدمة."
        )

        return EndOfServiceResult(
            total_amount=round(adjusted_award, 2),
            calculation_breakdown=breakdown,
            legal_explanation=explanation,
            applicable_articles=[ARTICLE_84_REFERENCE],
            additional_entitlements=[
                "قد تحتاج أرصدة الإجازات غير المستخدمة إلى تسوية مستقلة.",
                "قد تتطلب العمولات أو المكافآت مراجعة خاصة وفق العقد أو السياسة الداخلية.",
            ],
        )
