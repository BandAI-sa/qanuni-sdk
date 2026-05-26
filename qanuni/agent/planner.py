"""Planner for deterministic multi-step legal-agent scenarios."""

from __future__ import annotations

from typing import Literal

from qanuni.agent.guardrails import AgentGuardrails
from qanuni.agent.metadata import AgentCapabilityMetadata, AgentCapabilityRegistry
from qanuni.agent.models import AgentPlan, AgentPlanStep, AgentRunInput, AgentScenario
from qanuni.agent.payloads import AgentCapabilityPayloadBuilder


class AgentPlanner:
    """Select approved capabilities and order them into a deterministic plan.

    Args:
        registry: Capability registry exposed to the planner.
        payload_builder: Shared payload builder used to preview runtime needs.
        guardrails: Guardrail engine used to detect missing inputs early.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        registry: AgentCapabilityRegistry,
        payload_builder: AgentCapabilityPayloadBuilder,
        guardrails: AgentGuardrails,
    ) -> None:
        """Store the collaborating services used during planning.

        Args:
            registry: Capability registry exposed to the planner.
            payload_builder: Shared payload builder used to preview runtime needs.
            guardrails: Guardrail engine used to detect missing inputs early.

        Returns:
            None.

        Raises:
            None.
        """
        self._registry = registry
        self._payload_builder = payload_builder
        self._guardrails = guardrails

    def plan(self, request: AgentRunInput) -> AgentPlan:
        """Build a deterministic capability plan for the current request.

        Args:
            request: Normalized agent run input from the user.

        Returns:
            A structured deterministic plan for execution.

        Raises:
            None.
        """
        scenario = self._select_scenario(request)
        if scenario == AgentScenario.UNKNOWN:
            return AgentPlan(
                scenario=scenario,
                status_hint="blocked",
                plan_summary="تعذر على المخطط تحديد مسار قانوني آمن من المدخلات الحالية.",
                planning_notes=[
                    "يلزم هدف أكثر تحديدًا أو مستند قانوني واضح حتى يختار الـ agent workflow مناسبًا."
                ],
            )

        capability_ids = self._scenario_capability_ids(scenario)
        steps: list[AgentPlanStep] = []
        planning_notes = [
            "المخطط يختار فقط workflows معتمدة ومقيدة بالـ metadata ولا يستدعي أدوات عشوائية."
        ]
        plan_status: Literal["ready", "needs_more_information", "blocked"] = "ready"

        capability_id: str
        for index, capability_id in enumerate(capability_ids, start=1):
            capability = self._registry.get_capability(capability_id)
            preview_payload = self._payload_builder.build_payload(capability, request)
            missing_inputs = self._guardrails.missing_inputs_for_payload(
                capability,
                preview_payload,
            )
            status_hint: Literal["ready", "needs_more_information"] = (
                "ready" if not missing_inputs else "needs_more_information"
            )
            if missing_inputs and plan_status == "ready":
                plan_status = "needs_more_information"
            steps.append(
                AgentPlanStep(
                    step_id=f"agent_step_{index}",
                    capability_id=capability.capability_id,
                    title=capability.title,
                    reason=self._step_reason(scenario, capability),
                    required_inputs=list(capability.required_inputs),
                    missing_inputs=missing_inputs,
                    produced_entities=list(capability.produced_entities),
                    risk_domain=capability.risk_domain,
                    cost_hint=capability.cost_hint,
                    latency_hint=capability.latency_hint,
                    recommended_predecessors=list(capability.recommended_predecessors),
                    status_hint=status_hint,
                )
            )

        planning_notes.extend(self._scenario_notes(scenario))
        return AgentPlan(
            scenario=scenario,
            status_hint=plan_status,
            plan_summary=self._plan_summary(scenario, steps),
            steps=steps,
            planning_notes=planning_notes,
        )

    def _select_scenario(self, request: AgentRunInput) -> AgentScenario:
        if request.scenario_hint is not None:
            return request.scenario_hint

        goal = request.goal.casefold()
        if self._contains_any(goal, ["مطالبة", "انذار", "نزاع", "claim", "notice", "demand"]):
            return AgentScenario.CONTRACT_DISPUTE_NOTICE
        if self._contains_any(
            goal,
            ["عمل", "موظف", "فصل", "نهاية الخدمة", "employment", "labor", "probation"],
        ):
            return AgentScenario.EMPLOYMENT_RIGHTS_REVIEW
        if self._contains_any(goal, ["خصوصية", "بيانات", "pdpl", "privacy"]):
            return AgentScenario.PRIVACY_REMEDIATION
        if self._contains_any(goal, ["سياسة", "policy", "وصف وظيفي", "job description"]):
            return AgentScenario.POLICY_CREATION_REVIEW
        if self._contains_any(goal, ["عقد", "اتفاقية", "contract", "agreement"]):
            return AgentScenario.CONTRACT_REVIEW_ONLY
        return AgentScenario.UNKNOWN

    def _scenario_capability_ids(self, scenario: AgentScenario) -> list[str]:
        if scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE:
            return ["workflow.contract_review", "workflow.pre_litigation_notice"]
        if scenario == AgentScenario.EMPLOYMENT_RIGHTS_REVIEW:
            return ["workflow.employment_review"]
        if scenario == AgentScenario.PRIVACY_REMEDIATION:
            return ["workflow.privacy_compliance_review"]
        if scenario == AgentScenario.POLICY_CREATION_REVIEW:
            return ["workflow.policy_generation_review"]
        if scenario == AgentScenario.CONTRACT_REVIEW_ONLY:
            return ["workflow.contract_review"]
        return []

    def _step_reason(
        self,
        scenario: AgentScenario,
        capability: AgentCapabilityMetadata,
    ) -> str:
        if scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE:
            if capability.capability_id == "workflow.contract_review":
                return "نبدأ بتشخيص العقد واستخراج المخاطر قبل صياغة أي مطالبة قانونية."
            return "بعد فهم المخاطر والالتزامات يمكن الانتقال إلى خطاب المطالبة قبل النزاع."
        if scenario == AgentScenario.EMPLOYMENT_RIGHTS_REVIEW:
            return "هذا المسار يجمع تحليل عقد العمل مع الفحوصات النظامية والحقوق المالية."
        if scenario == AgentScenario.PRIVACY_REMEDIATION:
            return "هذا المسار يفحص الامتثال الحالي ثم يرتب أولويات المعالجة وقد يولد مسودة علاجية."
        if scenario == AgentScenario.POLICY_CREATION_REVIEW:
            return "هذا المسار يولد المستند المطلوب ثم يراجعه بخطوات إضافية بدل الاكتفاء بالتوليد."
        return "هذا المسار هو الأنسب لمراجعة العقد بصورة متكاملة."

    def _plan_summary(self, scenario: AgentScenario, steps: list[AgentPlanStep]) -> str:
        if scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE:
            return (
                f"الخطة ستنفذ {len(steps)} مرحلتين: مراجعة العقد ثم تجهيز "
                "مسار المطالبة قبل النزاع."
            )
        if scenario == AgentScenario.EMPLOYMENT_RIGHTS_REVIEW:
            return "الخطة ستنفذ مراجعة عمالية واحدة تجمع المستند والفحوصات النظامية."
        if scenario == AgentScenario.PRIVACY_REMEDIATION:
            return "الخطة ستنفذ مراجعة امتثال خصوصية كاملة مع أولويات علاجية واضحة."
        if scenario == AgentScenario.POLICY_CREATION_REVIEW:
            return "الخطة ستنفذ مسار توليد ومراجعة مستند سياساتي أو تشغيلي."
        return f"الخطة ستنفذ {len(steps)} workflow لمراجعة العقد بصورة مركبة."

    def _scenario_notes(self, scenario: AgentScenario) -> list[str]:
        if scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE:
            return [
                "تم فرض predecessor صريح بحيث لا يبدأ خطاب المطالبة قبل مراجعة العقد.",
                "سيتم التوقف تلقائيًا إذا غابت بيانات المطالبة الجوهرية."
            ]
        if scenario == AgentScenario.PRIVACY_REMEDIATION:
            return [
                "سيتم طلب معلومات إضافية فقط إذا طُلب توليد مسودة علاجية بدون بيانات شركة أو خدمة."
            ]
        return []

    def _contains_any(self, haystack: str, needles: list[str]) -> bool:
        needle: str
        for needle in needles:
            if needle.casefold() in haystack:
                return True
        return False
