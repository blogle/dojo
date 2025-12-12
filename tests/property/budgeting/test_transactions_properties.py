"""
Property-based tests for budgeting transactions.

This module uses the Hypothesis library to verify the correctness and
invariants of transaction processing within the budgeting domain. It
focuses on properties such as account balance consistency, temporal
integrity of transaction versions, and referential integrity.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace

import duckdb
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dojo.budgeting.errors import UnknownAccountError, UnknownCategoryError
from dojo.budgeting.schemas import NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Creates an in-memory DuckDB connection with schema and base fixtures applied.

    This fixture is used by property-based tests to provide a clean and consistent
    database state for each test run.

    Yields
    ------
    Generator[duckdb.DuckDBPyConnection, None, None]
        An in-memory DuckDB connection object.
    """
    conn = duckdb.connect(database=":memory:")
    # Get the package path where migration SQL files are located.
    migrations_pkg = resources.files("dojo.sql.migrations")
    # Apply all schema migrations to the in-memory database.
    apply_migrations(conn, migrations_pkg)
    # Apply a base set of budgeting data for tests.
    apply_base_budgeting_fixture(conn)
    try:
        yield conn
    finally:
        # Ensure the connection is closed after the test completes.
        conn.close()


def build_service() -> TransactionEntryService:
    """
    Builds and returns a new TransactionEntryService instance.

    Returns
    -------
    TransactionEntryService
        A new instance of the TransactionEntryService.
    """
    return TransactionEntryService()


def _fetchall_namespaces(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> list[SimpleNamespace]:
    """
    Executes an SQL query and fetches all rows as a list of SimpleNamespace objects.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    sql : str
        The SQL query string to execute.
    params : list[object] | tuple[object, ...] | None, optional
        Parameters to bind to the SQL query.

    Returns
    -------
    list[SimpleNamespace]
        A list of SimpleNamespace objects, each representing a row.
    """
    cursor = conn.execute(sql, params or [])
    rows = cursor.fetchall()
    # Extract column names from the cursor description.
    columns = [column[0] for column in cursor.description or ()]
    # Convert each row into a SimpleNamespace.
    return [SimpleNamespace(**{columns[idx]: row[idx] for idx in range(len(columns))}) for row in rows]


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> SimpleNamespace:
    """
    Executes an SQL query and fetches a single row as a SimpleNamespace, asserting it's not None.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    sql : str
        The SQL query string to execute.
    params : list[object] | tuple[object, ...] | None, optional
        Parameters to bind to the SQL query.

    Returns
    -------
    SimpleNamespace
        A SimpleNamespace object representing the fetched row.

    Raises
    ------
    AssertionError
        If no row is fetched (i.e., `fetchone()` returns None).
    """
    cursor = conn.execute(sql, params or [])
    row = cursor.fetchone()
    # Assert that a row was actually returned.
    assert row is not None, "Expected to fetch a row, but got None."
    # Extract column names from the cursor description.
    columns = [column[0] for column in cursor.description or ()]
    # Map column names to row values and create a SimpleNamespace.
    data = {columns[idx]: row[idx] for idx in range(len(columns))}
    return SimpleNamespace(**data)


# Strategy for generating transaction amounts (non-zero).
amount_strategy = st.integers(min_value=-50_00, max_value=50_00).filter(lambda x: x != 0)


@given(amounts=st.lists(amount_strategy, min_size=1, max_size=5))
@settings(max_examples=25, deadline=None)
def test_account_balance_matches_sum(amounts: list[int]) -> None:
    """
    Verifies that the account's current balance accurately reflects the sum of all transactions.

    This property test simulates a series of transactions on a specific account
    and asserts that the final `current_balance_minor` stored in the database
    matches the initial balance plus the sum of all generated transaction amounts.

    Parameters
    ----------
    amounts : list[int]
        A list of generated transaction amounts in minor units.
    """
    with ledger_connection() as conn:
        service = build_service()
        # Process each generated transaction amount.
        for amt in amounts:
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="house_checking",  # Use a fixed account for this test.
                    category_id="groceries",  # Use a fixed category.
                    amount_minor=amt,
                ),
            )
        # Fetch the current balance of the test account directly from the database.
        balance_row = _fetch_namespace(
            conn,
            "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'",
        )
        # Assert that the recorded balance matches the initial balance plus the sum of all transaction amounts.
        assert balance_row.current_balance_minor == 500000 + sum(amounts)


# Strategy for generating a list of tuples, each containing a transaction amount and a boolean
# indicating whether to reuse the concept_id.
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
    """
    Verifies the temporal ledger invariant that only one transaction version is active per concept.

    This property test simulates a chain of transaction creations and updates
    (by reusing `concept_id`). It then asserts that for any given `concept_id`,
    there is always exactly one `is_active = TRUE` entry in the `transactions` table.

    Parameters
    ----------
    operations : list[tuple[int, bool]]
        A list of operations, where each operation is a tuple containing:
        - `amount_minor` (int): The transaction amount.
        - `reuse_concept` (bool): Whether to reuse the `concept_id` from the previous operation.
    """
    with ledger_connection() as conn:
        service = build_service()
        last_concept_id = None
        for amount_minor, reuse_concept in operations:
            # Determine whether to use an existing concept_id or generate a new one.
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
            # Store the concept_id of the newly created/updated transaction.
            last_concept_id = result.concept_id

        # Query the database to count active transaction versions for each concept_id.
        rows = _fetchall_namespaces(
            conn,
            """
            SELECT concept_id, SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
            FROM transactions
            GROUP BY concept_id
            """,
        )
        # Assert that for every concept_id, there is exactly one active row.
        assert all(row.active_rows == 1 for row in rows)


