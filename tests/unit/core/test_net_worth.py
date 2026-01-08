"""
Unit tests for net worth aggregation.

This module contains unit tests that verify the correct calculation and
aggregation of net worth components by the `current_snapshot` function,
ensuring that account balances, investment positions, and tangible assets
are accurately reflected in the overall net worth.
"""

from decimal import Decimal

import duckdb

from dojo.core.net_worth import current_snapshot


def test_current_snapshot_reflects_accounts_and_positions(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that the `current_snapshot` function accurately aggregates net worth
    from various financial components including accounts, positions, and tangible assets.

    This test inserts a test position and a tangible asset, then asserts that
    the calculated `NetWorthSnapshot` correctly sums these values along with
    existing account balances.

    Parameters
    ----------
    in_memory_db : duckdb.DuckDBPyConnection
        An in-memory DuckDB connection with base fixtures applied.
    """
    # Insert an investment account and model its valuation via securities + prices + positions.
    in_memory_db.execute(
        """
        INSERT INTO accounts (
            account_id,
            name,
            account_type,
            account_class,
            account_role,
            current_balance_minor,
            currency,
            is_active
        )
        VALUES ('brokerage_test', 'Brokerage Test', 'asset', 'investment', 'on_budget', 0, 'USD', TRUE)
        """
    )
    in_memory_db.execute(
        """
        INSERT INTO investment_account_details (detail_id, account_id, uninvested_cash_minor, is_active)
        VALUES ('00000000-0000-0000-0000-000000000010', 'brokerage_test', 0, TRUE)
        """
    )

    in_memory_db.execute(
        """
        INSERT INTO securities (security_id, ticker, name, type, currency)
        VALUES ('00000000-0000-0000-0000-000000000011', 'SPY', 'SPY', 'ETF', 'USD')
        """
    )
    in_memory_db.execute(
        """
        INSERT INTO market_prices (security_id, market_date, close_minor, recorded_at)
        VALUES ('00000000-0000-0000-0000-000000000011', DATE '2025-01-01', 250000, CURRENT_TIMESTAMP)
        """
    )
    in_memory_db.execute(
        """
        INSERT INTO positions (
            position_id,
            concept_id,
            account_id,
            security_id,
            quantity,
            avg_cost_minor,
            is_active
        )
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000012',
            'brokerage_test',
            '00000000-0000-0000-0000-000000000011',
            1.0,
            0,
            TRUE
        )
        """
    )
    # Insert a test tangible asset.
    in_memory_db.execute(
        "INSERT INTO tangible_assets (tangible_id, account_id, asset_name, current_fair_value_minor, is_active) "
        "VALUES ('00000000-0000-0000-0000-000000000002', 'house_savings', 'Family Home', 850000, TRUE)"
    )

    # Get the current net worth snapshot.
    snapshot = current_snapshot(in_memory_db)
    # Assert total assets (initial checking + savings from base_budgeting.sql).
    assert snapshot.assets_minor == 500000 + 1_250_000
    # Assert total liabilities (from base_budgeting.sql).
    assert snapshot.liabilities_minor == -250000
    # Assert total positions (the newly inserted position).
    assert snapshot.positions_minor == 250000
    # Assert total tangibles (the newly inserted tangible asset).
    assert snapshot.tangibles_minor == 850000
    # Assert calculated net worth matches the sum of assets + positions + tangibles - liabilities.
    assert snapshot.net_worth_minor == (
        snapshot.assets_minor + snapshot.liabilities_minor + snapshot.positions_minor + snapshot.tangibles_minor
    )
    assert snapshot.net_worth_decimal == Decimal(snapshot.net_worth_minor).scaleb(-2).quantize(Decimal("0.01"))
