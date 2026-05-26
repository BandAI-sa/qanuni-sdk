"""Arabic answer synthesis for deterministic legal-agent runs."""

from __future__ import annotations

from qanuni.agent.guardrails import AgentGuardrails
from qanuni.agent.models import (
    AgentPlan,
    AgentRunInput,
    AgentRunStatus,
    AgentScenario,
)
from qanuni.agent.state_store import AgentStateStore


class AgentAnswerSynthesizer:
    """Compose the final Arabic response after planning and execution.

    Args:
        guardrails: Guardrail engine used to phrase follow-up questions consistently.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, guardrails: AgentGuardrails) -> None:
        """Store the guardrail engine used for follow-up phrasing.

        Args:
            guardrails: Guardrail engine used to phrase follow-up questions consistently.

        Returns:
            None.

        Raises:
            None.
        """
        self._guardrails = guardrails

    def synthesize(
        self,
        *,
        request: AgentRunInput,
        plan: AgentPlan,
        state_store: AgentStateStore,
        status: AgentRunStatus,
    ) -> tuple[str, str | None]:
        """Synthesize the final answer text and optional follow-up question.

        Args:
            request: Normalized agent run input from the user.
            plan: Deterministic plan produced by the planner.
            state_store: Populated runtime state store after execution.
            status: Terminal runtime status reached by the executor.

        Returns:
            A tuple containing the Arabic answer text and an optional follow-up question.

        Raises:
            None.
        """
        if status == AgentRunStatus.COMPLETED:
            return self._completed_answer(plan, state_store), None
        if status == AgentRunStatus.NEEDS_MORE_INFORMATION:
            missing = state_store.build().missing_inputs
            question = self._guardrails.next_question_for_missing_inputs(missing)
            return self._needs_information_answer(state_store, question), question
        return self._blocked_answer(request, state_store), None

    def _completed_answer(
        self,
        plan: AgentPlan,
        state_store: AgentStateStore,
    ) -> str:
        scenario = plan.scenario
        if scenario == AgentScenario.CONTRACT_DISPUTE_NOTICE:
            contract_result = state_store.result_for("workflow.contract_review")
            notice_result = state_store.result_for("workflow.pre_litigation_notice")
            contract_summary = str(getattr(contract_result, "executive_summary", ""))
            notice_text = str(getattr(notice_result, "demand_letter_text", ""))
            negotiation_points = list(getattr(notice_result, "negotiation_points", []))
            return (
                "أنهيت مسار النزاع التعاقدي كاملًا. "
                f"{contract_summary} "
                f"كما تم تجهيز خطاب مطالبة عربي جاهز مبدئيًا، وأبرز نقاط التفاوض هي: "
                f"{'، '.join(negotiation_points[:3]) or 'لم تُولد نقاط تفاوض إضافية'}."
                f"\n\nنص الخطاب المولد:\n{notice_text}"
            )
        if scenario == AgentScenario.EMPLOYMENT_RIGHTS_REVIEW:
            employment_result = state_store.result_for("workflow.employment_review")
            employment_summary = str(getattr(employment_result, "executive_summary", ""))
            risks = list(getattr(employment_result, "employment_risks", []))
            follow_ups = list(getattr(employment_result, "recommended_follow_ups", []))
            return (
                "أنهيت المراجعة العمالية كاملة. "
                f"{employment_summary} "
                f"أبرز المخاطر: {'، '.join(risks[:3]) or 'لا توجد مخاطر بارزة'}."
                f" وأهم المتابعات: {'، '.join(follow_ups[:3]) or 'لا توجد متابعات إضافية حالياً'}."
            )
        if scenario == AgentScenario.PRIVACY_REMEDIATION:
            privacy_result = state_store.result_for("workflow.privacy_compliance_review")
            privacy_summary = str(getattr(privacy_result, "executive_summary", ""))
            remediation = list(getattr(privacy_result, "remediation_priorities", []))
            return (
                "أنهيت مراجعة الخصوصية العلاجية. "
                f"{privacy_summary} "
                "وأولويات المعالجة الحالية هي: "
                f"{'، '.join(remediation[:4]) or 'لا توجد أولويات إضافية'}."
            )
        if scenario == AgentScenario.POLICY_CREATION_REVIEW:
            policy_result = state_store.result_for("workflow.policy_generation_review")
            policy_summary = str(getattr(policy_result, "executive_summary", ""))
            review_notes = list(getattr(policy_result, "review_notes", []))
            return (
                "أنهيت مسار التوليد والمراجعة. "
                f"{policy_summary} "
                f"وأبرز الملاحظات هي: {'، '.join(review_notes[:4]) or 'لا توجد ملاحظات إضافية'}."
            )
        contract_result = state_store.result_for("workflow.contract_review")
        contract_summary = str(getattr(contract_result, "executive_summary", ""))
        recommendations = list(getattr(contract_result, "amendment_recommendations", []))
        return (
            "أنهيت مراجعة العقد بالكامل. "
            f"{contract_summary} "
            f"وأهم التوصيات: {'، '.join(recommendations[:4]) or 'لا توجد توصيات إضافية'}."
        )

    def _needs_information_answer(
        self,
        state_store: AgentStateStore,
        question: str,
    ) -> str:
        completed = state_store.completed_capabilities()
        if not completed:
            return (
                "توقفت قبل بدء التنفيذ الكامل لأن بعض البيانات الجوهرية غير متاحة بعد. "
                + question
            )
        return (
            "أنجزت الجزء القابل للتنفيذ من المهمة، لكنني توقفت قبل الوصول إلى نتيجة نهائية كاملة. "
            f"المسارات المكتملة حتى الآن: {', '.join(completed)}. "
            + question
        )

    def _blocked_answer(
        self,
        request: AgentRunInput,
        state_store: AgentStateStore,
    ) -> str:
        guardrail_messages = state_store.build().guardrail_messages
        if guardrail_messages:
            return (
                "توقفت طبقة الـ agent لأن guardrails منعت استنتاجًا غير مدعوم. "
                + " ".join(guardrail_messages)
            )
        return (
            "تعذر إكمال الطلب الحالي بشكل آمن لأن الخطة لم تتمكن من اختيار مسار قانوني "
            f"واضح من الهدف التالي: {request.goal}"
        )
