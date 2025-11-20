"""Property-based tests for budgeting transactions."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources

import duckdb
from hypothesis import given, settings, strategies as st

from dojo.budgeting.schemas import NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


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


def build_service() -> TransactionEntryService:
    return TransactionEntryService()


amount_strategy = st.integers(min_value=-50_00, max_value=50_00).filter(lambda x: x != 0)


@given(amounts=st.lists(amount_strategy, min_size=1, max_size=5))
@settings(max_examples=25, deadline=None)
def test_account_balance_matches_sum(amounts: list[int]) -> None:
    with ledger_connection() as conn:
        service = build_service()
        for amt in amounts:
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="groceries",
                    amount_minor=amt,
                ),
            )
        row = conn.execute(
            "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'"
        ).fetchone()
        assert row is not None
        assert row[0] == 500000 + sum(amounts)


@given(
    operations=st.lists(
        st.tuples(amount_strategy, st.booleans()),
        min_size=2,
        max_size=6,
    )
)
@settings(max_examples=25, deadline=None)
def test_only_one_active_version_per_concept(
    operations: list[tuple[int, bool]],
) -> None:
    with ledger_connection() as conn:
        service = build_service()
        last_concept_id = None
        for amount_minor, reuse_concept in operations:
            concept = last_concept_id if reuse_concept and last_concept_id is not None else None
            result = service.create(
                conn,
                NewTransactionRequest(
                    concept_id=concept,
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="groceries",
                    amount_minor=amount_minor,
                ),
            )
            last_concept_id = result.concept_id

        rows = conn.execute(
            """
            SELECT concept_id, SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
            FROM transactions
            GROUP BY concept_id
            """
        ).fetchall()
        assert all(row[1] == 1 for row in rows)
