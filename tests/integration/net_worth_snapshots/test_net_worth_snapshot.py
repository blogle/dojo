"""Integration tests for net worth snapshot specs."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
from fastapi.testclient import TestClient

from tests.integration.helpers import (  # type: ignore[import]
    create_account,
    record_transaction,
)

SNAPSHOT_DATE = date(2025, 2, 5)


def _set_balance(client: TestClient, account_id: str, amount_minor: int) -> None:
    record_transaction(
        client,
        account_id=account_id,
        category_id="balance_adjustment",
        amount_minor=amount_minor,
        txn_date=SNAPSHOT_DATE,
    )


def _current_net_worth(client: TestClient) -> dict:
    response = client.get("/api/net-worth/current")
    assert response.status_code == 200, response.text
    return response.json()


def test_snapshot_includes_tracking_assets_and_sums_classes(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 7.1 — assets/liabilities arrays aggregate every active account regardless of role."""

    cash_account = "snapshot_cash"
    tracking_asset = "snapshot_tracking_asset"
    credit_account = "snapshot_credit"
    loan_account = "snapshot_loan"

    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=tracking_asset,
        account_type="asset",
        account_class="accessible",
        account_role="tracking",
    )
    create_account(
        api_client,
        account_id=credit_account,
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=loan_account,
        account_type="liability",
        account_class="loan",
        account_role="tracking",
    )

    _set_balance(api_client, account_id=cash_account, amount_minor=100_000)
    _set_balance(api_client, account_id=tracking_asset, amount_minor=40_000)
    _set_balance(api_client, account_id=credit_account, amount_minor=-15_000)
    _set_balance(api_client, account_id=loan_account, amount_minor=-50_000)

    snapshot = _current_net_worth(api_client)
    assert snapshot["assets_minor"] == 140_000
    assert snapshot["liabilities_minor"] == -65_000
    assert snapshot["positions_minor"] == 0
    assert snapshot["tangibles_minor"] == 0
    assert snapshot["net_worth_minor"] == 75_000

    # Double-check the DAO layer pulls the same totals directly from the database.
    row = pristine_db.execute(
        "SELECT SUM(current_balance_minor) FROM accounts WHERE account_type = 'asset' AND is_active = TRUE"
    ).fetchone()
    assert row == (140_000,)


def test_inactive_accounts_are_excluded_from_current_snapshot(api_client: TestClient) -> None:
    """Spec 7.2 — deactivating an account removes it from the live net worth feed."""

    cash_account = "inactive_cash"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    _set_balance(api_client, account_id=cash_account, amount_minor=30_000)

    snapshot = _current_net_worth(api_client)
    assert snapshot["assets_minor"] == 30_000

    response = api_client.delete(f"/api/accounts/{cash_account}")
    assert response.status_code == 204, response.text

    after = _current_net_worth(api_client)
    assert after["assets_minor"] == 0
    assert after["net_worth_minor"] == 0


def test_net_worth_history_endpoint_returns_daily_series(api_client: TestClient) -> None:
    today = date.today()
    response = api_client.get("/api/net-worth/history", params={"interval": "1W"})
    assert response.status_code == 200, response.text

    points = response.json()
    assert points, "expected at least one history point"
    assert points[0]["date"] == (today - timedelta(days=7)).isoformat()
    assert points[-1]["date"] == today.isoformat()

    dates = [point["date"] for point in points]
    assert dates == sorted(dates)


def test_net_worth_history_last_point_matches_current(api_client: TestClient) -> None:
    today = date.today()

    history = api_client.get("/api/net-worth/history", params={"interval": "1D"})
    assert history.status_code == 200, history.text
    points = history.json()
    assert points[-1]["date"] == today.isoformat()

    current = api_client.get("/api/net-worth/current")
    assert current.status_code == 200, current.text
    assert points[-1]["value_minor"] == current.json()["net_worth_minor"]
