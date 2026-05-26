"""Fallback JSON parsing helpers for model outputs."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from qanuni.core.exceptions import ErrorCode, QanuniOutputError, QanuniParseError

T = TypeVar("T", bound=BaseModel)


class OutputParser:
    """Convert raw JSON strings into typed Pydantic models.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    @staticmethod
    def parse(raw: str, model: type[T]) -> T:
        """Parse a raw JSON string into the supplied Pydantic model.

        Args:
            raw: Raw JSON string returned by the model provider.
            model: Target Pydantic model used for validation.

        Returns:
            A validated instance of the requested Pydantic model.

        Raises:
            QanuniParseError: If the payload is not valid JSON.
            QanuniOutputError: If the JSON payload does not satisfy the target schema.
        """
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise QanuniParseError(
                "Model returned invalid JSON.",
                raw_response=raw,
                error_code=ErrorCode.PARSE_INVALID_JSON,
            ) from exc

        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise QanuniOutputError(
                f"Model output did not match expected schema {model.__name__}.",
                error_code=ErrorCode.OUTPUT_SCHEMA_MISMATCH,
                details={"model_name": model.__name__},
            ) from exc
