"""Typed exception hierarchy for the Qanuni SDK."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Enumerates stable SDK error codes for logging and client handling."""

    CONFIG_INVALID = "QANUNI_CONFIG_INVALID"
    CONFIG_API_KEY_MISSING = "QANUNI_CONFIG_API_KEY_MISSING"
    VALIDATION_FAILED = "QANUNI_VALIDATION_FAILED"
    VALIDATION_INPUT_CONFLICT = "QANUNI_VALIDATION_INPUT_CONFLICT"
    VALIDATION_INPUT_TYPE = "QANUNI_VALIDATION_INPUT_TYPE"
    VALIDATION_DOCUMENT_SOURCE_MISSING = "QANUNI_VALIDATION_DOCUMENT_SOURCE_MISSING"
    VALIDATION_DOCUMENT_PATH_MISSING = "QANUNI_VALIDATION_DOCUMENT_PATH_MISSING"
    TIER_RESTRICTION = "QANUNI_TIER_RESTRICTION"
    ASYNC_PRO_REQUIRED = "QANUNI_ASYNC_PRO_REQUIRED"
    LICENSE_REQUIRED = "QANUNI_LICENSE_REQUIRED"
    LICENSE_INVALID = "QANUNI_LICENSE_INVALID"
    LICENSE_INVALID_FORMAT = "QANUNI_LICENSE_INVALID_FORMAT"
    LICENSE_INVALID_SIGNATURE = "QANUNI_LICENSE_INVALID_SIGNATURE"
    LICENSE_INVALID_STATUS = "QANUNI_LICENSE_INVALID_STATUS"
    LICENSE_INVALID_RESPONSE = "QANUNI_LICENSE_INVALID_RESPONSE"
    LICENSE_EXPIRED = "QANUNI_LICENSE_EXPIRED"
    LICENSE_REVOKED = "QANUNI_LICENSE_REVOKED"
    LICENSE_NOT_YET_VALID = "QANUNI_LICENSE_NOT_YET_VALID"
    LICENSE_PUBLIC_KEY_MISSING = "QANUNI_LICENSE_PUBLIC_KEY_MISSING"
    LICENSE_CACHE_INVALID = "QANUNI_LICENSE_CACHE_INVALID"
    LICENSE_STORAGE_FAILURE = "QANUNI_LICENSE_STORAGE_FAILURE"
    LICENSE_SDK_VERSION_UNSUPPORTED = "QANUNI_LICENSE_SDK_VERSION_UNSUPPORTED"
    LICENSE_ACTIVATION_LIMIT_REACHED = "QANUNI_LICENSE_ACTIVATION_LIMIT_REACHED"
    LICENSE_REFRESH_FAILED = "QANUNI_LICENSE_REFRESH_FAILED"
    LICENSE_ACTIVATION_KEY_INVALID = "QANUNI_LICENSE_ACTIVATION_KEY_INVALID"
    LICENSE_ACTIVATION_KEY_EXISTS = "QANUNI_LICENSE_ACTIVATION_KEY_EXISTS"
    LICENSE_ISSUER_KEY_MISSING = "QANUNI_LICENSE_ISSUER_KEY_MISSING"
    LICENSE_ISSUER_KEY_EXISTS = "QANUNI_LICENSE_ISSUER_KEY_EXISTS"
    LICENSE_MACHINE_FINGERPRINT_REQUIRED = "QANUNI_LICENSE_MACHINE_FINGERPRINT_REQUIRED"
    LICENSE_RECORD_NOT_FOUND = "QANUNI_LICENSE_RECORD_NOT_FOUND"
    LICENSE_RECORD_ALREADY_EXISTS = "QANUNI_LICENSE_RECORD_ALREADY_EXISTS"
    TOOL_NOT_LICENSED = "QANUNI_TOOL_NOT_LICENSED"
    FEATURE_NOT_LICENSED = "QANUNI_FEATURE_NOT_LICENSED"
    PROMPT_SCHEMA_INVALID = "QANUNI_PROMPT_SCHEMA_INVALID"
    PROMPT_TOO_SHORT = "QANUNI_PROMPT_TOO_SHORT"
    PROMPT_FILE_MISSING = "QANUNI_PROMPT_FILE_MISSING"
    LEGAL_REFERENCE_REQUIRED = "QANUNI_LEGAL_REFERENCE_REQUIRED"
    LEGAL_REFERENCE_INVALID = "QANUNI_LEGAL_REFERENCE_INVALID"
    LEGAL_REFERENCE_FILE_MISSING = "QANUNI_LEGAL_REFERENCE_FILE_MISSING"
    API_PROVIDER_FAILURE = "QANUNI_API_PROVIDER_FAILURE"
    API_RESPONSE_INCOMPLETE = "QANUNI_API_RESPONSE_INCOMPLETE"
    API_RESPONSE_REFUSAL = "QANUNI_API_RESPONSE_REFUSAL"
    API_EMPTY_PARSED_OUTPUT = "QANUNI_API_EMPTY_PARSED_OUTPUT"
    API_OUTPUT_TEXT_MISSING = "QANUNI_API_OUTPUT_TEXT_MISSING"
    MCP_AUTH_REQUIRED = "QANUNI_MCP_AUTH_REQUIRED"
    MCP_AUTH_INVALID = "QANUNI_MCP_AUTH_INVALID"
    MCP_RATE_LIMITED = "QANUNI_MCP_RATE_LIMITED"
    MCP_RUN_NOT_FOUND = "QANUNI_MCP_RUN_NOT_FOUND"
    MCP_RESOURCE_NOT_FOUND = "QANUNI_MCP_RESOURCE_NOT_FOUND"
    MCP_SURFACE_NOT_FOUND = "QANUNI_MCP_SURFACE_NOT_FOUND"
    PARSE_INVALID_JSON = "QANUNI_PARSE_INVALID_JSON"
    OUTPUT_SCHEMA_MISMATCH = "QANUNI_OUTPUT_SCHEMA_MISMATCH"
    FEATURE_NOT_READY = "QANUNI_FEATURE_NOT_READY"


