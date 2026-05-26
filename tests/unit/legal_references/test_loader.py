from __future__ import annotations

import pytest

from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.legal_references import LegalReferenceLoader, LegalReferenceMode


def test_legal_reference_loader_reads_packaged_profile() -> None:
    """Packaged legal-reference profiles should load into typed reusable packets."""
    profile = LegalReferenceLoader.load("sa/contracts/review_baseline.yaml")

    assert profile.profile_id == "sa.contracts.review_baseline"
    assert profile.mode == LegalReferenceMode.STRICT
    assert "sa_contract_review_internal_standard" in profile.source_ids()
    assert "contracts-separate-mandatory-vs-best-practice" in profile.rule_ids()


def test_legal_reference_loader_rejects_missing_profile() -> None:
    """Missing legal-reference profiles should raise a stable validation error code."""
    with pytest.raises(QanuniValidationError) as exc_info:
        LegalReferenceLoader.load("sa/contracts/missing_profile.yaml")

    assert exc_info.value.error_code == ErrorCode.LEGAL_REFERENCE_FILE_MISSING
