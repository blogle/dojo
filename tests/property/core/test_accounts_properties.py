"""
Property-based tests for account service invariants.

This module utilizes the Hypothesis library to perform property-based testing
on functionalities related to financial accounts, ensuring data consistency
and correct behavior under various scenarios, especially concerning balance
synchronization and the creation of associated detail records.
"""

import string
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import duckdb
from hypothesis import given, settings
from hypothesis import strategies as st

from dojo.budgeting.schemas import (
    AccountClass,
    AccountCreateRequest,
    NewTransactionRequest,
)
from dojo.budgeting.services import (
    AccountAdminService,
    TransactionEntryService,
    derive_payment_category_id,
    derive_payment_category_name,
)
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Creates an in-memory DuckDB connection with schema and base fixtures applied.

    This fixture provides a clean and consistent database state for each test run,
    with all necessary migrations applied and a base set of budgeting data.

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


def build_transaction_service() -> TransactionEntryService:
    """
    Builds and returns a new TransactionEntryService instance.

    Returns
    -------
    TransactionEntryService
        A new instance of the TransactionEntryService.
    """
    return TransactionEntryService()


def build_account_admin_service() -> AccountAdminService:
    """
    Builds and returns a new AccountAdminService instance.

    Returns
    -------
    AccountAdminService
        A new instance of the AccountAdminService.
    """
    return AccountAdminService()


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


# Strategies
# Strategy for generating valid account IDs (alphanumeric with underscores).
account_id_strategy = st.text(min_size=3, max_size=20, alphabet=string.ascii_lowercase + string.digits + "_")
# Strategy for generating account names.
account_name_strategy = st.text(min_size=3, max_size=50)
# Strategy for sampling account classes, excluding 'tangible' and 'accessible' for this context.
account_class_strategy = st.sampled_from([c for c in AccountClass.__args__ if c not in ["tangible", "accessible"]])
# Strategy for generating non-zero transaction amounts in minor units.
amount_strategy = st.integers(min_value=-50_000, max_value=50_000).filter(lambda x: x != 0)


@st.composite
def cash_account_strategy(draw: Callable[..., Any]) -> dict[str, Any]:
    """
    Hypothesis strategy for generating a dictionary representing a cash account.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    dict
        A dictionary containing data for creating a cash account.
    """
    return {
        "account_id": draw(account_id_strategy),
        "name": draw(account_name_strategy),
        "account_type": "asset",
        "account_class": "cash",
        "account_role": "on_budget",
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
        "opened_on": date.today(),
    }


@st.composite
def account_create_request_strategy(draw: Callable[..., Any]) -> AccountCreateRequest:
    """
    Hypothesis strategy for generating `AccountCreateRequest` payloads.

    This strategy ensures that the `account_type` is consistent with the
    drawn `account_class` (e.g., 'liability' for 'credit' or 'loan' classes).

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    AccountCreateRequest
        A generated `AccountCreateRequest` object.
    """
    account_class = draw(account_class_strategy)
    account_type = "liability" if account_class in ["credit", "loan"] else "asset"
    return AccountCreateRequest(
        account_id=draw(account_id_strategy),
        name=draw(account_name_strategy),
        account_type=account_type,
        account_class=account_class,
        account_role="on_budget",
        current_balance_minor=0,
        currency="USD",
        is_active=True,
        opened_on=date.today(),
    )


@st.composite
def credit_account_create_request_strategy(draw: Callable[..., Any]) -> AccountCreateRequest:
    """
    Hypothesis strategy for generating `AccountCreateRequest` payloads specifically for credit accounts.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    AccountCreateRequest
        A generated `AccountCreateRequest` object configured for a credit account.
    """
    return AccountCreateRequest(
        account_id=draw(account_id_strategy),
        name=draw(account_name_strategy),
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
        current_balance_minor=0,
        currency="USD",
        is_active=True,
        opened_on=date.today(),
    )


# Mapping of account classes to their corresponding detail table names.
DETAIL_TABLES = {
    "cash": "cash_account_details",
    "credit": "credit_account_details",
    "investment": "investment_account_details",
    "loan": "loan_account_details",
    # "tangible": "tangible_asset_details",
    # "accessible": "accessible_asset_details",
}


