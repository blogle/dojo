"""Investment tracking services (portfolio state, reconciliation, market sync)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from uuid import UUID, uuid4, uuid5

import duckdb
import pandas as pd

from dojo.core import clock
from dojo.investments.dao import InvestmentDAO
from dojo.investments.domain import CreatePositionRequest, PortfolioHistoryPoint, PortfolioState, PositionView
from dojo.investments.market_client import MarketClient
from dojo.investments.sql import load_sql as load_investments_sql

_POSITION_CONCEPT_NAMESPACE = UUID("2f7f9ea4-2fd0-4c21-9bb1-7a5eb5e7a0ac")


def round_half_up_minor(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_market_value_minor(quantity: float, price_minor: int | None) -> int:
    if price_minor is None:
        return 0
    return round_half_up_minor(Decimal(str(quantity)) * Decimal(price_minor))


@dataclass(frozen=True)
class PortfolioTotals:
    holdings_value_minor: int
    nav_minor: int
    total_return_minor: int


def compute_portfolio_totals(
    *,
    ledger_cash_minor: int,
    uninvested_cash_minor: int,
    lots: list[tuple[float, int | None]],
) -> PortfolioTotals:
    holdings_value_minor = sum(compute_market_value_minor(qty, price_minor) for (qty, price_minor) in lots)
    nav_minor = uninvested_cash_minor + holdings_value_minor
    total_return_minor = nav_minor - ledger_cash_minor
    return PortfolioTotals(
        holdings_value_minor=holdings_value_minor,
        nav_minor=nav_minor,
        total_return_minor=total_return_minor,
    )


class InvestmentService:
    def __init__(self, *, market_client: MarketClient | None = None) -> None:
        self._market_client = market_client or MarketClient()

    def get_portfolio_state(self, conn: duckdb.DuckDBPyConnection, account_id: str) -> PortfolioState:
        dao = InvestmentDAO(conn)
        account = dao.require_active_investment_account(account_id)
        uninvested_cash_minor = dao.get_active_uninvested_cash_minor(account_id)
        positions = dao.get_active_positions_with_prices(account_id)

        lots = [(p.quantity, p.close_minor) for p in positions]
        totals = compute_portfolio_totals(
            ledger_cash_minor=account.current_balance_minor,
            uninvested_cash_minor=uninvested_cash_minor,
            lots=lots,
        )

        position_views: list[PositionView] = []
        for p in positions:
            market_value_minor = compute_market_value_minor(p.quantity, p.close_minor)
            cost_basis_minor = round_half_up_minor(Decimal(str(p.quantity)) * Decimal(p.avg_cost_minor))
            gain_minor = market_value_minor - cost_basis_minor
            position_views.append(
                PositionView(
                    security_id=p.security_id,
                    ticker=p.ticker,
                    name=p.name,
                    quantity=p.quantity,
                    avg_cost_minor=p.avg_cost_minor,
                    price_minor=p.close_minor,
                    market_value_minor=market_value_minor,
                    gain_minor=gain_minor,
                )
            )

        total_return_pct: float | None
        if account.current_balance_minor <= 0:
            total_return_pct = None
        else:
            total_return_pct = totals.total_return_minor / account.current_balance_minor

        return PortfolioState(
            account_id=account.account_id,
            ledger_cash_minor=account.current_balance_minor,
            uninvested_cash_minor=uninvested_cash_minor,
            holdings_value_minor=totals.holdings_value_minor,
            nav_minor=totals.nav_minor,
            total_return_minor=totals.total_return_minor,
            total_return_pct=total_return_pct,
            positions=position_views,
        )

    def get_portfolio_history(
        self,
        conn: duckdb.DuckDBPyConnection,
        account_id: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[PortfolioHistoryPoint]:
        dao = InvestmentDAO(conn)
        dao.require_active_investment_account(account_id)

        cursor = conn.execute(
            load_investments_sql("portfolio_history.sql"),
            {
                "account_id": account_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        rows = cursor.fetchall()
        if not rows:
            return []

        columns = [desc[0] for desc in cursor.description or ()]
        points: list[PortfolioHistoryPoint] = []
        for row in rows:
            record = {columns[idx]: row[idx] for idx in range(len(columns))}
            points.append(
                PortfolioHistoryPoint(
                    market_date=record["market_date"],
                    nav_minor=int(record["nav_minor"]),
                    cash_flow_minor=int(record["cash_flow_minor"]),
                    return_minor=int(record["return_minor"]),
                )
            )
        return points

    def reconcile_portfolio(
        self,
        conn: duckdb.DuckDBPyConnection,
        account_id: str,
        *,
        uninvested_cash_minor: int,
        positions: list[CreatePositionRequest],
    ) -> PortfolioState:
        dao = InvestmentDAO(conn)
        dao.require_active_investment_account(account_id)

        recorded_at = clock.now()

        with dao.transaction() as tx:
            tx.scd2_set_uninvested_cash_minor(account_id, uninvested_cash_minor, recorded_at=recorded_at)

            existing = tx.get_active_positions_for_reconcile(account_id)
            existing_by_ticker = {row.ticker.upper(): row for row in existing}
            requested_tickers: set[str] = set()

            for req in positions:
                ticker = req.ticker.strip().upper()
                requested_tickers.add(ticker)
                security = tx.ensure_security(ticker=ticker, recorded_at=recorded_at)
                concept_id = uuid5(_POSITION_CONCEPT_NAMESPACE, f"{account_id}:{security.security_id}")

                current = existing_by_ticker.get(ticker)
                if current is None:
                    tx.insert_position(
                        position_id=uuid4(),
                        concept_id=concept_id,
                        account_id=account_id,
                        security_id=security.security_id,
                        quantity=req.quantity,
                        avg_cost_minor=req.avg_cost_minor,
                        recorded_at=recorded_at,
                    )
                    continue

                if current.quantity == req.quantity and current.avg_cost_minor == req.avg_cost_minor:
                    continue

                tx.close_position(current.position_id, recorded_at=recorded_at)
                tx.insert_position(
                    position_id=uuid4(),
                    concept_id=current.concept_id,
                    account_id=account_id,
                    security_id=current.security_id,
                    quantity=req.quantity,
                    avg_cost_minor=req.avg_cost_minor,
                    recorded_at=recorded_at,
                )

            for current in existing:
                if current.ticker.upper() in requested_tickers:
                    continue
                tx.close_position(current.position_id, recorded_at=recorded_at)

        return self.get_portfolio_state(conn, account_id)

    def sync_market_data(self, conn: duckdb.DuckDBPyConnection) -> int:
        """Fetch and upsert OHLC data for all active tickers.

        Returns the number of upserted (security_id, market_date) rows.
        """

        dao = InvestmentDAO(conn)
        active = dao.list_active_securities_with_last_market_date()
        if not active:
            return 0

        tickers = [row.ticker for row in active]
        start_dates: list[date] = []
        today = date.today()
        default_start = today - timedelta(days=365 * 5)

        for row in active:
            if row.last_market_date is None:
                start_dates.append(default_start)
            else:
                start_dates.append(row.last_market_date + timedelta(days=1))

        start_date = min(start_dates) if start_dates else default_start
        frames = self._market_client.fetch_prices(tickers, start_date=start_date)

        recorded_at = clock.now()

        upsert_rows: list[Mapping[str, object]] = []
        for active_row in active:
            df = frames.get(active_row.ticker)
            if df is None or df.empty:
                continue

            for timestamp, row in df.iterrows():
                market_date = cast(pd.Timestamp, timestamp).date()
                upsert_rows.append(
                    {
                        "security_id": str(active_row.security_id),
                        "market_date": market_date,
                        "open_minor": _to_price_minor(row.get("Open")),
                        "high_minor": _to_price_minor(row.get("High")),
                        "low_minor": _to_price_minor(row.get("Low")),
                        "close_minor": _to_price_minor(row.get("Close")),
                        "adj_close_minor": _to_price_minor(row.get("Adj Close")),
                        "volume": _to_volume(row.get("Volume")),
                        "recorded_at": recorded_at,
                    }
                )

        dao.upsert_market_prices(upsert_rows)
        return len(upsert_rows)


def _to_price_minor(value: float | int | str | None) -> int | None:
    if value is None or bool(pd.isna(value)):
        return None
    return round_half_up_minor(Decimal(str(value)) * Decimal(100))


def _to_volume(value: float | int | str | None) -> int | None:
    if value is None or bool(pd.isna(value)):
        return None
    return int(float(value))
