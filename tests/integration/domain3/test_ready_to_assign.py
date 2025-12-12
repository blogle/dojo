"""Integration tests for Domain 3 Ready-to-Assign specs."""

from __future__ import annotations

from datetime import date

import duckdb
from fastapi.testclient import TestClient

TEST_HEADERS = {"X-Test-Date": "2025-02-15"}
JANUARY = date(2025, 1, 1)
FEBRUARY = date(2025, 2, 1)


def _create_cash_account(client: TestClient, account_id: str) -> dict:
    payload = {
        "account_id": account_id,
        "name": f"{account_id}-cash",
        "account_type": "asset",
        "account_class": "cash",
        "account_role": "on_budget",
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
    }
    response = client.post("/api/accounts", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _record_income(
    client: TestClient,
    *,
    account_id: str,
    amount_minor: int,
    txn_date: date,
) -> dict:
    payload = {
        "transaction_date": txn_date.isoformat(),
        "account_id": account_id,
        "category_id": "available_to_budget",
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


def _create_category(client: TestClient, category_id: str, name: str) -> dict:
    payload = {
        "category_id": category_id,
        "name": name,
        "group_id": None,
        "is_active": True,
    }
    response = client.post("/api/budget-categories", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _allocate_from_rta(
    client: TestClient,
    *,
    category_id: str,
    month_start: date,
    amount_minor: int,
) -> dict:
    payload = {
        "to_category_id": category_id,
        "amount_minor": amount_minor,
        "month_start": month_start.isoformat(),
    }
    response = client.post("/api/budget/allocations", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _list_categories(client: TestClient, month_start: date) -> list[dict]:
    response = client.get(
        "/api/budget-categories",
        params={"month": month_start.isoformat()},
        headers=TEST_HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _fetch_account(client: TestClient, account_id: str) -> dict:
    response = client.get("/api/accounts", headers=TEST_HEADERS)
    assert response.status_code == 200, response.text
    for record in response.json():
        if record["account_id"] == account_id:
            return record
    raise AssertionError(f"account {account_id} missing from /api/accounts")


def _perform_transfer(
    client: TestClient,
    *,
    source_account_id: str,
    destination_account_id: str,
    amount_minor: int,
    txn_date: date,
) -> dict:
    payload = {
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
        "category_id": "account_transfer",
        "amount_minor": amount_minor,
        "transaction_date": txn_date.isoformat(),
        "memo": "domain3-transfer",
    }
    response = client.post("/api/transfers", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def test_income_transaction_increases_ready_to_assign_and_net_worth(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    _create_cash_account(api_client, "domain3_income")
    baseline_rta = _ready_to_assign(api_client, FEBRUARY)
    income = 200_000

    _record_income(api_client, account_id="domain3_income", amount_minor=income, txn_date=date(2025, 2, 10))

    updated_rta = _ready_to_assign(api_client, FEBRUARY)
    assert updated_rta - baseline_rta == income

    account = _fetch_account(api_client, "domain3_income")
    assert account["current_balance_minor"] == income
    assert _net_worth_minor(api_client) == income

    non_system_rows = pristine_db.execute(
        (
            """
            SELECT COUNT(*) FROM budget_category_monthly_state s
            INNER JOIN budget_categories c ON c.category_id = s.category_id
            WHERE c.is_system IS NOT TRUE
            """
        )
    ).fetchone()
    assert non_system_rows is not None
    assert non_system_rows[0] == 0


def test_allocation_guard_blocks_over_budgeting(api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection) -> None:
    _create_cash_account(api_client, "domain3_guard")
    _record_income(api_client, account_id="domain3_guard", amount_minor=50_000, txn_date=date(2025, 2, 8))
    _create_category(api_client, "housing", "Housing")

    payload = {
        "to_category_id": "housing",
        "amount_minor": 75_000,
        "month_start": FEBRUARY.isoformat(),
    }
    response = api_client.post("/api/budget/allocations", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 400
    assert response.json()["detail"] == "Ready-to-Assign is insufficient for this allocation."

    assert _ready_to_assign(api_client, FEBRUARY) == 50_000
    alloc_count = pristine_db.execute("SELECT COUNT(*) FROM budget_allocations").fetchone()
    assert alloc_count is not None and alloc_count[0] == 0


def test_category_rollover_carries_available_into_next_month(api_client: TestClient) -> None:
    _create_cash_account(api_client, "domain3_rollover")
    _record_income(api_client, account_id="domain3_rollover", amount_minor=120_000, txn_date=date(2025, 1, 10))
    _create_category(api_client, "buffer", "Rollover Buffer")

    _allocate_from_rta(
        api_client,
        category_id="buffer",
        month_start=JANUARY,
        amount_minor=120_000,
    )

    january_state = {c["category_id"]: c for c in _list_categories(api_client, JANUARY)}
    assert january_state["buffer"]["available_minor"] == 120_000

    feb_state = {c["category_id"]: c for c in _list_categories(api_client, FEBRUARY)}
    assert feb_state["buffer"]["available_minor"] == 120_000
    assert feb_state["buffer"]["allocated_minor"] == 0
    assert feb_state["buffer"]["activity_minor"] == 0

    assert _ready_to_assign(api_client, JANUARY) == 0
    assert _ready_to_assign(api_client, FEBRUARY) == 0


def test_internal_cash_transfer_is_budget_neutral(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    _create_cash_account(api_client, "domain3_source")
    _create_cash_account(api_client, "domain3_sink")
    _record_income(api_client, account_id="domain3_source", amount_minor=300_000, txn_date=date(2025, 2, 5))
    baseline_rta = _ready_to_assign(api_client, FEBRUARY)

    response = _perform_transfer(
        api_client,
        source_account_id="domain3_source",
        destination_account_id="domain3_sink",
        amount_minor=300_000,
        txn_date=date(2025, 2, 6),
    )

    source = _fetch_account(api_client, "domain3_source")
    sink = _fetch_account(api_client, "domain3_sink")
    assert source["current_balance_minor"] == 0
    assert sink["current_balance_minor"] == 300_000

    assert _ready_to_assign(api_client, FEBRUARY) == baseline_rta
    assert _net_worth_minor(api_client) == 300_000

    concept_id = response["concept_id"]
    txn_rows = pristine_db.execute(
        "SELECT COUNT(*) FROM transactions WHERE concept_id = ?",
        [str(concept_id)],
    ).fetchone()
    assert txn_rows is not None and txn_rows[0] == 2
