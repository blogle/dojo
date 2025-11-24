"""Property-based tests for budgeting transactions."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace

import duckdb
from hypothesis import given, settings, strategies as st

from dojo.budgeting.schemas import NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture

import pytest
from dojo.budgeting.errors import UnknownAccount, UnknownCategory



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


def _fetchall_namespaces(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> list[SimpleNamespace]:
    cursor = conn.execute(sql, params or [])
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description or ()]
    return [SimpleNamespace(**{columns[idx]: row[idx] for idx in range(len(columns))}) for row in rows]


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> SimpleNamespace:
    cursor = conn.execute(sql, params or [])
    row = cursor.fetchone()
    assert row is not None
    columns = [column[0] for column in cursor.description or ()]
    data = {columns[idx]: row[idx] for idx in range(len(columns))}
    return SimpleNamespace(**data)


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
        balance_row = _fetch_namespace(
            conn,
            "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'",
        )
        assert balance_row.current_balance_minor == 500000 + sum(amounts)


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

        rows = _fetchall_namespaces(
            conn,
            """
            SELECT concept_id, SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
            FROM transactions
            GROUP BY concept_id
            """,
        )
        assert all(row.active_rows == 1 for row in rows)


edit_chain_strategy = st.lists(amount_strategy, min_size=2, max_size=5)

@given(edits=edit_chain_strategy)
@settings(max_examples=10, deadline=None)
def test_chronological_integrity_of_edits(edits):
    """
    Verify that performing multiple edits on a single transaction
    maintains that `valid_from` and `valid_to` timestamps are always
    correctly ordered, with no overlaps or gaps.
    """
    with ledger_connection() as conn:
        service = build_service()

        # Create the initial transaction
        initial_result = service.create(
            conn,
            NewTransactionRequest(
                transaction_date=date.today(),
                account_id="house_checking",
                category_id="groceries",
                amount_minor=edits[0],
            ),
        )
        concept_id = initial_result.concept_id

        # Perform the edits
        for amount in edits[1:]:
            service.create(
                conn,
                NewTransactionRequest(
                    concept_id=concept_id,
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="groceries",
                    amount_minor=amount,
                ),
            )
            
        # Verify the chain of validity
        versions = _fetchall_namespaces(
            conn,
            "SELECT valid_from, valid_to FROM transactions WHERE concept_id = ? ORDER BY valid_from",
            [str(concept_id)],
        )

        assert len(versions) == len(edits)

        for i in range(len(versions) - 1):
            assert versions[i].valid_to == versions[i + 1].valid_from, f"Gap or overlap found at version {i}"

        # Check that the last version is open-ended
        last_valid_to = versions[-1].valid_to
        assert last_valid_to.year == 9999
        assert last_valid_to.month == 12
        assert last_valid_to.day == 31


def test_referential_integrity():
    """
    Verify that creating transactions pointing to non-existent or inactive
    `account_id`s and `category_id`s fails as expected.
    """
    with ledger_connection() as conn:
        service = build_service()

        # Test with non-existent account
        with pytest.raises(UnknownAccount):
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="non_existent_account",
                    category_id="groceries",
                    amount_minor=100,
                ),
            )

        # Test with non-existent category
        with pytest.raises(UnknownCategory):
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="non_existent_category",
                    amount_minor=100,
                ),
            )
            
        # Test with inactive account
        conn.execute("UPDATE accounts SET is_active = FALSE WHERE account_id = 'house_checking'")
        with pytest.raises(UnknownAccount):
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="groceries",
                    amount_minor=100,
                ),
            )
