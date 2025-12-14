"""Integration tests for spending flow specs."""

from __future__ import annotations

from datetime import date

import duckdb
from fastapi.testclient import TestClient

from dojo.budgeting.services import derive_payment_category_id
from tests.integration.helpers import (  # type: ignore[import]
    FEBRUARY_2025,
    allocate_from_rta,
    category_state,
    create_account,
    create_category,
    fetch_account,
    fund_ready_to_assign,
    net_worth_minor,
    ready_to_assign,
    record_transaction,
)

FEBRUARY = FEBRUARY_2025
SPEND_DATE = date(2025, 2, 10)


def test_cash_spend_updates_category_activity_and_cash_balance(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 4.1 — cash spending touches only the cash account and chosen envelope."""

    cash_account = "cash_spend_cash"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_category(api_client, category_id="groceries_cash", name="Groceries")

    income_minor = 20_000  # $200.00
    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=income_minor, txn_date=SPEND_DATE)
    allocate_from_rta(api_client, category_id="groceries_cash", amount_minor=income_minor, month_start=FEBRUARY)
    baseline_net = net_worth_minor(api_client)

    spend_minor = 6_000  # $60.00
    record_transaction(
        api_client,
        account_id=cash_account,
        category_id="groceries_cash",
        amount_minor=-spend_minor,
        txn_date=SPEND_DATE,
    )

    account = fetch_account(api_client, cash_account)
    assert account["current_balance_minor"] == income_minor - spend_minor

    row = pristine_db.execute(
        """
        SELECT available_minor, activity_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        ["groceries_cash", FEBRUARY],
    ).fetchone()
    assert row == (income_minor - spend_minor, spend_minor)

    assert ready_to_assign(api_client, FEBRUARY) == 0
    assert baseline_net - net_worth_minor(api_client) == spend_minor

    txn_row = pristine_db.execute(
        """
        SELECT amount_minor, category_id, is_active
        FROM transactions
        WHERE account_id = ? AND category_id = ?
        """,
        [cash_account, "groceries_cash"],
    ).fetchone()
    assert txn_row == (-spend_minor, "groceries_cash", True)


