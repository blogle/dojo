"""
Property-based tests for investment service invariants.

This module uses the Hypothesis library to explore the behavior of the
investment domain, specifically focusing on how positions are managed
and how account types are enforced (or not enforced) at the database level.
These tests highlight current limitations in database-level constraints
and indicate where application-level logic is crucial.
"""

import string
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import duckdb
from hypothesis import given, settings
from hypothesis import strategies as st

from dojo.budgeting.schemas import AccountClass
from dojo.budgeting.services import AccountAdminService
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
account_id_strategy = st.text(
    min_size=3, max_size=20, alphabet=string.ascii_lowercase + string.digits + "_"
)
# Strategy for generating instrument tickers.
instrument_strategy = st.text(min_size=1, max_size=5, alphabet=string.ascii_uppercase)
# Strategy for generating quantity of an instrument.
quantity_strategy = st.floats(min_value=0.1, max_value=1000.0)
# Strategy for generating market value of a position in minor units.
market_value_strategy = st.integers(min_value=1, max_value=1_000_000_00)


@st.composite
def investment_account_strategy(draw):
    """
    Hypothesis strategy for generating a dictionary representing an investment account.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    dict
        A dictionary containing data for creating an investment account.
    """
    return {
        "account_id": draw(account_id_strategy),
        "name": "Test Investment Account",
        "account_type": "asset",
        "account_class": "investment",
        "account_role": "on_budget",
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
        "opened_on": date.today(),
    }


@st.composite
def non_investment_account_strategy(draw):
    """
    Hypothesis strategy for generating a dictionary representing a non-investment account.

    This strategy ensures that the generated account is of a class other than 'investment'.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    dict
        A dictionary containing data for creating a non-investment account.
    """
    non_investment_class = draw(
        st.sampled_from([c for c in AccountClass.__args__ if c != "investment"])
    )
    account_type = (
        "liability" if non_investment_class in ["credit", "loan"] else "asset"
    )
    return {
        "account_id": draw(account_id_strategy),
        "name": "Test Non-Investment Account",
        "account_type": account_type,
        "account_class": non_investment_class,
        "account_role": "on_budget",
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
        "opened_on": date.today(),
    }


def _create_account(conn: duckdb.DuckDBPyConnection, account_data: dict[str, Any]):
    """
    Manually creates an account and its corresponding detail entry in the database.

    This helper function is used by tests to set up account data directly in the database,
    bypassing the service layer to test database-level invariants or behaviors.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    account_data : dict[str, Any]
        A dictionary containing the account's attributes.
    """
    # Insert the main account record into the accounts table.
    conn.execute(
        """
        INSERT INTO accounts (account_id, name, account_type, account_class, account_role, current_balance_minor, currency, is_active, opened_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        list(account_data.values()),
    )
    # Insert into the specific detail table based on the account's class.
    detail_table = f"{account_data['account_class']}_account_details"
    if account_data["account_class"] in ["cash", "credit", "investment", "loan"]:
        conn.execute(
            f"INSERT INTO {detail_table} (detail_id, account_id) VALUES (?, ?)",
            [str(uuid4()), account_data["account_id"]],
        )


@given(
    account_data=investment_account_strategy(),
    instrument=instrument_strategy,
    quantity=quantity_strategy,
    market_value=market_value_strategy,
)
@settings(max_examples=10, deadline=None)
def test_position_uniqueness_is_not_enforced(
    account_data, instrument, quantity, market_value
):
    """
    Demonstrates that the "Position Uniqueness" invariant is NOT enforced at the database level.

    This test highlights that the database schema does not prevent the creation
    of multiple active positions for the same instrument within the same account.
    Such an invariant *should* be enforced by application-level logic. The test
    passes if duplicate active positions can be successfully created, indicating
    the absence of a database constraint.

    Parameters
    ----------
    account_data : dict
        Generated data for an investment account.
    instrument : str
        Generated instrument ticker.
    quantity : float
        Generated quantity for the position.
    market_value : int
        Generated market value for the position in minor units.
    """
    with ledger_connection() as conn:
        # Create an investment account to associate positions with.
        _create_account(conn, account_data)

        # Insert the first position for the instrument.
        conn.execute(
            "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor) VALUES (?, ?, ?, ?, ?)",
            [
                str(uuid4()),
                account_data["account_id"],
                instrument,
                quantity,
                market_value,
            ],
        )

        # Insert a second, duplicate active position for the same instrument within the same account.
        conn.execute(
            "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor) VALUES (?, ?, ?, ?, ?)",
            [
                str(uuid4()),
                account_data["account_id"],
                instrument,
                quantity,
                market_value,
            ],
        )

        # Verify that two active positions now exist, which violates the intended invariant.
        count_row = _fetch_namespace(
            conn,
            "SELECT COUNT(*) AS total_positions FROM positions WHERE account_id = ? AND instrument = ? AND is_active = TRUE",
            [account_data["account_id"], instrument],
        )

        assert count_row.total_positions == 2, (
            "Duplicate active positions were not created, which is unexpected."
        )


@given(
    account_data=non_investment_account_strategy(),
    instrument=instrument_strategy,
    quantity=quantity_strategy,
    market_value=market_value_strategy,
)
@settings(max_examples=10, deadline=None)
def test_account_class_is_not_enforced(
    account_data, instrument, quantity, market_value
):
    """
    Demonstrates that the "Account Class" invariant is NOT enforced at the database level for positions.

    This test highlights that the database schema does not prevent the creation
    of investment positions for accounts that are not of the 'investment' class.
    This invariant *should* be enforced by application-level logic. The test
    passes if a position can be successfully created for a non-investment account,
    indicating the absence of a database constraint.

    Parameters
    ----------
    account_data : dict
        Generated data for a non-investment account.
    instrument : str
        Generated instrument ticker.
    quantity : float
        Generated quantity for the position.
    market_value : int
        Generated market value for the position in minor units.
    """
    with ledger_connection() as conn:
        # Create a non-investment account.
        _create_account(conn, account_data)

        # Attempt to insert an investment position for this non-investment account.
        conn.execute(
            "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor) VALUES (?, ?, ?, ?, ?)",
            [
                str(uuid4()),
                account_data["account_id"],
                instrument,
                quantity,
                market_value,
            ],
        )

        # Verify that the position was created, which violates the intended invariant.
        count_row = _fetch_namespace(
            conn,
            "SELECT COUNT(*) AS total_positions FROM positions WHERE account_id = ?",
            [account_data["account_id"]],
        )

        assert count_row.total_positions == 1, (
            "Position for non-investment account was not created, which is unexpected."
        )
