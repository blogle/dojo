"""Integration tests for Domain 5 transfers, contributions, and payments."""

from __future__ import annotations

from datetime import date

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
    perform_transfer,
)

FEBRUARY = FEBRUARY_2025
OPENING_DATE = date(2025, 2, 1)
TRANSFER_DATE = date(2025, 2, 15)


def _set_opening_balance(
    client: TestClient,
    *,
    account_id: str,
    amount_minor: int,
    txn_date: date = OPENING_DATE,
) -> None:
    """Create a balance adjustment entry for ``account_id``."""

    record_transaction(
        client,
        account_id=account_id,
        category_id="balance_adjustment",
        amount_minor=amount_minor,
        txn_date=txn_date,
    )


def test_cash_to_credit_payment_consumes_payment_category(api_client: TestClient) -> None:
    """Spec 5.1 — paying a credit card spends only from the earmarked payment envelope."""

    cash_account = "domain5_cash_payment"
    credit_account = "domain5_credit_payment"
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
    payment_category = derive_payment_category_id(credit_account)

    # Fund the payment category from Ready-to-Assign.
    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=30_000, txn_date=OPENING_DATE)
    allocate_from_rta(api_client, category_id=payment_category, amount_minor=30_000, month_start=FEBRUARY)

    # Establish the existing outstanding liability.
    _set_opening_balance(api_client, account_id=credit_account, amount_minor=-80_000)
    baseline_net = net_worth_minor(api_client)

    response = perform_transfer(
        api_client,
        source_account_id=cash_account,
        destination_account_id=credit_account,
        category_id=payment_category,
        amount_minor=25_000,
        txn_date=TRANSFER_DATE,
    )

    cash = fetch_account(api_client, cash_account)
    assert cash["current_balance_minor"] == 5_000

    credit = fetch_account(api_client, credit_account)
    assert credit["current_balance_minor"] == -55_000

    payment_state = category_state(api_client, category_id=payment_category, month_start=FEBRUARY)
    assert payment_state["available_minor"] == 5_000
    assert payment_state["activity_minor"] == 25_000
    assert response["category"]["activity_minor"] == 25_000

    assert ready_to_assign(api_client, FEBRUARY) == 0
    assert net_worth_minor(api_client) == baseline_net


def test_cash_to_accessible_transfer_is_budget_neutral(api_client: TestClient) -> None:
    """Spec 5.2 — moving funds to an accessible asset preserves RTA and net worth."""

    cash_account = "domain5_cash_accessible"
    accessible_account = "domain5_accessible"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=accessible_account,
        account_type="asset",
        account_class="accessible",
        account_role="tracking",
    )
    create_category(api_client, category_id="short_term_savings", name="Short-Term Savings")

    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=50_000, txn_date=OPENING_DATE)
    allocate_from_rta(
        api_client,
        category_id="short_term_savings",
        amount_minor=40_000,
        month_start=FEBRUARY,
    )
    baseline_net = net_worth_minor(api_client)

    perform_transfer(
        api_client,
        source_account_id=cash_account,
        destination_account_id=accessible_account,
        category_id="short_term_savings",
        amount_minor=40_000,
        txn_date=TRANSFER_DATE,
    )

    cash = fetch_account(api_client, cash_account)
    assert cash["current_balance_minor"] == 10_000
    accessible = fetch_account(api_client, accessible_account)
    assert accessible["current_balance_minor"] == 40_000

    category = category_state(api_client, category_id="short_term_savings", month_start=FEBRUARY)
    assert category["available_minor"] == 0
    assert category["activity_minor"] == 40_000

    assert ready_to_assign(api_client, FEBRUARY) == 10_000
    assert net_worth_minor(api_client) == baseline_net


