"""Guardrails for deterministic planning and execution in the legal agent."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from qanuni.agent.metadata import AgentCapabilityMetadata


class AgentGuardrails:
    """Centralize validation and stopping logic for the legal-agent runtime.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    def missing_inputs_for_payload(
        self,
        capability: AgentCapabilityMetadata,
        payload: dict[str, Any],
    ) -> list[str]:
        """Validate one payload and return the missing inputs that block execution.

        Args:
            capability: Capability metadata selected by the planner or executor.
            payload: Workflow payload prepared from the current request state.

        Returns:
            A deduplicated list of missing logical inputs.

        Raises:
            None.
        """
        try:
            capability.input_model.model_validate(payload)
        except ValidationError as exc:
            return self._extract_missing_inputs(exc, payload)
        return []

    def validate_predecessors(
        self,
        capability: AgentCapabilityMetadata,
        completed_capabilities: list[str],
    ) -> list[str]:
        """Check whether all recommended predecessors have already completed.

        Args:
            capability: Capability metadata selected by the planner or executor.
            completed_capabilities: Ordered list of completed capability IDs.

        Returns:
            A list of missing predecessor capability IDs.

        Raises:
            None.
        """
        return [
            predecessor
            for predecessor in capability.recommended_predecessors
            if predecessor not in completed_capabilities
        ]

    def validate_result(
        self,
        capability: AgentCapabilityMetadata,
        result: Any,
    ) -> list[str]:
        """Ensure one workflow result contains the minimum supported output surface.

        Args:
            capability: Capability metadata selected by the planner or executor.
            result: Workflow result object returned by the SDK.

        Returns:
            A list of guardrail messages describing unsupported result gaps.

        Raises:
            None.
        """
        messages: list[str] = []
        requirement: str
        for requirement in capability.completion_requirements:
            value = self._resolve_path_value(result, requirement)
            if not value:
                messages.append(
                    f"Capability '{capability.capability_id}' did not populate '{requirement}'."
                )
        return messages

    def next_question_for_missing_inputs(self, missing_inputs: list[str]) -> str:
        """Translate missing runtime inputs into one Arabic follow-up question.

        Args:
            missing_inputs: Canonical missing input field names gathered by guardrails.

        Returns:
            A single Arabic follow-up question suitable for the user.

        Raises:
            None.
        """
        labels = [self._input_label(field_name) for field_name in missing_inputs]
        unique_labels: list[str] = []
        label: str
        for label in labels:
            if label not in unique_labels:
                unique_labels.append(label)
        joined = "، ".join(unique_labels)
        return f"لإكمال هذه المهمة أحتاج إلى: {joined}."

    def _extract_missing_inputs(
        self,
        error: ValidationError,
        payload: dict[str, Any],
    ) -> list[str]:
        missing_inputs: list[str] = []
        details: list[Any] = error.errors(include_url=False)
        detail: Any
        for detail in details:
            error_type = str(detail.get("type", ""))
            location = detail.get("loc", ())
            if error_type == "missing" and location:
                missing_inputs.append(str(location[0]))
            if location and payload.get(str(location[0])) is None:
                missing_inputs.append(str(location[0]))
            message = str(detail.get("msg", ""))
            if "Provide either document_text or document_file." in message:
                missing_inputs.extend(["document_text", "document_file"])
            if (
                "Provide company_name and service_type when generate_policy_draft is enabled."
                in message
            ):
                missing_inputs.extend(["company_name", "service_type"])
            if "Provide policy_type, company_name, and industry for hr_policy." in message:
                missing_inputs.extend(["policy_type", "company_name", "industry"])
            if "Provide employee_count for hr_policy." in message:
                missing_inputs.append("employee_count")
            if "Missing required job-description fields:" in message:
                tail = message.split(":", maxsplit=1)[-1]
                field_name: str
                for field_name in tail.split(","):
                    normalized = field_name.strip().strip(".")
                    if normalized:
                        missing_inputs.append(normalized)
            if "Provide required_experience_years for job_description." in message:
                missing_inputs.append("required_experience_years")
            if "Provide company_name and service_type for privacy_policy." in message:
                missing_inputs.extend(["company_name", "service_type"])
        return self._unique_strings(missing_inputs)

    def _resolve_path_value(self, payload: Any, path: str) -> Any:
        value = payload
        segment: str
        for segment in path.split("."):
            value = getattr(value, segment, None)
            if value is None:
                return None
        return value

    def _input_label(self, field_name: str) -> str:
        labels: dict[str, str] = {
            "claim_type": "نوع المطالبة",
            "company_name": "اسم الشركة",
            "deadline_days": "عدد أيام المهلة",
            "document_file": "ملف المستند",
            "document_text": "نص المستند",
            "employee_count": "عدد الموظفين",
            "incident_description": "وصف الواقعة",
            "industry": "القطاع",
            "policy_kind": "نوع السياسة المطلوبة",
            "policy_type": "نوع سياسة الموارد البشرية",
            "recipient_name": "اسم الجهة الموجه إليها",
            "required_education": "المؤهل المطلوب",
            "required_experience_years": "سنوات الخبرة المطلوبة",
            "sender_name": "اسم الجهة المرسلة",
            "service_type": "نوع الخدمة",
            "threat_of_action": "صياغة الإجراء القانوني المزمع",
            "job_title": "المسمى الوظيفي",
            "department": "الإدارة",
        }
        return labels.get(field_name, field_name)

    def _unique_strings(self, values: list[str]) -> list[str]:
        unique_values: list[str] = []
        value: str
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in unique_values:
                unique_values.append(normalized)
        return unique_values
