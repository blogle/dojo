"""Legacy net worth marks computations (Aspire parity).

We preserve Aspire's snapshot log verbatim. Aspire's displayed net worth history
is computed by month buckets (missing mark => 0 contribution) and sign derived
from the configured NetWorthAssets/NetWorthDebts lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LegacyMark:
    mark_date: date
    category_name: str
    amount_minor: int  # magnitude (non-negative)


def _month_end(d: date) -> date:
    # First of next month minus one day.
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    return next_month.fromordinal(next_month.toordinal() - 1)


def _month_iter(start: date, end: date) -> list[date]:
    # Return month-end dates from start..end inclusive.
    cursor = date(start.year, start.month, 1)
    out: list[date] = []
    while True:
        end_of_month = _month_end(cursor)
        out.append(end_of_month)
        if end_of_month >= end:
            break
        # Move to next month.
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return out


def aspire_bucket_series(
    marks: list[LegacyMark],
    *,
    net_worth_assets: set[str],
    net_worth_debts: set[str],
) -> list[tuple[date, int]]:
    """Compute Aspire-parity monthly net worth totals.

    - Only categories in assets/debts lists contribute to totals.
    - Marks are summed within their month bucket.
    - Missing marks for a category/month contribute 0.
    """

    if not marks:
        return []

    included = net_worth_assets | net_worth_debts
    filtered = [m for m in marks if m.category_name in included]
    if not filtered:
        return []

    min_date = min(m.mark_date for m in filtered)
    max_date = max(m.mark_date for m in filtered)
    months = _month_iter(min_date, max_date)

    # Aggregate by (month_end, category)
    by_month_cat: dict[tuple[date, str], int] = {}
    for m in filtered:
        me = _month_end(m.mark_date)
        key = (me, m.category_name)
        by_month_cat[key] = by_month_cat.get(key, 0) + int(m.amount_minor)

    points: list[tuple[date, int]] = []
    for me in months:
        total = 0
        for cat in included:
            magnitude = by_month_cat.get((me, cat), 0)
            if cat in net_worth_debts:
                total -= magnitude
            else:
                total += magnitude
        points.append((me, total))
    return points
