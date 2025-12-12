"""Shared helper utilities for integration tests."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi.testclient import TestClient

TEST_HEADERS = {"X-Test-Date": "2025-02-15"}
JANUARY_2025 = date(2025, 1, 1)
FEBRUARY_2025 = date(2025, 2, 1)


def _headers(custom: dict[str, str] | None) -> dict[str, str]:
    if custom is None:
        return TEST_HEADERS
    return custom


def create_account(
    client: TestClient,
    *,
    account_id: str,
    account_type: str,
    account_class: str,
    account_role: str,
    name: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create an account via the API and assert success."""

    payload = {
        "account_id": account_id,
        "name": name or f"{account_id}-name",
        "account_type": account_type,
        "account_class": account_class,
        "account_role": account_role,
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
    }
    response = client.post("/api/accounts", json=payload, headers=_headers(headers))
    assert response.status_code == 201, response.text
    return response.json()


def create_category(
    client: TestClient,
    *,
    category_id: str,
    name: str,
    group_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a budgeting category and return its payload."""

    payload = {
        "category_id": category_id,
        "name": name,
        "group_id": group_id,
        "is_active": True,
    }
    response = client.post("/api/budget-categories", json=payload, headers=_headers(headers))
    assert response.status_code == 201, response.text
    return response.json()


def ready_to_assign(client: TestClient, month_start: date, headers: dict[str, str] | None = None) -> int:
    """Return the Ready-to-Assign balance for ``month_start``."""

    response = client.get(
        "/api/budget/ready-to-assign",
        params={"month": month_start.isoformat()},
        headers=_headers(headers),
    )
    assert response.status_code == 200, response.text
    return int(response.json()["ready_to_assign_minor"])


def net_worth_minor(client: TestClient, headers: dict[str, str] | None = None) -> int:
    """Fetch the current net-worth minor-unit total."""

    response = client.get("/api/net-worth/current", headers=_headers(headers))
    assert response.status_code == 200, response.text
    return int(response.json()["net_worth_minor"])


def record_transaction(
    client: TestClient,
    *,
    account_id: str,
    category_id: str,
    amount_minor: int,
    txn_date: date,
    headers: dict[str, str] | None = None,
    memo: str | None = None,
    concept_id: str | None = None,
) -> dict[str, Any]:
    """Insert a ledger transaction with the provided payload."""

    payload = {
        "transaction_date": txn_date.isoformat(),
        "account_id": account_id,
        "category_id": category_id,
        "amount_minor": amount_minor,
        "status": "cleared",
        "memo": memo,
    }
    if concept_id is not None:
        payload["concept_id"] = concept_id
    response = client.post("/api/transactions", json=payload, headers=_headers(headers))
    assert response.status_code == 201, response.text
    return response.json()


def fund_ready_to_assign(
    client: TestClient,
    *,
    account_id: str,
    amount_minor: int,
    txn_date: date,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Convenience helper that books income into Ready-to-Assign for ``account_id``."""

    return record_transaction(
        client,
        account_id=account_id,
        category_id="available_to_budget",
        amount_minor=amount_minor,
        txn_date=txn_date,
        headers=headers,
    )


def allocate_from_rta(
    client: TestClient,
    *,
    category_id: str,
    amount_minor: int,
    month_start: date,
    headers: dict[str, str] | None = None,
    memo: str | None = None,
) -> dict[str, Any]:
    """Allocate funds from Ready-to-Assign into ``category_id``."""

    payload = {
        "to_category_id": category_id,
        "amount_minor": amount_minor,
        "month_start": month_start.isoformat(),
        "memo": memo,
    }
    response = client.post("/api/budget/allocations", json=payload, headers=_headers(headers))
    assert response.status_code == 201, response.text
    return response.json()


def fetch_account(client: TestClient, account_id: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Return the current API record for ``account_id``."""

    response = client.get("/api/accounts", headers=_headers(headers))
    assert response.status_code == 200, response.text
    for record in response.json():
        if record["account_id"] == account_id:
            return record
    raise AssertionError(f"account {account_id} was not returned")


def category_state(
    client: TestClient,
    *,
    category_id: str,
    month_start: date,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fetch the budget category state for ``category_id`` at ``month_start``."""

    response = client.get(
        "/api/budget-categories",
        params={"month": month_start.isoformat()},
        headers=_headers(headers),
    )
    assert response.status_code == 200, response.text
    for record in response.json():
        if record["category_id"] == category_id:
            return record
    raise AssertionError(f"category {category_id} missing from /api/budget-categories")


def perform_transfer(
    client: TestClient,
    *,
    source_account_id: str,
    destination_account_id: str,
    category_id: str,
    amount_minor: int,
    txn_date: date,
    headers: dict[str, str] | None = None,
    memo: str | None = None,
) -> dict[str, Any]:
    """Execute a categorized transfer between accounts."""

    payload = {
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
        "category_id": category_id,
        "amount_minor": amount_minor,
        "transaction_date": txn_date.isoformat(),
        "memo": memo,
    }
    response = client.post("/api/transfers", json=payload, headers=_headers(headers))
    assert response.status_code == 201, response.text
    return response.json()
