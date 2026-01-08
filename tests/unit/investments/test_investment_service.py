from __future__ import annotations

from uuid import UUID

import duckdb

from dojo.investments.domain import CreatePositionRequest
from dojo.investments.service import InvestmentService


def _create_investment_account(
    conn: duckdb.DuckDBPyConnection,
    *,
    account_id: str,
    ledger_cash_minor: int,
) -> None:
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
            is_active
        )
        VALUES (?, ?, 'asset', 'investment', 'on_budget', ?, 'USD', TRUE)
        """,
        [account_id, f"Investment {account_id}", ledger_cash_minor],
    )
    conn.execute(
        """
        INSERT INTO investment_account_details (detail_id, account_id, uninvested_cash_minor, is_active)
        VALUES (uuid(), ?, 0, TRUE)
        """,
        [account_id],
    )


def test_reconcile_position_updates_scd2_rows(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    _create_investment_account(in_memory_db, account_id="inv_scd2", ledger_cash_minor=0)

    service = InvestmentService()

    service.reconcile_portfolio(
        in_memory_db,
        "inv_scd2",
        uninvested_cash_minor=0,
        positions=[CreatePositionRequest(ticker="AAPL", quantity=10.0, avg_cost_minor=10000)],
    )
    service.reconcile_portfolio(
        in_memory_db,
        "inv_scd2",
        uninvested_cash_minor=0,
        positions=[CreatePositionRequest(ticker="AAPL", quantity=12.0, avg_cost_minor=10000)],
    )

    rows = in_memory_db.execute(
        """
        SELECT p.concept_id, p.is_active, p.valid_to
        FROM positions p
        JOIN securities s ON s.security_id = p.security_id
        WHERE p.account_id = 'inv_scd2' AND s.ticker = 'AAPL'
        ORDER BY p.valid_from
        """
    ).fetchall()

    assert len(rows) == 2
    assert UUID(str(rows[0][0])) == UUID(str(rows[1][0]))
    assert rows[0][1] is False
    assert str(rows[0][2]) != "9999-12-31 00:00:00"
    assert rows[1][1] is True


def test_reconcile_implicit_liquidation_closes_missing_positions(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    _create_investment_account(in_memory_db, account_id="inv_liq", ledger_cash_minor=0)

    service = InvestmentService()

    service.reconcile_portfolio(
        in_memory_db,
        "inv_liq",
        uninvested_cash_minor=0,
        positions=[CreatePositionRequest(ticker="AAPL", quantity=1.0, avg_cost_minor=10000)],
    )
    service.reconcile_portfolio(
        in_memory_db,
        "inv_liq",
        uninvested_cash_minor=0,
        positions=[],
    )

    row = in_memory_db.execute(
        """
        SELECT COUNT(*)
        FROM positions
        WHERE account_id = 'inv_liq' AND is_active = TRUE
        """
    ).fetchone()
    assert row is not None

    count_active = row[0]
    assert count_active == 0


def test_nav_calculation_matches_spec(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    _create_investment_account(in_memory_db, account_id="inv_nav", ledger_cash_minor=100_000)

    service = InvestmentService()

    # Reconcile holdings (no prices yet).
    service.reconcile_portfolio(
        in_memory_db,
        "inv_nav",
        uninvested_cash_minor=0,
        positions=[CreatePositionRequest(ticker="AAPL", quantity=10.0, avg_cost_minor=10000)],
    )

    security_row = in_memory_db.execute("SELECT security_id FROM securities WHERE ticker = 'AAPL'").fetchone()
    assert security_row is not None
    security_id = security_row[0]
    in_memory_db.execute(
        """
        INSERT INTO market_prices (security_id, market_date, close_minor, recorded_at)
        VALUES (?, DATE '2025-01-02', 11000, CURRENT_TIMESTAMP)
        """,
        [str(security_id)],
    )

    state = service.get_portfolio_state(in_memory_db, "inv_nav")
    assert state.holdings_value_minor == 110_000
    assert state.nav_minor == 110_000
    assert state.total_return_minor == 10_000
    assert state.total_return_pct == 0.1