def test_credit_spend_against_funded_category_preserves_rta(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 4.2 — credit purchases consume the funded envelope and increase liability."""

    cash_account = "credit_spend_cash_seed"
    credit_account = "credit_spend_card"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=credit_account,
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
    )
    create_category(api_client, category_id="groceries_credit", name="Groceries (Card)")

    income_minor = 20_000
    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=income_minor, txn_date=SPEND_DATE)
    allocate_from_rta(api_client, category_id="groceries_credit", amount_minor=income_minor, month_start=FEBRUARY)
    baseline_net = net_worth_minor(api_client)

    spend_minor = 8_000  # $80.00 charge
    record_transaction(
        api_client,
        account_id=credit_account,
        category_id="groceries_credit",
        amount_minor=-spend_minor,
        txn_date=SPEND_DATE,
    )

    credit = fetch_account(api_client, credit_account)
    assert credit["current_balance_minor"] == -spend_minor

    cat_state = category_state(api_client, category_id="groceries_credit", month_start=FEBRUARY)
    assert cat_state["available_minor"] == income_minor - spend_minor
    assert cat_state["activity_minor"] == spend_minor

    assert ready_to_assign(api_client, FEBRUARY) == 0

    net_after = net_worth_minor(api_client)
    assert baseline_net - net_after == spend_minor

    txn_row = pristine_db.execute(
        "SELECT amount_minor FROM transactions WHERE account_id = ? AND category_id = ?",
        [credit_account, "groceries_credit"],
    ).fetchone()
    assert txn_row == (-spend_minor,)


def test_credit_refund_improves_liability_and_restores_envelope(api_client: TestClient) -> None:
    """Spec 4.3 — refunds lower the liability and replenish the funded category."""

    cash_account = "credit_refund_cash_seed"
    credit_account = "credit_refund_card"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=credit_account,
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
    )
    create_category(api_client, category_id="groceries_refund", name="Groceries")

    income_minor = 20_000
    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=income_minor, txn_date=SPEND_DATE)
    allocate_from_rta(api_client, category_id="groceries_refund", amount_minor=income_minor, month_start=FEBRUARY)

    spend_minor = 8_000
    record_transaction(
        api_client,
        account_id=credit_account,
        category_id="groceries_refund",
        amount_minor=-spend_minor,
        txn_date=SPEND_DATE,
    )
    net_after_spend = net_worth_minor(api_client)

    refund_minor = 3_000
    record_transaction(
        api_client,
        account_id=credit_account,
        category_id="groceries_refund",
        amount_minor=refund_minor,
        txn_date=date(2025, 2, 12),
    )

    credit = fetch_account(api_client, credit_account)
    assert credit["current_balance_minor"] == -(spend_minor - refund_minor)

    cat_state = category_state(api_client, category_id="groceries_refund", month_start=FEBRUARY)
    assert cat_state["available_minor"] == income_minor - spend_minor + refund_minor
    assert cat_state["activity_minor"] == spend_minor - refund_minor

    net_after_refund = net_worth_minor(api_client)
    assert net_after_refund - net_after_spend == refund_minor


def test_split_transaction_apportions_amounts_by_category(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 4.4 — split spending keeps each envelope's share and maintains a single concept."""

    cash_account = "split_spend_cash"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_category(api_client, category_id="split_a", name="Split A")
    create_category(api_client, category_id="split_b", name="Split B")

    total_income = 90_00  # $90.00
    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=total_income, txn_date=SPEND_DATE)
    allocate_from_rta(api_client, category_id="split_a", amount_minor=50_00, month_start=FEBRUARY)
    allocate_from_rta(api_client, category_id="split_b", amount_minor=40_00, month_start=FEBRUARY)

    record_transaction(
        api_client,
        account_id=cash_account,
        category_id="split_a",
        amount_minor=-50_00,
        txn_date=SPEND_DATE,
    )
    record_transaction(
        api_client,
        account_id=cash_account,
        category_id="split_b",
        amount_minor=-40_00,
        txn_date=SPEND_DATE,
    )

    account = fetch_account(api_client, cash_account)
    total_spent = 50_00 + 40_00
    assert account["current_balance_minor"] == total_income - total_spent

    cat_a = category_state(api_client, category_id="split_a", month_start=FEBRUARY)
    cat_b = category_state(api_client, category_id="split_b", month_start=FEBRUARY)
    assert cat_a["available_minor"] == 0
    assert cat_a["activity_minor"] == 50_00
    assert cat_b["available_minor"] == 0
    assert cat_b["activity_minor"] == 40_00

    txn_count = pristine_db.execute(
        """
        SELECT COUNT(*) FROM transactions
        WHERE account_id = ? AND category_id IN (?, ?) AND is_active = TRUE
        """,
        [cash_account, "split_a", "split_b"],
    ).fetchone()
    assert txn_count == (2,)


def test_credit_overspend_tracks_unfunded_portion(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 4.5 — overspending on credit isolates the unfunded portion as uncovered debt."""

    cash_account = "credit_overspend_cash_seed"
    credit_account = "credit_overspend_card"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=credit_account,
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
    )
    create_category(api_client, category_id="dining_credit", name="Dining")

    funded_minor = 20_00  # $20.00 available in Dining
    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=funded_minor, txn_date=SPEND_DATE)
    allocate_from_rta(api_client, category_id="dining_credit", amount_minor=funded_minor, month_start=FEBRUARY)

    spend_minor = 50_00  # $50.00 charge
    record_transaction(
        api_client,
        account_id=credit_account,
        category_id="dining_credit",
        amount_minor=-spend_minor,
        txn_date=SPEND_DATE,
    )

    dining_state = category_state(api_client, category_id="dining_credit", month_start=FEBRUARY)
    assert dining_state["available_minor"] == funded_minor - spend_minor
    assert ready_to_assign(api_client, FEBRUARY) == 0

    payment_category_id = derive_payment_category_id(credit_account)
    payment_row = pristine_db.execute(
        """
        SELECT available_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        [payment_category_id, FEBRUARY],
    ).fetchone()
    assert payment_row is not None
    # The payment category tracks the full charge so RTA stays unchanged.
    assert payment_row[0] == spend_minor

    credit = fetch_account(api_client, credit_account)
    assert credit["current_balance_minor"] == -spend_minor
