from __future__ import annotations

import pytest

from qanuni.core.exceptions import QanuniOutputError, QanuniParseError
from qanuni.core.output_parser import OutputParser
from qanuni.models.labor import ProbationCheckResult


def test_output_parser_parses_valid_json() -> None:
    raw = """
    {
      "is_legal": true,
      "max_allowed_days": 90,
      "violations": [],
      "employee_rights_during_probation": [],
      "employer_rights_during_probation": [],
      "legal_explanation": "ok"
    }
    """
    result = OutputParser.parse(raw, ProbationCheckResult)
    assert result.is_legal is True


def test_output_parser_raises_on_invalid_json() -> None:
    with pytest.raises(QanuniParseError):
        OutputParser.parse("not-json", ProbationCheckResult)


def test_output_parser_raises_on_schema_mismatch() -> None:
    raw = '{"unexpected": "value"}'
    with pytest.raises(QanuniOutputError):
        OutputParser.parse(raw, ProbationCheckResult)
