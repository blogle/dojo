from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from dojo.investments.service import compute_portfolio_totals

quantity_strategy = st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False)
price_minor_strategy = st.integers(min_value=0, max_value=1_000_000)


@st.composite
def lots_strategy(draw: st.DrawFn) -> list[tuple[float, int | None]]:
    count = draw(st.integers(min_value=0, max_value=10))
    lots: list[tuple[float, int | None]] = []
    for _ in range(count):
        qty = draw(quantity_strategy)
        price_minor = draw(st.one_of(price_minor_strategy, st.none()))
        lots.append((qty, price_minor))
    return lots


@given(
    ledger_cash_minor=st.integers(min_value=-1_000_000, max_value=1_000_000),
    uninvested_cash_minor=st.integers(min_value=0, max_value=1_000_000),
    lots=lots_strategy(),
)
@settings(max_examples=50, deadline=None)
def test_nav_identity_holds_in_minor_units(
    ledger_cash_minor: int,
    uninvested_cash_minor: int,
    lots: list[tuple[float, int | None]],
) -> None:
    totals = compute_portfolio_totals(
        ledger_cash_minor=ledger_cash_minor,
        uninvested_cash_minor=uninvested_cash_minor,
        lots=lots,
    )

    assert totals.nav_minor == uninvested_cash_minor + totals.holdings_value_minor


@given(
    ledger_cash_minor=st.integers(min_value=-1_000_000, max_value=1_000_000),
    uninvested_cash_minor=st.integers(min_value=0, max_value=1_000_000),
    lots=lots_strategy(),
)
@settings(max_examples=50, deadline=None)
def test_return_identity_holds_in_minor_units(
    ledger_cash_minor: int,
    uninvested_cash_minor: int,
    lots: list[tuple[float, int | None]],
) -> None:
    totals = compute_portfolio_totals(
        ledger_cash_minor=ledger_cash_minor,
        uninvested_cash_minor=uninvested_cash_minor,
        lots=lots,
    )

    assert totals.total_return_minor == totals.nav_minor - ledger_cash_minor