class QanuniError(Exception):
    """Base exception for all SDK errors.

    Args:
        message: Human-readable description of the failure.
        error_code: Stable machine-readable error code.
        details: Optional structured context about the failure.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the base error with machine-readable metadata.

        Args:
            message: Human-readable description of the failure.
            error_code: Stable machine-readable error code.
            details: Optional structured context about the failure.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message)
        self.error_code: ErrorCode = error_code
        self.details: dict[str, Any] = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error into a structured dictionary.

        Args:
            None.

        Returns:
            A dictionary containing the message, error code, and structured details.

        Raises:
            None.
        """
        return {
            "message": str(self.args[0]),
            "error_code": self.error_code,
            "details": self.details,
        }

    def __str__(self) -> str:
        """Return a display-friendly error string.

        Args:
            None.

        Returns:
            A string that prefixes the human message with the stable error code.

        Raises:
            None.
        """
        return f"[{self.error_code}] {self.args[0]}"


class QanuniConfigError(QanuniError):
    """Raised when configuration is missing or invalid.

    Args:
        message: Human-readable description of the configuration problem.
        error_code: Optional override for the default configuration error code.
        details: Optional structured context about the configuration failure.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.CONFIG_INVALID,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a configuration-related SDK error.

        Args:
            message: Human-readable description of the configuration problem.
            error_code: Optional override for the default configuration error code.
            details: Optional structured context about the configuration failure.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message, error_code=error_code, details=details)


class QanuniTierError(QanuniError):
    """Raised when a tier-restricted feature is accessed without entitlement.

    Args:
        message: Human-readable description of the entitlement failure.
        error_code: Optional override for the default tier error code.
        details: Optional structured context about the blocked feature.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.TIER_RESTRICTION,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a tier-related SDK error.

        Args:
            message: Human-readable description of the entitlement failure.
            error_code: Optional override for the default tier error code.
            details: Optional structured context about the blocked feature.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message, error_code=error_code, details=details)


