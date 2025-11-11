"""Property-based tests for net worth aggregation."""

from contextlib import contextmanager
from importlib import resources
from uuid import uuid4

import duckdb
from hypothesis import given, settings, strategies as st

from dojo.core.migrate import apply_migrations
from dojo.core.net_worth import current_snapshot


@contextmanager
def ledger_connection() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    try:
        yield conn
    finally:
        conn.close()


assets_strategy = st.lists(st.integers(min_value=0, max_value=2_000_00), min_size=1, max_size=4)
liabilities_strategy = st.lists(st.integers(min_value=0, max_value=1_000_00), min_size=1, max_size=4)
pos_strategy = st.lists(st.integers(min_value=0, max_value=500_00), min_size=0, max_size=3)


@given(
    assets=assets_strategy,
    liabilities=liabilities_strategy,
    positions=pos_strategy,
)
@settings(max_examples=20)
def test_net_worth_matches_manual_computation(
    assets: list[int],
    liabilities: list[int],
    positions: list[int],
) -> None:
    with ledger_connection() as conn:
        conn.execute("DELETE FROM accounts")
        conn.execute("DELETE FROM positions")

        for idx, value in enumerate(assets):
            conn.execute(
                """
                INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active)
                VALUES (?, ?, 'asset', ?, 'USD', TRUE)
                """,
                [f"asset_{idx}", f"Asset {idx}", value],
            )
        for idx, value in enumerate(liabilities):
            conn.execute(
                """
                INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active)
                VALUES (?, ?, 'liability', ?, 'USD', TRUE)
                """,
                [f"liability_{idx}", f"Liability {idx}", value],
            )
        for value in positions:
            conn.execute(
                """
                INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor, is_active)
                VALUES (?, 'asset_0', ?, 1.0, ?, TRUE)
                """,
                [str(uuid4()), "TICK", value],
            )

        snapshot = current_snapshot(conn)
        assert snapshot.assets_minor == sum(assets)
        assert snapshot.liabilities_minor == sum(liabilities)
        assert snapshot.positions_minor == sum(positions)
        assert snapshot.net_worth_minor == sum(assets) - sum(liabilities) + sum(positions)
