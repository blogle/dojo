from __future__ import annotations

from datetime import date
from uuid import uuid4

import duckdb

from dojo.investments.domain import CreatePositionRequest
from dojo.investments.service import InvestmentService


def test_portfolio_history_reports_daily_nav_and_return(in_memory_db: duckdb.DuckDBPyConnection) -> None:
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
        VALUES ('inv_hist', 'History Account', 'asset', 'investment', 'on_budget', 0, 'USD', TRUE)
        """
    )

    # Ledger cash basis: +$1,000 transfer in on 2025-01-15.
    in_memory_db.execute(
        """
        INSERT INTO transactions (
            transaction_version_id,
            concept_id,
            account_id,
            category_id,
            transaction_date,
            amount_minor,
            memo
        )
        VALUES (?, ?, 'inv_hist', 'opening_balance', DATE '2025-01-15', 100000, 'transfer in')
        """,
        [str(uuid4()), str(uuid4())],
    )

    service = InvestmentService()
    service.reconcile_portfolio(
        in_memory_db,
        "inv_hist",
        uninvested_cash_minor=0,
        positions=[CreatePositionRequest(ticker="AAPL", quantity=10.0, avg_cost_minor=10000)],
    )

    security_row = in_memory_db.execute("SELECT security_id FROM securities WHERE ticker = 'AAPL'").fetchone()
    assert security_row is not None
    security_id = security_row[0]

    in_memory_db.execute(
        """
        INSERT INTO market_prices (security_id, market_date, close_minor, recorded_at)
        VALUES (?, DATE '2025-01-15', 10000, CURRENT_TIMESTAMP)
        """,
        [str(security_id)],
    )
    in_memory_db.execute(
        """
        INSERT INTO market_prices (security_id, market_date, close_minor, recorded_at)
        VALUES (?, DATE '2025-01-16', 11000, CURRENT_TIMESTAMP)
        """,
        [str(security_id)],
    )

    points = service.get_portfolio_history(
        in_memory_db,
        "inv_hist",
        start_date=date(2025, 1, 15),
        end_date=date(2025, 1, 16),
    )

    assert [p.market_date for p in points] == [date(2025, 1, 15), date(2025, 1, 16)]

    assert points[0].nav_minor == 100000
    assert points[0].return_minor == 0
    assert points[0].cash_flow_minor == 0

    assert points[1].nav_minor == 110000
    assert points[1].return_minor == 10000
    assert points[1].cash_flow_minor == 0