@given(
    account_data=cash_account_strategy(),
    initial_balance=st.integers(min_value=-100000, max_value=100000),
    transactions=st.lists(amount_strategy, min_size=1, max_size=10),
)
@settings(max_examples=10, deadline=None)
def test_balance_synchronization(
    account_data: dict[str, Any],
    initial_balance: int,
    transactions: list[int],
) -> None:
    """
    Verifies that the `accounts.current_balance_minor` field correctly
    reflects the sum of all associated transactions.

    This property test creates an account, an optional initial balance
    transaction, and a series of subsequent transactions. It then asserts
    that the account's final recorded balance matches the sum of all
    transaction amounts.

    Parameters
    ----------
    account_data : dict
        Generated dictionary containing base data for a cash account.
    initial_balance : int
        A generated initial balance amount in minor units.
    transactions : list[int]
        A list of generated transaction amounts in minor units.
    """
    with ledger_connection() as conn:
        transaction_service = build_transaction_service()

        # Manually create account records. The service's `create_account` handles this,
        # but for direct balance testing, we create it here to control initial state.
        conn.execute(
            """
            INSERT INTO accounts (
                account_id,
                name,
                account_type,
                account_class,
                account_role,
                current_balance_minor,
                currency,
                is_active,
                opened_on
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(account_data.values()),
        )
        conn.execute(
            """
            INSERT INTO cash_account_details (detail_id, account_id) VALUES (?, ?)
            """,
            [str(uuid4()), account_data["account_id"]],
        )

        # 1. Create an opening balance transaction if the initial balance is non-zero.
        if initial_balance != 0:
            transaction_service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id=account_data["account_id"],
                    category_id="opening_balance",
                    amount_minor=initial_balance,
                ),
            )

        # 2. Create a series of transactions generated by Hypothesis.
        for amount in transactions:
            transaction_service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id=account_data["account_id"],
                    category_id="groceries",  # Use an arbitrary existing category.
                    amount_minor=amount,
                ),
            )

        # 3. Verify the final balance in the 'accounts' table.
        final_balance_row = _fetch_namespace(
            conn,
            "SELECT current_balance_minor FROM accounts WHERE account_id = ?",
            [account_data["account_id"]],
        )
        final_balance = final_balance_row.current_balance_minor

        # 4. Calculate the total of all transactions directly from the 'transactions' table.
        total_transactions_row = _fetch_namespace(
            conn,
            "SELECT SUM(amount_minor) AS total_amount_minor FROM transactions WHERE account_id = ?",
            [account_data["account_id"]],
        )
        total_transactions = total_transactions_row.total_amount_minor

        # Assert that the account's current balance matches the sum of its transactions.
        assert final_balance == total_transactions


@given(payload=account_create_request_strategy())
@settings(max_examples=10, deadline=None)
def test_one_to_one_account_details(payload: AccountCreateRequest) -> None:
    """
    Verifies the one-to-one relationship between `accounts` and detail tables.

    This property test creates an account using the `AccountAdminService`
    and then asserts that:
    1. Exactly one corresponding record exists in the correct `*_account_details` table.
    2. No records exist in any other `*_account_details` tables for that account.
    """
    with ledger_connection() as conn:
        service = build_account_admin_service()
        # Create the account, which should also create its detail record.
        service.create_account(conn, payload)

        # Determine the expected detail table based on the account class.
        target_table = DETAIL_TABLES[payload.account_class]

        # Check that the target detail table has exactly one record for this account.
        count_row = _fetch_namespace(
            conn,
            f"SELECT COUNT(*) AS row_count FROM {target_table} WHERE account_id = ?",
            [payload.account_id],
        )
        assert count_row.row_count == 1, f"Expected 1 record in {target_table}, found {count_row.row_count}"

        # Check that all other detail tables do NOT have a record for this account.
        for account_class, detail_table in DETAIL_TABLES.items():
            if account_class == payload.account_class:
                continue
            count_row = _fetch_namespace(
                conn,
                f"SELECT COUNT(*) AS row_count FROM {detail_table} WHERE account_id = ?",
                [payload.account_id],
            )
            assert count_row.row_count == 0, f"Expected 0 records in {detail_table}, found {count_row.row_count}"


@given(payload=credit_account_create_request_strategy())
@settings(max_examples=10, deadline=None)
def test_credit_account_creates_payment_category(payload: AccountCreateRequest) -> None:
    """
    Verifies that creating a 'credit' class account automatically
    creates a corresponding "payment" category.

    This test asserts that for every newly created liability account of
    `credit` class, a unique payment category and its group are correctly
    registered in the `budget_categories` and `budget_category_groups` tables.

    Parameters
    ----------
    payload : AccountCreateRequest
        Generated `AccountCreateRequest` for a credit account.
    """
    with ledger_connection() as conn:
        service = build_account_admin_service()
        # Create the credit account using the admin service.
        service.create_account(conn, payload)

        # Derive the expected category ID and name for the payment category.
        expected_category_id = derive_payment_category_id(payload.account_id)
        expected_category_name = derive_payment_category_name(payload.name)

        # Fetch the created payment category from the database.
        category_row = _fetch_namespace(
            conn,
            "SELECT name, group_id FROM budget_categories WHERE category_id = ?",
            [expected_category_id],
        )

        # Assert that the payment category was created with the correct name and group ID.
        assert category_row.name == expected_category_name, "Payment category was not created with the expected name."
        assert category_row.group_id == "credit_card_payments", (
            "Payment category was not assigned to the 'credit_card_payments' group."
        )

        # Fetch the credit card payment group itself to verify its existence and name.
        group_row = _fetch_namespace(
            conn,
            "SELECT name FROM budget_category_groups WHERE group_id = 'credit_card_payments'",
        )

        assert group_row.name == "Credit Card Payments", (
            "Credit card payment group does not exist or has an incorrect name."
        )
