"""Saudi labor-law constants and deterministic helpers.

These values were aligned against official Saudi government sources reviewed on
2026-05-23. Deterministic encoding is intentionally limited to rules that were
directly verified. Areas with source conflicts are left out of hardcoded logic.
"""

from __future__ import annotations

BASE_MAX_PROBATION_DAYS = 90
EXTENDED_MAX_PROBATION_DAYS = 180

FIRST_FIVE_YEARS_MULTIPLIER = 0.5
AFTER_FIVE_YEARS_MULTIPLIER = 1.0

ARTICLE_53_REFERENCE = "المادة 53 من نظام العمل السعودي"
ARTICLE_84_REFERENCE = "المادة 84 من نظام العمل السعودي"


def max_probation_days(*, written_extension: bool) -> int:
    """Return the verified Saudi probation ceiling for the given scenario.

    Args:
        written_extension: Whether a written extension to the probation term exists.

    Returns:
        The maximum lawful probation days for the supplied scenario.

    Raises:
        None.
    """
    return EXTENDED_MAX_PROBATION_DAYS if written_extension else BASE_MAX_PROBATION_DAYS


def calculate_base_end_of_service(monthly_salary: float, years_of_service: float) -> float:
    """Calculate the base award before any resignation reduction rules are applied.

    Args:
        monthly_salary: Last monthly salary used as the award basis.
        years_of_service: Total completed or prorated years of service.

    Returns:
        The base end-of-service award before resignation discounts.

    Raises:
        None.
    """
    first_segment_years = min(years_of_service, 5)
    second_segment_years = max(years_of_service - 5, 0)
    return (
        monthly_salary * FIRST_FIVE_YEARS_MULTIPLIER * first_segment_years
        + monthly_salary * AFTER_FIVE_YEARS_MULTIPLIER * second_segment_years
    )


def apply_resignation_discount(base_award: float, years_of_service: float) -> float:
    """Apply resignation entitlement reductions to the base award amount.

    Args:
        base_award: Base end-of-service award before resignation reduction.
        years_of_service: Total completed or prorated years of service.

    Returns:
        The resignation-adjusted award amount.

    Raises:
        None.
    """
    if years_of_service < 2:
        return 0.0
    if years_of_service < 5:
        return base_award / 3
    if years_of_service < 10:
        return base_award * (2 / 3)
    return base_award
