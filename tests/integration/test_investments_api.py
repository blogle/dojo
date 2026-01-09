from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from dojo.core.app import create_app
from dojo.core.config import Settings
from dojo.core.db import get_connection
from dojo.investments.service import InvestmentService


class _FakeMarketClient:
    def fetch_prices(self, tickers: list[str], start_date: date) -> dict[str, pd.DataFrame]:
        _ = start_date
        out: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            out[ticker.strip().upper()] = pd.DataFrame(
                {
                    "Open": [110.0],
                    "High": [110.0],
                    "Low": [110.0],
                    "Close": [110.0],
                    "Adj Close": [110.0],
                    "Volume": [1000],
                },
                index=pd.to_datetime(["2025-01-15"]),
            )
        return out

    def fetch_metadata(self, ticker: str) -> dict[str, object]:
        _ = ticker
        return {}


@pytest.fixture()
def investment_api_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "investments-api.duckdb"
    if db_path.exists():
        db_path.unlink()

    settings = Settings(
        db_path=db_path,
        run_startup_migrations=True,
        testing=True,
    )
    app = create_app(settings)
    app.state.investment_service = InvestmentService(market_client=_FakeMarketClient())
    return TestClient(app)


def test_investments_api_flow_end_to_end(investment_api_client: TestClient) -> None:
    client = investment_api_client

    # 1) Create accounts.
    resp = client.post(
        "/api/accounts",
        json={
            "account_id": "cash_src",
            "name": "Cash Source",
            "account_type": "asset",
            "account_class": "cash",
            "account_role": "on_budget",
            "current_balance_minor": 0,
            "currency": "USD",
            "opened_on": "2025-01-01",
            "is_active": True,
            "interest_rate_apy": 0.0,
        },
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/transactions",
        json={
            "transaction_date": "2025-01-01",
            "account_id": "cash_src",
            "category_id": "opening_balance",
            "amount_minor": 100000,
            "memo": "Opening balance",
            "status": "cleared",
        },
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/accounts",
        json={
            "account_id": "brokerage_1",
            "name": "Brokerage 1",
            "account_type": "asset",
            "account_class": "investment",
            "account_role": "on_budget",
            "current_balance_minor": 0,
            "currency": "USD",
            "opened_on": "2025-01-01",
            "is_active": True,
            "risk_free_sweep_rate": 0.0,
        },
    )
    assert resp.status_code == 201, resp.text

    # 2) Add ledger cash via transfer in.
    resp = client.post(
        "/api/transfers",
        json={
            "source_account_id": "cash_src",
            "destination_account_id": "brokerage_1",
            "category_id": "account_transfer",
            "amount_minor": 100000,
            "transaction_date": "2025-01-15",
            "memo": "Fund brokerage",
        },
    )
    assert resp.status_code == 201, resp.text

    # 3/4) Reconcile portfolio (cash fully invested) with one position.
    resp = client.post(
        "/api/investments/accounts/brokerage_1/reconcile",
        json={
            "uninvested_cash_minor": 0,
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 10.0,
                    "avg_cost_minor": 10000,
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text

    # 5) Trigger market update (mocked to $110 close).
    resp = client.post("/api/jobs/market-update")
    assert resp.status_code == 202, resp.text

    # Ensure the background task finished and wrote prices.
    with get_connection(client.app.state.settings.db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM market_prices").fetchone()
        assert row is not None
        assert row[0] > 0

    # 6) Verify portfolio state.
    resp = client.get("/api/investments/accounts/brokerage_1")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["ledger_cash_minor"] == 100000
    assert data["uninvested_cash_minor"] == 0
    assert data["holdings_value_minor"] == 110000
    assert data["nav_minor"] == 110000
    assert data["total_return_minor"] == 10000
    assert data["total_return_pct"] == 0.1
