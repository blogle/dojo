"""Integration tests for Account Onboarding Wizard extended properties."""

from __future__ import annotations

from datetime import date

import duckdb
from fastapi.testclient import TestClient

TEST_HEADERS = {"X-Test-Date": "2025-02-15"}


def _create_account_extended(
    client: TestClient,
    **kwargs,
) -> dict:
    payload = {
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
        **kwargs,
    }
    response = client.post("/api/accounts", json=payload, headers=TEST_HEADERS)
    assert response.status_code == 201, f"{response.status_code}: {response.text}"
    return response.json()


def test_wizard_cash_account_creation(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 1.1 variant: Verify Cash account creation with wizard fields."""
    account_id = "wizard_cash_01"
    res = _create_account_extended(
        api_client,
        account_id=account_id,
        name="Main Checking",
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
        institution_name="Chase",
        interest_rate_apy=0.015,
    )
    assert res["account_id"] == account_id
    
    # Verify main table
    row = pristine_db.execute(
        "SELECT institution_name FROM accounts WHERE account_id = ?", [account_id]
    ).fetchone()
    assert row[0] == "Chase"

    # Verify detail table
    row_detail = pristine_db.execute(
        "SELECT interest_rate_apy FROM cash_account_details WHERE account_id = ? AND is_active = TRUE",
        [account_id],
    ).fetchone()
    assert row_detail is not None
    assert row_detail[0] == 0.015


def test_wizard_credit_card_creation(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 1.2 variant: Verify Credit account creation with wizard fields."""
    account_id = "wizard_credit_01"
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="Gold Card",
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
        institution_name="Amex",
        card_type="American Express",
        apr=24.99,
        cash_advance_apr=29.99,
    )

    # Verify detail table
    row_detail = pristine_db.execute(
        """
        SELECT card_type, apr, cash_advance_apr 
        FROM credit_account_details 
        WHERE account_id = ? AND is_active = TRUE
        """,
        [account_id],
    ).fetchone()
    assert row_detail is not None
    assert row_detail[0] == "American Express"
    assert row_detail[1] == 24.99
    assert row_detail[2] == 29.99


def test_wizard_loan_creation(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 1.3 variant: Verify Loan account creation with wizard fields."""
    account_id = "wizard_loan_01"
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="Student Loan A",
        account_type="liability",
        account_class="loan",
        account_role="tracking",
        institution_name="Sallie Mae",
        initial_principal_minor=5000000,
        interest_rate_apy=6.5,
        mortgage_escrow_details="Includes taxes",
    )

    # Verify detail table
    row_detail = pristine_db.execute(
        """
        SELECT initial_principal_minor, interest_rate_apy, mortgage_escrow_details
        FROM loan_account_details 
        WHERE account_id = ? AND is_active = TRUE
        """,
        [account_id],
    ).fetchone()
    assert row_detail is not None
    assert row_detail[0] == 5000000
    assert row_detail[1] == 6.5
    assert row_detail[2] == "Includes taxes"


def test_wizard_investment_creation(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 1.4 variant: Verify Investment account creation with wizard fields."""
    account_id = "wizard_invest_01"
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="Roth IRA",
        account_type="asset",
        account_class="investment",
        account_role="tracking",
        institution_name="Vanguard",
        risk_free_sweep_rate=4.5,
        is_self_directed=True,
        tax_classification="Roth IRA",
    )

    # Verify detail table
    row_detail = pristine_db.execute(
        """
        SELECT risk_free_sweep_rate, is_self_directed, tax_classification
        FROM investment_account_details 
        WHERE account_id = ? AND is_active = TRUE
        """,
        [account_id],
    ).fetchone()
    assert row_detail is not None
    assert row_detail[0] == 4.5
    assert row_detail[1] is True
    assert row_detail[2] == "Roth IRA"


def test_wizard_accessible_asset_creation(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Verify Accessible Asset creation with wizard fields."""
    account_id = "wizard_accessible_01"
    term_end = date(2026, 12, 31)
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="CD 12-Month",
        account_type="asset",
        account_class="accessible",
        account_role="tracking",
        institution_name="Ally",
        interest_rate_apy=5.0,
        term_end_date=term_end.isoformat(),
        early_withdrawal_penalty=True,
    )

    # Verify detail table
    row_detail = pristine_db.execute(
        """
        SELECT interest_rate_apy, term_end_date, early_withdrawal_penalty
        FROM accessible_asset_details 
        WHERE account_id = ? AND is_active = TRUE
        """,
        [account_id],
    ).fetchone()
    assert row_detail is not None
    assert row_detail[0] == 5.0
    # DuckDB returns date objects
    assert row_detail[1] == term_end
    assert row_detail[2] is True


def test_wizard_tangible_asset_creation(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Verify Tangible Asset creation with wizard fields."""
    account_id = "wizard_tangible_01"
    _create_account_extended(
        api_client,
        account_id=account_id,
        name="Honda Civic",
        account_type="asset",
        account_class="tangible",
        account_role="tracking",
        asset_name="2018 Honda Civic",
        acquisition_cost_minor=2000000,
    )

    # Verify detail table
    row_detail = pristine_db.execute(
        """
        SELECT asset_name, acquisition_cost_minor
        FROM tangible_asset_details 
        WHERE account_id = ? AND is_active = TRUE
        """,
        [account_id],
    ).fetchone()
    assert row_detail is not None
    assert row_detail[0] == "2018 Honda Civic"
    assert row_detail[1] == 2000000