# Strategy for generating a sequence of transaction edit amounts.
edit_chain_strategy = st.lists(amount_strategy, min_size=2, max_size=5)


@given(edits=edit_chain_strategy)
@settings(max_examples=10, deadline=None)
def test_chronological_integrity_of_edits(edits: list[int]) -> None:
    """
    Verifies the chronological integrity of transaction versions after edits.

    When a transaction is edited, a new version is created, and the `valid_to`
    timestamp of the previous version should match the `valid_from` timestamp
    of the new version, ensuring no gaps or overlaps in the transaction history.
    The last version should have an open-ended `valid_to` (9999-12-31).

    Parameters
    ----------
    edits : list[int]
        A list of transaction amounts, representing successive edits to a single transaction.
    """
    with ledger_connection() as conn:
        service = build_service()

        # Create the initial transaction.
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

        # Perform the subsequent edits, reusing the same concept_id.
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

        # Retrieve all versions of the transaction, ordered by their valid_from timestamp.
        versions = _fetchall_namespaces(
            conn,
            "SELECT valid_from, valid_to FROM transactions WHERE concept_id = ? ORDER BY valid_from",
            [str(concept_id)],
        )

        # Assert that the number of versions matches the number of edits.
        assert len(versions) == len(edits)

        # Verify that valid_to of a version matches valid_from of the subsequent version.
        for i in range(len(versions) - 1):
            assert versions[i].valid_to == versions[i + 1].valid_from, f"Gap or overlap found at version {i}"

        # Check that the last version is open-ended (valid until the end of time).
        last_valid_to = versions[-1].valid_to
        assert last_valid_to.year == 9999
        assert last_valid_to.month == 12
        assert last_valid_to.day == 31


def test_referential_integrity() -> None:
    """
    Verifies that creating transactions with non-existent or inactive
    account/category IDs fails with appropriate exceptions.

    This test ensures that the system enforces referential integrity rules
    by preventing transactions from being recorded against invalid or
    unavailable financial entities.
    """
    with ledger_connection() as conn:
        service = build_service()

        # Test case: Attempt to create a transaction with a non-existent account ID.
        with pytest.raises(UnknownAccountError):
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="non_existent_account",
                    category_id="groceries",
                    amount_minor=100,
                ),
            )

        # Test case: Attempt to create a transaction with a non-existent category ID.
        with pytest.raises(UnknownCategoryError):
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="non_existent_category",
                    amount_minor=100,
                ),
            )

        # Test case: Attempt to create a transaction with an inactive account.
        # First, deactivate the 'house_checking' account.
        conn.execute("UPDATE accounts SET is_active = FALSE WHERE account_id = 'house_checking'")
        with pytest.raises(UnknownAccountError):
            service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id="house_checking",
                    category_id="groceries",
                    amount_minor=100,
                ),
            )


operation_strategy = st.lists(
    st.one_of(
        st.tuples(st.just("edit"), amount_strategy),
        st.tuples(st.just("void"), st.just(0)),
    ),
    min_size=1,
    max_size=5,
)


@given(operations=operation_strategy)
@settings(max_examples=10, deadline=None)
def test_temporal_chain_handles_edits_and_voids(operations: list[tuple[str, int]]) -> None:
    """Spec 2.7: Random edits/voids maintain a continuous temporal chain."""
    with ledger_connection() as conn:
        service = build_service()
        base_amount = operations[0][1] if operations and operations[0][0] == "edit" else 1_00
        result = service.create(
            conn,
            NewTransactionRequest(
                transaction_date=date.today(),
                account_id="house_checking",
                category_id="groceries",
                amount_minor=base_amount,
            ),
        )
        concept_id = result.concept_id
        voided = False

        for op, value in operations:
            if op == "edit" and not voided:
                service.create(
                    conn,
                    NewTransactionRequest(
                        concept_id=concept_id,
                        transaction_date=date.today(),
                        account_id="house_checking",
                        category_id="groceries",
                        amount_minor=value,
                    ),
                )
            elif op == "void" and not voided:
                service.delete_transaction(conn, concept_id)
                voided = True

        versions = _fetchall_namespaces(
            conn,
            """
            SELECT valid_from, valid_to, is_active
            FROM transactions
            WHERE concept_id = ?
            ORDER BY valid_from
            """,
            [str(concept_id)],
        )
        assert versions, "expected at least one version"

        for idx in range(len(versions) - 1):
            assert versions[idx].valid_to == versions[idx + 1].valid_from

        active_rows = sum(1 for row in versions if row.is_active)
        if voided:
            assert active_rows == 0
        else:
            assert active_rows == 1
            assert versions[-1].valid_to.year == 9999
