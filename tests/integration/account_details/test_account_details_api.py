from __future__ import annotations

from datetime import date

import duckdb
import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import (  # type: ignore[import]
    FEBRUARY_2025,
    TEST_HEADERS,
    fetch_account,
    fund_ready_to_assign,
    ready_to_assign,
)

FEBRUARY = FEBRUARY_2025


def _create_account_extended(client: TestClient, **kwargs: object) -> dict:
    payload = {
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
        **kwargs,
    }
    response = client.post("/api/accounts", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _post_transaction(client: TestClient, *, account_id: str, txn_date: date, amount_minor: int, status: str) -> None:
    response = client.post(
        "/api/transactions",
        json={
            "transaction_date": txn_date.isoformat(),
            "account_id": account_id,
            "category_id": "account_transfer",
            "amount_minor": amount_minor,
            "memo": "test",
            "status": status,
        },
        headers=TEST_HEADERS,
    )
    assert response.status_code == 201, response.text


def test_account_details_get_account_returns_class_specific_details(api_client: TestClient) -> None:
    cash_id = "detail_cash"
    accessible_id = "detail_accessible"
    credit_id = "detail_credit"
    loan_id = "detail_loan"
    tangible_id = "detail_tangible"
    investment_id = "detail_investment"

    _create_account_extended(
        api_client,
        account_id=cash_id,
        name="Main Checking",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
        institution_name="Chase",
        interest_rate_apy=0.015,
    )
    _create_account_extended(
        api_client,
        account_id=accessible_id,
        name="CD",
        account_type="asset",
        account_class="accessible",
        account_role="tracking",
        institution_name="Ally",
        interest_rate_apy=0.04,
        term_end_date="2026-01-01",
        early_withdrawal_penalty=True,
    )
    _create_account_extended(
        api_client,
        account_id=credit_id,
        name="Gold Card",
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
        institution_name="Amex",
        card_type="American Express",
        apr=24.99,
        cash_advance_apr=29.99,
    )
    _create_account_extended(
        api_client,
        account_id=loan_id,
        name="Mortgage",
        account_type="liability",
        account_class="loan",
        account_role="tracking",
        institution_name="Wells Fargo",
        initial_principal_minor=50000000,
        interest_rate_apy=6.5,
        mortgage_escrow_details="Includes taxes",
    )
    _create_account_extended(
        api_client,
        account_id=tangible_id,
        name="Car",
        account_type="asset",
        account_class="tangible",
        account_role="tracking",
        asset_name="2018 Honda Civic",
        acquisition_cost_minor=1800000,
    )
    _create_account_extended(
        api_client,
        account_id=investment_id,
        name="Brokerage",
        account_type="asset",
        account_class="investment",
        account_role="tracking",
        institution_name="Fidelity",
        risk_free_sweep_rate=4.5,
        is_self_directed=True,
        tax_classification="Taxable Brokerage",
    )

    cash = api_client.get(f"/api/accounts/{cash_id}", headers=TEST_HEADERS)
    assert cash.status_code == 200, cash.text
    payload = cash.json()
    assert payload["account_id"] == cash_id
    assert payload["account_class"] == "cash"
    assert payload["institution_name"] == "Chase"
    assert payload["details"]["interest_rate_apy"] == 0.015

    accessible = api_client.get(f"/api/accounts/{accessible_id}", headers=TEST_HEADERS)
    assert accessible.status_code == 200, accessible.text
    payload = accessible.json()
    assert payload["account_class"] == "accessible"
    assert payload["details"]["interest_rate_apy"] == 0.04
    assert payload["details"]["term_end_date"] == "2026-01-01"
    assert payload["details"]["early_withdrawal_penalty"] is True

    credit = api_client.get(f"/api/accounts/{credit_id}", headers=TEST_HEADERS)
    assert credit.status_code == 200, credit.text
    payload = credit.json()
    assert payload["account_type"] == "liability"
    assert payload["details"]["card_type"] == "American Express"
    assert payload["details"]["apr"] == 24.99

    loan = api_client.get(f"/api/accounts/{loan_id}", headers=TEST_HEADERS)
    assert loan.status_code == 200, loan.text
    payload = loan.json()
    assert payload["account_class"] == "loan"
    assert payload["details"]["initial_principal_minor"] == 50000000
    assert payload["details"]["mortgage_escrow_details"] == "Includes taxes"

    tangible = api_client.get(f"/api/accounts/{tangible_id}", headers=TEST_HEADERS)
    assert tangible.status_code == 200, tangible.text
    payload = tangible.json()
    assert payload["account_class"] == "tangible"
    assert payload["details"]["asset_name"] == "2018 Honda Civic"
    assert payload["details"]["acquisition_cost_minor"] == 1800000

    investment = api_client.get(f"/api/accounts/{investment_id}", headers=TEST_HEADERS)
    assert investment.status_code == 200, investment.text
    payload = investment.json()
    assert payload["account_class"] == "investment"
    assert payload["details"]["is_self_directed"] is True
    assert payload["details"]["tax_classification"] == "Taxable Brokerage"


def test_account_details_transactions_endpoint_filters_and_status(api_client: TestClient) -> None:
    acct_a = "detail_tx_a"
    acct_b = "detail_tx_b"
    _create_account_extended(
        api_client,
        account_id=acct_a,
        name="A",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    _create_account_extended(
        api_client,
        account_id=acct_b,
        name="B",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )

    _post_transaction(api_client, account_id=acct_a, txn_date=date(2025, 2, 14), amount_minor=1000, status="cleared")
    _post_transaction(api_client, account_id=acct_a, txn_date=date(2025, 2, 14), amount_minor=-250, status="pending")
    _post_transaction(api_client, account_id=acct_b, txn_date=date(2025, 2, 14), amount_minor=500, status="cleared")

    resp = api_client.get(f"/api/accounts/{acct_a}/transactions", headers=TEST_HEADERS)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows
    assert all(row["account_id"] == acct_a for row in rows)
    assert {row["status"] for row in rows} == {"pending", "cleared"}

    resp = api_client.get(
        f"/api/accounts/{acct_a}/transactions",
        params={"status": "cleared"},
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows
    assert all(row["account_id"] == acct_a for row in rows)
    assert {row["status"] for row in rows} == {"cleared"}


def test_account_details_history_is_absolute_series_and_status_filtered(
    api_client: TestClient,
) -> None:
    account_id = "detail_hist"
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="History",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )

    response = api_client.post(
        "/api/transactions",
        json={
            "transaction_date": "2025-02-01",
            "account_id": account_id,
            "category_id": "opening_balance",
            "amount_minor": 1000,
            "memo": "Opening",
            "status": "cleared",
        },
        headers=TEST_HEADERS,
    )
    assert response.status_code == 201, response.text

    _post_transaction(api_client, account_id=account_id, txn_date=date(2025, 2, 11), amount_minor=200, status="pending")
    _post_transaction(api_client, account_id=account_id, txn_date=date(2025, 2, 11), amount_minor=300, status="cleared")

    resp = api_client.get(
        f"/api/accounts/{account_id}/history",
        params={"start_date": "2025-02-10", "end_date": "2025-02-12"},
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    points = resp.json()
    assert [p["as_of_date"] for p in points] == ["2025-02-10", "2025-02-11", "2025-02-12"]
    assert [p["balance_minor"] for p in points] == [1000, 1500, 1500]

    resp = api_client.get(
        f"/api/accounts/{account_id}/history",
        params={"start_date": "2025-02-10", "end_date": "2025-02-12", "status": "cleared"},
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    points = resp.json()
    assert [p["balance_minor"] for p in points] == [1000, 1300, 1300]


def test_account_details_history_enforces_balance_continuity(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    account_id = "detail_continuity"
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="Continuity",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )

    response = api_client.post(
        "/api/transactions",
        json={
            "transaction_date": "2025-02-15",
            "account_id": account_id,
            "category_id": "opening_balance",
            "amount_minor": 5000,
            "memo": "Opening",
            "status": "cleared",
        },
        headers=TEST_HEADERS,
    )
    assert response.status_code == 201, response.text

    acct = fetch_account(api_client, account_id)
    assert acct["current_balance_minor"] == 5000

    resp = api_client.get(
        f"/api/accounts/{account_id}/history",
        params={"start_date": "2025-02-15", "end_date": "2025-02-15"},
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    points = resp.json()
    assert points[-1]["balance_minor"] == 5000

    pristine_db.execute(
        "UPDATE accounts SET current_balance_minor = 0 WHERE account_id = ?",
        [account_id],
    )

    resp = api_client.get(
        f"/api/accounts/{account_id}/history",
        params={"start_date": "2025-02-15", "end_date": "2025-02-15"},
        headers=TEST_HEADERS,
    )
    assert resp.status_code == 409


def test_account_details_tangible_balance_adjustment_does_not_change_ready_to_assign(
    api_client: TestClient,
) -> None:
    cash_account = "detail_tangible_cash"
    tangible_account = "detail_tangible_asset"

    _create_account_extended(
        api_client,
        account_id=cash_account,
        name="Cash",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    _create_account_extended(
        api_client,
        account_id=tangible_account,
        name="Car",
        account_type="asset",
        account_class="tangible",
        account_role="tracking",
        asset_name="Car",
        acquisition_cost_minor=1500000,
    )

    fund_ready_to_assign(
        api_client,
        account_id=cash_account,
        amount_minor=50_000,
        txn_date=date(2025, 2, 1),
    )

    rta_before = ready_to_assign(api_client, FEBRUARY)

    response = api_client.post(
        "/api/transactions",
        json={
            "transaction_date": "2025-02-15",
            "account_id": tangible_account,
            "category_id": "balance_adjustment",
            "amount_minor": 1_000_000,
            "memo": "Valuation update",
            "status": "cleared",
        },
        headers=TEST_HEADERS,
    )
    assert response.status_code == 201, response.text

    assert ready_to_assign(api_client, FEBRUARY) == rta_before

    acct = fetch_account(api_client, tangible_account)
    assert acct["current_balance_minor"] == 1_000_000
