from __future__ import annotations

from qanuni.jurisdictions.sa_labor import (
    BASE_MAX_PROBATION_DAYS,
    EXTENDED_MAX_PROBATION_DAYS,
    apply_resignation_discount,
    calculate_base_end_of_service,
    max_probation_days,
)


def test_probation_constants_match_verified_limits() -> None:
    assert BASE_MAX_PROBATION_DAYS == 90
    assert EXTENDED_MAX_PROBATION_DAYS == 180
    assert max_probation_days(written_extension=False) == 90
    assert max_probation_days(written_extension=True) == 180


def test_end_of_service_base_calculation() -> None:
    assert calculate_base_end_of_service(10000, 7) == 45000


def test_resignation_discount_under_two_years() -> None:
    assert apply_resignation_discount(10000, 1.9) == 0.0


def test_resignation_discount_between_two_and_five_years() -> None:
    assert apply_resignation_discount(30000, 3) == 10000


def test_resignation_discount_between_five_and_ten_years() -> None:
    assert apply_resignation_discount(45000, 7) == 30000
