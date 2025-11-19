"""Unit tests for net worth aggregation."""

from decimal import Decimal

import duckdb

from dojo.core.net_worth import current_snapshot


def test_current_snapshot_reflects_accounts_and_positions(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    in_memory_db.execute(
        "INSERT INTO positions (position_id, account_id, instrument, quantity, market_value_minor, is_active) "
        "VALUES ('00000000-0000-0000-0000-000000000001', 'house_checking', 'SPY', 1.0, 250000, TRUE)"
    )
    in_memory_db.execute(
        "INSERT INTO tangible_assets (tangible_id, account_id, asset_name, current_fair_value_minor, is_active) "
        "VALUES ('00000000-0000-0000-0000-000000000002', 'house_savings', 'Family Home', 850000, TRUE)"
    )

    snapshot = current_snapshot(in_memory_db)
    assert snapshot.assets_minor == 500000 + 1_250_000  # checking + savings
    assert snapshot.liabilities_minor == 250000
    assert snapshot.positions_minor == 250000
    assert snapshot.tangibles_minor == 850000
    assert snapshot.net_worth_minor == (
        snapshot.assets_minor - snapshot.liabilities_minor + snapshot.positions_minor + snapshot.tangibles_minor
    )
    assert snapshot.net_worth_decimal == Decimal(snapshot.net_worth_minor).scaleb(-2).quantize(Decimal("0.01"))
