"""Unit tests for Spec 4.6 split transaction precision."""

import pytest

from dojo.budgeting.services import split_amount_minor


def test_split_amount_minor_three_way_rounding() -> None:
    """Splitting 10.00 three ways stays in integer minor units."""
    shares = split_amount_minor(1_000, 3)
    assert shares == [333, 333, 334]
    assert sum(shares) == 1_000


def test_split_amount_minor_handles_negative_totals() -> None:
    """Negative spends distribute rounding to keep totals aligned."""
    shares = split_amount_minor(-1_000, 3)
    assert shares == [-333, -333, -334]
    assert sum(shares) == -1_000


def test_split_amount_minor_supports_zero_totals() -> None:
    """Zero totals still emit the requested number of legs."""
    shares = split_amount_minor(0, 4)
    assert shares == [0, 0, 0, 0]


def test_split_amount_minor_requires_positive_part_count() -> None:
    """Invalid splits reject non-positive part counts."""
    with pytest.raises(ValueError):
        split_amount_minor(100, 0)


def test_split_amount_minor_preserves_total_minor_units() -> None:
    """Arbitrary splits never leak or create value."""
    total = 12_345
    shares = split_amount_minor(total, 5)
    assert len(shares) == 5
    assert sum(shares) == total
    assert max(shares) - min(shares) <= 1