def test_accessible_withdrawal_reclassifies_to_income(api_client: TestClient) -> None:
    """Spec 5.3 — withdrawing from an accessible asset raises Ready-to-Assign as income."""

    cash_account = "domain5_cash_withdraw"
    accessible_account = "domain5_accessible_withdraw"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=accessible_account,
        account_type="asset",
        account_class="accessible",
        account_role="tracking",
    )

    _set_opening_balance(api_client, account_id=accessible_account, amount_minor=100_000)
    baseline_net = net_worth_minor(api_client)

    # Outflow from the accessible asset.
    record_transaction(
        api_client,
        account_id=accessible_account,
        category_id="account_transfer",
        amount_minor=-30_000,
        txn_date=TRANSFER_DATE,
    )
    # Inflow into cash categorized as Ready-to-Assign income.
    record_transaction(
        api_client,
        account_id=cash_account,
        category_id="available_to_budget",
        amount_minor=30_000,
        txn_date=TRANSFER_DATE,
    )

    accessible = fetch_account(api_client, accessible_account)
    assert accessible["current_balance_minor"] == 70_000
    cash = fetch_account(api_client, cash_account)
    assert cash["current_balance_minor"] == 30_000

    assert ready_to_assign(api_client, FEBRUARY) == 30_000
    assert net_worth_minor(api_client) == baseline_net


def test_cash_to_investment_contribution_is_budget_neutral(api_client: TestClient) -> None:
    """Spec 5.4 — contributing to an investment account keeps RTA and net worth fixed."""

    cash_account = "domain5_cash_invest"
    investment_account = "domain5_invest"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=investment_account,
        account_type="asset",
        account_class="investment",
        account_role="tracking",
    )
    create_category(api_client, category_id="investment_contrib", name="Investment Contribution")

    fund_ready_to_assign(api_client, account_id=cash_account, amount_minor=80_000, txn_date=OPENING_DATE)
    allocate_from_rta(
        api_client,
        category_id="investment_contrib",
        amount_minor=50_000,
        month_start=FEBRUARY,
    )
    baseline_net = net_worth_minor(api_client)

    perform_transfer(
        api_client,
        source_account_id=cash_account,
        destination_account_id=investment_account,
        category_id="investment_contrib",
        amount_minor=50_000,
        txn_date=TRANSFER_DATE,
    )

    cash = fetch_account(api_client, cash_account)
    assert cash["current_balance_minor"] == 30_000
    investment = fetch_account(api_client, investment_account)
    assert investment["current_balance_minor"] == 50_000

    category = category_state(api_client, category_id="investment_contrib", month_start=FEBRUARY)
    assert category["available_minor"] == 0
    assert category["activity_minor"] == 50_000

    assert ready_to_assign(api_client, FEBRUARY) == 30_000
    assert net_worth_minor(api_client) == baseline_net


def test_investment_withdrawal_treated_as_income(api_client: TestClient) -> None:
    """Spec 5.5 — withdrawing from an investment account boosts RTA when categorized as income."""

    cash_account = "domain5_cash_invest_withdraw"
    investment_account = "domain5_invest_withdraw"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_account(
        api_client,
        account_id=investment_account,
        account_type="asset",
        account_class="investment",
        account_role="tracking",
    )

    _set_opening_balance(api_client, account_id=investment_account, amount_minor=500_000)
    baseline_net = net_worth_minor(api_client)

    # Remove funds from the investment account without affecting the budget.
    record_transaction(
        api_client,
        account_id=investment_account,
        category_id="account_transfer",
        amount_minor=-40_000,
        txn_date=TRANSFER_DATE,
    )
    # Categorize the inflow into cash as income to Ready-to-Assign.
    record_transaction(
        api_client,
        account_id=cash_account,
        category_id="available_to_budget",
        amount_minor=40_000,
        txn_date=TRANSFER_DATE,
    )

    cash = fetch_account(api_client, cash_account)
    assert cash["current_balance_minor"] == 40_000

    investment = fetch_account(api_client, investment_account)
    assert investment["current_balance_minor"] == 460_000

    assert ready_to_assign(api_client, FEBRUARY) == 40_000
    assert net_worth_minor(api_client) == baseline_net
