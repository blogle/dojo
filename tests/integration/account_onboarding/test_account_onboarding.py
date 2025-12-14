"""Integration tests for account onboarding specs."""

from __future__ import annotations

from datetime import date

import duckdb
from fastapi.testclient import TestClient

TEST_HEADERS = {"X-Test-Date": "2025-02-15"}
CURRENT_MONTH = date(2025, 2, 1)


def _create_account(
    client: TestClient,
    *,
    account_id: str,
    account_type: str,
    account_class: str,
    account_role: str,
) -> dict:
    payload = {
        "account_id": account_id,
        "name": f"{account_id}-name",
        "account_type": account_type,
        "account_class": account_class,
        "account_role": account_role,
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
    }
    response = client.post("/api/accounts", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _record_transaction(
    client: TestClient,
    *,
    account_id: str,
    category_id: str,
    amount_minor: int,
    txn_date: date,
) -> dict:
    payload = {
        "transaction_date": txn_date.isoformat(),
        "account_id": account_id,
        "category_id": category_id,
        "amount_minor": amount_minor,
        "status": "cleared",
    }
    response = client.post("/api/transactions", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _ready_to_assign(client: TestClient, month_start: date) -> int:
    response = client.get(
        "/api/budget/ready-to-assign",
        params={"month": month_start.isoformat()},
        headers=TEST_HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()["ready_to_assign_minor"]


def _net_worth_minor(client: TestClient) -> int:
    response = client.get("/api/net-worth/current", headers=TEST_HEADERS)
    assert response.status_code == 200, response.text
    return response.json()["net_worth_minor"]


def _non_system_budget_commitment(conn: duckdb.DuckDBPyConnection) -> int:
    row = conn.execute(
        """
            SELECT COALESCE(SUM(allocated_minor + inflow_minor - activity_minor), 0)
            FROM budget_category_monthly_state s
            INNER JOIN budget_categories c ON c.category_id = s.category_id
            WHERE c.is_system IS NOT TRUE
            """
    ).fetchone()
    return 0 if row is None else int(row[0])


def _fetch_account(client: TestClient, account_id: str) -> dict:
    response = client.get("/api/accounts", headers=TEST_HEADERS)
    assert response.status_code == 200, response.text
    for record in response.json():
        if record["account_id"] == account_id:
            return record
    raise AssertionError(f"account {account_id} not returned")


def test_cash_account_opening_balance_updates_rta(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    opening_amount = 500_000  # $5,000.00
    baseline_rta = _ready_to_assign(api_client, CURRENT_MONTH)
    assert baseline_rta == 0

    _create_account(
        api_client,
        account_id="spec1_cash",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    _record_transaction(
        api_client,
        account_id="spec1_cash",
        category_id="available_to_budget",
        amount_minor=opening_amount,
        txn_date=date(2025, 2, 10),
    )

    account = _fetch_account(api_client, "spec1_cash")
    assert account["current_balance_minor"] == opening_amount

    txn_row = pristine_db.execute(
        "SELECT amount_minor, category_id, is_active FROM transactions WHERE account_id = ?",
        ["spec1_cash"],
    ).fetchone()
    assert txn_row is not None
    assert txn_row[0] == opening_amount
    assert txn_row[1] == "available_to_budget"
    assert txn_row[2] is True

    updated_rta = _ready_to_assign(api_client, CURRENT_MONTH)
    assert updated_rta == opening_amount
    assert _non_system_budget_commitment(pristine_db) == 0
    assert _net_worth_minor(api_client) == opening_amount


def test_credit_card_onboarding_preserves_budget_and_tracks_liability(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    opening_debt = -120_000  # -$1,200.00
    assert _ready_to_assign(api_client, CURRENT_MONTH) == 0

    _create_account(
        api_client,
        account_id="spec1_credit",
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
    )
    _record_transaction(
        api_client,
        account_id="spec1_credit",
        category_id="balance_adjustment",
        amount_minor=opening_debt,
        txn_date=date(2025, 2, 10),
    )

    account = _fetch_account(api_client, "spec1_credit")
    assert account["current_balance_minor"] == opening_debt

    txn_row = pristine_db.execute(
        "SELECT amount_minor, category_id FROM transactions WHERE account_id = ?",
        ["spec1_credit"],
    ).fetchone()
    assert txn_row is not None
    assert txn_row[0] == opening_debt
    assert txn_row[1] == "balance_adjustment"

    assert _ready_to_assign(api_client, CURRENT_MONTH) == 0
    assert _non_system_budget_commitment(pristine_db) == 0
    assert _net_worth_minor(api_client) == opening_debt


def test_tracking_loan_onboarding_isolated_from_budget(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    loan_balance = -35_000_000  # -$350,000.00
    _create_account(
        api_client,
        account_id="spec1_loan",
        account_type="liability",
        account_class="loan",
        account_role="tracking",
    )
    _record_transaction(
        api_client,
        account_id="spec1_loan",
        category_id="balance_adjustment",
        amount_minor=loan_balance,
        txn_date=date(2025, 2, 10),
    )

    account = _fetch_account(api_client, "spec1_loan")
    assert account["account_role"] == "tracking"
    assert account["current_balance_minor"] == loan_balance

    assert _ready_to_assign(api_client, CURRENT_MONTH) == 0
    assert _non_system_budget_commitment(pristine_db) == 0
    assert _net_worth_minor(api_client) == loan_balance


def test_tracking_asset_onboarding_increases_net_worth_without_budget_effect(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    asset_balance = 2_000_000  # $20,000.00
    _create_account(
        api_client,
        account_id="spec1_invest",
        account_type="asset",
        account_class="investment",
        account_role="tracking",
    )
    _record_transaction(
        api_client,
        account_id="spec1_invest",
        category_id="balance_adjustment",
        amount_minor=asset_balance,
        txn_date=date(2025, 2, 10),
    )

    account = _fetch_account(api_client, "spec1_invest")
    assert account["account_class"] == "investment"
    assert account["account_role"] == "tracking"
    assert account["current_balance_minor"] == asset_balance

    assert _ready_to_assign(api_client, CURRENT_MONTH) == 0
    assert _non_system_budget_commitment(pristine_db) == 0
    assert _net_worth_minor(api_client) == asset_balance
