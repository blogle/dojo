"""Integration tests for the reconciliation API contract."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from tests.integration.helpers import TEST_HEADERS, create_account


def _create_transaction(
    client: TestClient,
    *,
    account_id: str,
    category_id: str,
    amount_minor: int,
    txn_date: date,
    status: str,
    memo: str,
) -> dict:
    payload = {
        "transaction_date": txn_date.isoformat(),
        "account_id": account_id,
        "category_id": category_id,
        "amount_minor": amount_minor,
        "status": status,
        "memo": memo,
    }
    response = client.post("/api/transactions", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _update_transaction(
    client: TestClient,
    concept_id: str,
    *,
    account_id: str,
    category_id: str,
    amount_minor: int,
    txn_date: date,
    memo: str,
) -> dict:
    payload = {
        "transaction_date": txn_date.isoformat(),
        "account_id": account_id,
        "category_id": category_id,
        "amount_minor": amount_minor,
        "memo": memo,
    }
    response = client.put(f"/api/transactions/{concept_id}", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def test_reconciliation_worksheet_includes_mutations_and_pending(
    api_client: TestClient,
) -> None:
    """GET worksheet returns modified/new items plus old pending items."""

    account_id = "checking_recon"
    category_id = "balance_adjustment"

    create_account(
        api_client,
        account_id=account_id,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
        headers=TEST_HEADERS,
    )

    tx_cleared = _create_transaction(
        api_client,
        account_id=account_id,
        category_id=category_id,
        amount_minor=-2000,
        txn_date=date(2025, 1, 10),
        status="cleared",
        memo="cleared-at-t1",
    )
    tx_pending = _create_transaction(
        api_client,
        account_id=account_id,
        category_id=category_id,
        amount_minor=-1500,
        txn_date=date(2025, 1, 11),
        status="pending",
        memo="pending-at-t1",
    )
    tx_old_pending = _create_transaction(
        api_client,
        account_id=account_id,
        category_id=category_id,
        amount_minor=-500,
        txn_date=date(2024, 10, 1),
        status="pending",
        memo="old-pending-at-t1",
    )
    tx_stable_cleared = _create_transaction(
        api_client,
        account_id=account_id,
        category_id=category_id,
        amount_minor=-999,
        txn_date=date(2025, 1, 9),
        status="cleared",
        memo="cleared-stable",
    )

    latest_before = api_client.get(
        f"/api/accounts/{account_id}/reconciliations/latest",
        headers=TEST_HEADERS,
    )
    assert latest_before.status_code == 204, latest_before.text

    commit = api_client.post(
        f"/api/accounts/{account_id}/reconciliations",
        json={"statement_date": "2025-01-31", "statement_balance_minor": 0},
        headers=TEST_HEADERS,
    )
    assert commit.status_code == 201, commit.text

    latest_after = api_client.get(
        f"/api/accounts/{account_id}/reconciliations/latest",
        headers=TEST_HEADERS,
    )
    assert latest_after.status_code == 200, latest_after.text

    _update_transaction(
        api_client,
        tx_pending["concept_id"],
        account_id=account_id,
        category_id=category_id,
        amount_minor=-2500,
        txn_date=date(2025, 1, 11),
        memo="pending-tip-adjusted",
    )
    _update_transaction(
        api_client,
        tx_cleared["concept_id"],
        account_id=account_id,
        category_id=category_id,
        amount_minor=-2000,
        txn_date=date(2025, 1, 12),
        memo="cleared-date-corrected",
    )
    tx_new = _create_transaction(
        api_client,
        account_id=account_id,
        category_id=category_id,
        amount_minor=-333,
        txn_date=date(2025, 1, 13),
        status="cleared",
        memo="new-at-t2",
    )

    worksheet = api_client.get(
        f"/api/accounts/{account_id}/reconciliations/worksheet",
        headers=TEST_HEADERS,
    )
    assert worksheet.status_code == 200, worksheet.text

    worksheet_concepts = {row["concept_id"] for row in worksheet.json()}

    assert tx_pending["concept_id"] in worksheet_concepts
    assert tx_cleared["concept_id"] in worksheet_concepts
    assert tx_new["concept_id"] in worksheet_concepts
    assert tx_old_pending["concept_id"] in worksheet_concepts

    assert tx_stable_cleared["concept_id"] not in worksheet_concepts