class QanuniLicenseError(QanuniTierError):
    """Raised when a signed license is missing, invalid, or insufficient.

    Args:
        message: Human-readable description of the licensing failure.
        error_code: Optional override for the default licensing error code.
        details: Optional structured context about the blocked entitlement.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.LICENSE_REQUIRED,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a licensing-related SDK error.

        Args:
            message: Human-readable description of the licensing failure.
            error_code: Optional override for the default licensing error code.
            details: Optional structured context about the blocked entitlement.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message, error_code=error_code, details=details)


class QanuniAPIError(QanuniError):
    """Raised when the underlying model provider fails.

    Args:
        message: Human-readable description of the provider failure.
        status_code: Optional upstream HTTP or API status code.
        error_code: Optional override for the default provider error code.
        details: Optional structured context about the upstream failure.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: ErrorCode = ErrorCode.API_PROVIDER_FAILURE,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a provider-related SDK error.

        Args:
            message: Human-readable description of the provider failure.
            status_code: Optional upstream HTTP or API status code.
            error_code: Optional override for the default provider error code.
            details: Optional structured context about the upstream failure.

        Returns:
            None.

        Raises:
            None.
        """
        merged_details: dict[str, Any] = details or {}
        if status_code is not None:
            merged_details["status_code"] = status_code
        self.status_code: int | None = status_code
        super().__init__(message, error_code=error_code, details=merged_details)


class QanuniParseError(QanuniError):
    """Raised when the model output cannot be parsed.

    Args:
        message: Human-readable description of the parsing failure.
        raw_response: Raw text returned by the model, if available.
        error_code: Optional override for the default parse error code.
        details: Optional structured context about the parsing failure.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_response: str | None = None,
        error_code: ErrorCode = ErrorCode.PARSE_INVALID_JSON,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a parsing-related SDK error.

        Args:
            message: Human-readable description of the parsing failure.
            raw_response: Raw text returned by the model, if available.
            error_code: Optional override for the default parse error code.
            details: Optional structured context about the parsing failure.

        Returns:
            None.

        Raises:
            None.
        """
        merged_details: dict[str, Any] = details or {}
        if raw_response is not None:
            merged_details["raw_response"] = raw_response
        self.raw_response: str | None = raw_response
        super().__init__(message, error_code=error_code, details=merged_details)


class QanuniOutputError(QanuniError):
    """Raised when the model output does not match the expected schema.

    Args:
        message: Human-readable description of the schema mismatch.
        error_code: Optional override for the default output error code.
        details: Optional structured context about the schema mismatch.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.OUTPUT_SCHEMA_MISMATCH,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a structured-output validation error.

        Args:
            message: Human-readable description of the schema mismatch.
            error_code: Optional override for the default output error code.
            details: Optional structured context about the schema mismatch.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message, error_code=error_code, details=details)


class QanuniValidationError(QanuniError):
    """Raised when user input violates product or legal constraints.

    Args:
        message: Human-readable description of the validation failure.
        error_code: Optional override for the default validation error code.
        details: Optional structured context about the validation failure.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a validation-related SDK error.

        Args:
            message: Human-readable description of the validation failure.
            error_code: Optional override for the default validation error code.
            details: Optional structured context about the validation failure.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message, error_code=error_code, details=details)


class QanuniFeatureNotReadyError(QanuniError):
    """Raised when a catalogued tool is not implemented yet.

    Args:
        message: Human-readable description of the unfinished feature.
        error_code: Optional override for the default feature-readiness error code.
        details: Optional structured context about the missing feature.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.FEATURE_NOT_READY,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a feature-readiness SDK error.

        Args:
            message: Human-readable description of the unfinished feature.
            error_code: Optional override for the default feature-readiness error code.
            details: Optional structured context about the missing feature.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(message, error_code=error_code, details=details)
