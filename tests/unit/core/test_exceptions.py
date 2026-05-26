from __future__ import annotations

from qanuni.core.exceptions import (
    ErrorCode,
    QanuniAPIError,
    QanuniConfigError,
    QanuniLicenseError,
    QanuniValidationError,
)


def test_config_error_exposes_stable_error_code() -> None:
    """Configuration errors should expose a stable machine-readable error code."""
    error = QanuniConfigError(
        "Missing key",
        error_code=ErrorCode.CONFIG_API_KEY_MISSING,
        details={"tool_id": "contracts.gap_analysis"},
    )
    payload = error.to_dict()
    assert payload["error_code"] == ErrorCode.CONFIG_API_KEY_MISSING
    assert payload["details"]["tool_id"] == "contracts.gap_analysis"


def test_api_error_carries_status_code_in_details() -> None:
    """Provider errors should include status-code context when available."""
    error = QanuniAPIError("Upstream failed", status_code=429)
    assert error.status_code == 429
    assert error.details["status_code"] == 429


def test_validation_error_string_includes_error_code() -> None:
    """Rendered validation errors should surface the stable error code prefix."""
    error = QanuniValidationError(
        "Invalid input",
        error_code=ErrorCode.VALIDATION_INPUT_TYPE,
    )
    assert str(error).startswith(f"[{ErrorCode.VALIDATION_INPUT_TYPE}]")


def test_license_error_exposes_machine_readable_code() -> None:
    """Licensing errors should preserve their machine-readable error code."""
    error = QanuniLicenseError(
        "Missing license",
        error_code=ErrorCode.LICENSE_REQUIRED,
        details={"tool_id": "contracts.risk_score"},
    )
    assert error.to_dict()["error_code"] == ErrorCode.LICENSE_REQUIRED
