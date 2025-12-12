"""Unit tests for Domain 10 goal calculation helpers."""

import pytest

from dojo.budgeting.services import GoalCalculator


def test_target_date_monthly_amount_basic() -> None:
    """Spec 10.1: Target-date goals divide evenly across remaining months."""
    assert GoalCalculator.target_date_monthly_amount(1_200_00, 12) == 100_00


def test_target_date_existing_balance_reduces_need() -> None:
    """Spec 10.2: Existing savings lower the required contribution."""
    assert GoalCalculator.target_date_monthly_amount(600_00, 6, current_available_minor=120_00) == 80_00


def test_catch_up_monthly_amount_after_skipped_month() -> None:
    """Spec 10.3: Skipping a month increases the monthly funding requirement."""
    assert GoalCalculator.catch_up_monthly_amount(1_200_00, 0, 11) == 10_909


def test_recurring_shortfall_only_counts_current_month_allocations() -> None:
    """Spec 10.4: Recurring monthly goals use the month's allocations, not rollovers."""
    assert GoalCalculator.recurring_shortfall(1_500, 1_500) == 0
    assert GoalCalculator.recurring_shortfall(1_500, 0) == 1_500


def test_recurring_interval_monthly_amount_normalizes_interval() -> None:
    """Spec 10.5: Interval goals normalize into even monthly targets."""
    assert GoalCalculator.recurring_interval_monthly_amount(150_00, 3) == 50_00


def test_goal_calculator_validates_inputs() -> None:
    with pytest.raises(ValueError):
        GoalCalculator.target_date_monthly_amount(10_00, 0)
    with pytest.raises(ValueError):
        GoalCalculator.catch_up_monthly_amount(10_00, 0, 0)
    with pytest.raises(ValueError):
        GoalCalculator.recurring_interval_monthly_amount(10_00, 0)
