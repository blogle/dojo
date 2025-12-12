"""Property-based tests for Domain 3 allocation and RTA invariants."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import date, timedelta
from importlib import resources
from typing import Any

import duckdb
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dojo.budgeting.dao import BudgetingDAO
from dojo.budgeting.schemas import NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture

DrawFn = Callable[..., Any]


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    apply_base_budgeting_fixture(conn)
    try:
        yield conn
    finally:
        conn.close()


def build_transaction_service() -> TransactionEntryService:
    return TransactionEntryService()


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> dict[str, Any] | None:
    cursor = conn.execute(sql, params or [])
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [column[0] for column in cursor.description or ()]
    return {columns[idx]: row[idx] for idx in range(len(columns))}


CATEGORIES = ["groceries", "housing"]
allocation_amount_strategy = st.integers(min_value=1, max_value=100_00)


@st.composite
def reallocation_strategy(draw: DrawFn) -> tuple[str, str, int]:
    source = draw(st.sampled_from(CATEGORIES))
    dest = draw(st.sampled_from([c for c in CATEGORIES if c != source]))
    amount = draw(allocation_amount_strategy)
    return source, dest, amount


@given(reallocations=st.lists(reallocation_strategy(), min_size=1, max_size=5))
@settings(max_examples=10, deadline=None)
def test_reallocations_remain_zero_sum(reallocations: list[tuple[str, str, int]]) -> None:
    """Spec 3.2: Category-to-category reallocations keep total available constant."""
    with ledger_connection() as conn:
        service = build_transaction_service()
        dao = BudgetingDAO(conn)
        month = date.today().replace(day=1)

        service.allocate_envelope(conn, "groceries", 500_00, month)
        service.allocate_envelope(conn, "housing", 1_500_00, month)

        baseline = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        baseline_available = int(baseline["total_available"]) if baseline else 0

        for source, dest, amount in reallocations:
            record = dao.get_category_month_state(source, month)
            if record and record.available_minor >= amount:
                service.allocate_envelope(
                    conn,
                    dest,
                    amount,
                    month,
                    from_category_id=source,
                )

        final_row = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        final_available = int(final_row["total_available"]) if final_row else 0
        assert final_available == baseline_available


@given(
    prev_allocations=st.lists(st.integers(min_value=100, max_value=2_000_00), min_size=1, max_size=3),
    prev_spend=st.lists(st.integers(min_value=100, max_value=1_000_00), min_size=1, max_size=3),
    curr_allocations=st.lists(st.integers(min_value=100, max_value=2_000_00), min_size=1, max_size=3),
    curr_spend=st.lists(st.integers(min_value=100, max_value=1_000_00), min_size=1, max_size=3),
)
@settings(max_examples=12, deadline=None)
def test_fundamental_budget_equation(
    prev_allocations: list[int],
    prev_spend: list[int],
    curr_allocations: list[int],
    curr_spend: list[int],
) -> None:
    """Spec 3.6: Available(M) == Available(M-1) + Allocations(M) - Activity(M)."""
    with ledger_connection() as conn:
        service = build_transaction_service()
        dao = BudgetingDAO(conn)
        category = "groceries"
        prev_month = date(2025, 1, 1)
        curr_month = prev_month + timedelta(days=31)

        # Seed Ready to Assign so we can allocate funds.
        service.create(
            conn,
            NewTransactionRequest(
                transaction_date=prev_month,
                account_id="house_checking",
                category_id="income",
                amount_minor=sum(prev_allocations) + sum(curr_allocations) + 5_000,
            ),
        )

        for amount in prev_allocations:
            service.allocate_envelope(conn, category, amount, prev_month)
        for amount in prev_spend:
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=prev_month,
                    account_id="house_checking",
                    category_id=category,
                    amount_minor=-amount,
                ),
            )

        for amount in curr_allocations:
            service.allocate_envelope(conn, category, amount, curr_month)
        for amount in curr_spend:
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=curr_month,
                    account_id="house_checking",
                    category_id=category,
                    amount_minor=-amount,
                ),
            )

        detail = dao.get_budget_category_detail(category, curr_month)
        assert detail is not None, "expected category detail state"

        lhs = detail.available_minor
        rhs = detail.last_month_available_minor + detail.allocated_minor - detail.activity_minor
        assert lhs == rhs


@given(
    inflows=st.lists(st.integers(min_value=500, max_value=5_000_00), min_size=1, max_size=3),
    spend=st.lists(st.integers(min_value=100, max_value=2_000_00), min_size=1, max_size=5),
)
@settings(max_examples=10, deadline=None)
def test_global_zero_sum_between_cash_and_envelopes(
    inflows: list[int],
    spend: list[int],
) -> None:
    """Spec 3.7: On-budget cash equals Ready to Assign plus envelope balances."""
    with ledger_connection() as conn:
        service = build_transaction_service()
        month = date.today().replace(day=1)
        category = "groceries"

        for amount in inflows:
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=month,
                    account_id="house_checking",
                    category_id="income",
                    amount_minor=amount,
                ),
            )
            service.allocate_envelope(conn, category, amount // 2, month)

        for amount in spend:
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=month,
                    account_id="house_checking",
                    category_id=category,
                    amount_minor=-amount,
                ),
            )

        cash_row = _fetch_namespace(
            conn,
            """
            SELECT SUM(current_balance_minor) AS total_cash
            FROM accounts
            WHERE account_role = 'on_budget' AND account_class = 'cash'
            """,
        )
        total_cash = int(cash_row["total_cash"]) if cash_row and cash_row["total_cash"] is not None else 0

        available_row = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        total_available = (
            int(available_row["total_available"])
            if available_row and available_row["total_available"] is not None
            else 0
        )
        rta = service.ready_to_assign(conn, month)

        assert total_cash == total_available + rta
