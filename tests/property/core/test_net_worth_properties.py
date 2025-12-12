"""
Property-based tests for net worth aggregation.

This module uses the Hypothesis library to test the `current_snapshot` function
responsible for aggregating net worth. It verifies that the calculated net worth
components (assets, liabilities, positions) and the total net worth match
manual computations based on generated data.
"""

from collections.abc import Generator
from contextlib import contextmanager
from importlib import resources
from uuid import uuid4

import duckdb
from hypothesis import given, settings
from hypothesis import strategies as st

from dojo.core.migrate import apply_migrations
from dojo.core.net_worth import current_snapshot


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Creates an in-memory DuckDB connection and applies all migrations.

    This fixture provides a clean and consistent database state for each test run,
    with only the schema established, allowing tests to insert their own data.

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
    try:
        yield conn
    finally:
        # Ensure the connection is closed after the test completes.
        conn.close()


# Strategies for generating financial amounts in minor units.
assets_strategy = st.lists(st.integers(min_value=0, max_value=2_000_00), min_size=1, max_size=4)
liabilities_strategy = st.lists(st.integers(min_value=0, max_value=1_000_00), min_size=1, max_size=4)
pos_strategy = st.lists(st.integers(min_value=0, max_value=500_00), min_size=0, max_size=3)
account_strategy = st.lists(
    st.tuples(
        st.sampled_from(["asset", "liability"]),
        st.integers(min_value=1_000, max_value=2_000_00),
        st.booleans(),
        st.booleans(),
    ),
    min_size=1,
    max_size=5,
)


@given(
    assets=assets_strategy,
    liabilities=liabilities_strategy,
    positions=pos_strategy,
)
@settings(max_examples=20, deadline=None)
def test_net_worth_matches_manual_computation(
    assets: list[int],
    liabilities: list[int],
    positions: list[int],
) -> None:
    """
    Verifies that the `current_snapshot` function accurately calculates net worth.

    This property test generates various combinations of assets, liabilities,
    and investment positions. It then populates the database with this data
    and asserts that the `NetWorthSnapshot` returned by `current_snapshot`
    matches the sum of generated values.

    Parameters
    ----------
    assets : list[int]
        A list of generated asset amounts in minor units.
    liabilities : list[int]
        A list of generated liability amounts in minor units.
    positions : list[int]
        A list of generated investment position values in minor units.
    """
    with ledger_connection() as conn:
        # Clear existing data to ensure a clean state for each test run.
        conn.execute("DELETE FROM positions")
        conn.execute("DELETE FROM tangible_assets")
        conn.execute("DELETE FROM cash_account_details")
        conn.execute("DELETE FROM credit_account_details")
        conn.execute("DELETE FROM accessible_asset_details")
        conn.execute("DELETE FROM investment_account_details")
        conn.execute("DELETE FROM loan_account_details")
        conn.execute("DELETE FROM tangible_asset_details")
        conn.execute("DELETE FROM accounts")

        # Insert generated asset accounts.
        for idx, value in enumerate(assets):
            conn.execute(
                """
                INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active)
                VALUES (?, ?, 'asset', ?, 'USD', TRUE)
                """,
                [f"asset_{idx}", f"Asset {idx}", value],
            )
        # Insert generated liability accounts.
        for idx, value in enumerate(liabilities):
            conn.execute(
                """
                INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active)
                VALUES (?, ?, 'liability', ?, 'USD', TRUE)
                """,
                [f"liability_{idx}", f"Liability {idx}", -value],
            )
        # Insert generated investment positions.
        for value in positions:
            # Assuming 'asset_0' exists from the assets loop, or create a dummy one.
            conn.execute(
                """
                INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor, is_active)
                VALUES (?, 'asset_0', ?, 1.0, ?, TRUE)
                """,
                [str(uuid4()), "TICK", value],
            )

        # Retrieve the net worth snapshot.
        snapshot = current_snapshot(conn)
        # Assert that the snapshot values match the sum of the generated inputs.
        assert snapshot.assets_minor == sum(assets)
        assert snapshot.liabilities_minor == -sum(liabilities)
        assert snapshot.positions_minor == sum(positions)
        # Net worth is calculated as Assets - Liabilities + Positions.
        assert snapshot.net_worth_minor == sum(assets) - sum(liabilities) + sum(positions)


@given(accounts=account_strategy)
@settings(max_examples=15, deadline=None)
def test_net_worth_equation_respects_account_activation(accounts: list[tuple[str, int, bool, bool]]) -> None:
    """Spec 7.3: Assets/liabilities equation holds even when accounts toggle active state."""
    with ledger_connection() as conn:
        conn.execute("DELETE FROM accounts")
        for idx, (account_type, amount, is_tracking, is_active) in enumerate(accounts):
            balance = amount if account_type == "asset" else -amount
            conn.execute(
                """
                INSERT INTO accounts (
                    account_id, name, account_type, current_balance_minor,
                    currency, is_active, account_class, account_role
                )
                VALUES (?, ?, ?, ?, 'USD', ?, ?, ?)
                """,
                [
                    f"acct_{idx}",
                    f"Account {idx}",
                    account_type,
                    balance,
                    is_active,
                    "cash" if account_type == "asset" else "credit",
                    "tracking" if is_tracking else "on_budget",
                ],
            )

        snapshot = current_snapshot(conn)
        rows = conn.execute(
            "SELECT account_type, current_balance_minor, is_active FROM accounts",
        ).fetchall()
        manual_assets = sum(row[1] for row in rows if row[0] == "asset" and row[2])
        manual_liabilities = sum(row[1] for row in rows if row[0] == "liability" and row[2])
        expected_net_worth = manual_assets + manual_liabilities

        assert snapshot.assets_minor == manual_assets
        assert snapshot.liabilities_minor == manual_liabilities
        assert snapshot.net_worth_minor == expected_net_worth + snapshot.positions_minor + snapshot.tangibles_minor
