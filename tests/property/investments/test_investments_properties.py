"""Property-based tests for investment service invariants."""

import string
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace
import duckdb
from uuid import uuid4

from hypothesis import given, settings, strategies as st

from dojo.budgeting.schemas import AccountClass
from dojo.budgeting.services import AccountAdminService
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create an in-memory DuckDB connection with all migrations and base fixtures applied."""
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    apply_base_budgeting_fixture(conn)
    try:
        yield conn
    finally:
        conn.close()


def build_account_admin_service() -> AccountAdminService:
    return AccountAdminService()


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


# Strategies
account_id_strategy = st.text(
    min_size=3, max_size=20, alphabet=string.ascii_lowercase + string.digits + "_"
)
instrument_strategy = st.text(min_size=1, max_size=5, alphabet=string.ascii_uppercase)
quantity_strategy = st.floats(min_value=0.1, max_value=1000.0)
market_value_strategy = st.integers(min_value=1, max_value=1_000_000_00)


@st.composite
def investment_account_strategy(draw):
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
    non_investment_class = draw(st.sampled_from([c for c in AccountClass.__args__ if c != "investment"]))
    account_type = "liability" if non_investment_class in ["credit", "loan"] else "asset"
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


def _create_account(conn, account_data):
    # Manually create account and details since service doesn't handle it
    conn.execute(
        """
        INSERT INTO accounts (account_id, name, account_type, account_class, account_role, current_balance_minor, currency, is_active, opened_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        list(account_data.values()),
    )
    detail_table = f"{account_data['account_class']}_account_details"
    if account_data['account_class'] in ['cash', 'credit', 'investment', 'loan']:
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
def test_position_uniqueness_is_not_enforced(account_data, instrument, quantity, market_value):
    """
    This test demonstrates that the "Position Uniqueness" invariant is NOT
    enforced at the database level. It should be enforced by application logic,
    which appears to be missing. The test passes if duplicate active positions
    can be created.
    """
    with ledger_connection() as conn:
        _create_account(conn, account_data)
        
        # Insert the first position
        conn.execute(
            "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor) VALUES (?, ?, ?, ?, ?)",
            [str(uuid4()), account_data["account_id"], instrument, quantity, market_value],
        )
        
        # Insert a second, duplicate active position for the same instrument
        conn.execute(
            "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor) VALUES (?, ?, ?, ?, ?)",
            [str(uuid4()), account_data["account_id"], instrument, quantity, market_value],
        )
        
        # Verify that two active positions now exist, which violates the invariant
        count_row = _fetch_namespace(
            conn,
            "SELECT COUNT(*) AS total_positions FROM positions WHERE account_id = ? AND instrument = ? AND is_active = TRUE",
            [account_data["account_id"], instrument],
        )
        
        assert count_row.total_positions == 2, "Duplicate active positions were not created, which is unexpected."


@given(
    account_data=non_investment_account_strategy(),
    instrument=instrument_strategy,
    quantity=quantity_strategy,
    market_value=market_value_strategy,
)
@settings(max_examples=10, deadline=None)
def test_account_class_is_not_enforced(account_data, instrument, quantity, market_value):
    """
    This test demonstrates that the "Account Class" invariant is NOT
    enforced at the database level. It should be enforced by application logic.
    The test passes if a position can be created for a non-investment account.
    """
    with ledger_connection() as conn:
        _create_account(conn, account_data)

        # Attempt to insert a position for a non-investment account
        conn.execute(
            "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor) VALUES (?, ?, ?, ?, ?)",
            [str(uuid4()), account_data["account_id"], instrument, quantity, market_value],
        )

        # Verify that the position was created, which violates the invariant
        count_row = _fetch_namespace(
            conn,
            "SELECT COUNT(*) AS total_positions FROM positions WHERE account_id = ?",
            [account_data["account_id"]],
        )

        assert count_row.total_positions == 1, "Position for non-investment account was not created, which is unexpected."
