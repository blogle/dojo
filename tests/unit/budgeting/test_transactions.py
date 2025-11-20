"""Unit tests for the transaction entry service."""

from datetime import date

import duckdb
import pytest

from dojo.budgeting.errors import InvalidTransaction
from dojo.budgeting.schemas import CategorizedTransferRequest, NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService


def test_create_transaction_updates_account_and_category(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-12345,
        memo="weekly groceries",
    )

    response = service.create(in_memory_db, cmd)

    assert response.status == "pending"
    assert response.account.current_balance_minor == 500000 - 12345
    assert response.category.available_minor == 12345 * -1
    rows = in_memory_db.execute(
        "SELECT COUNT(*) FROM transactions WHERE concept_id = ?",
        [str(response.concept_id)],
    ).fetchone()
    assert rows is not None
    assert rows[0] == 1


def test_system_category_transactions_skip_budget_activity(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="opening_balance",
        amount_minor=25000,
        memo="Seed balance",
    )

    response = service.create(in_memory_db, cmd)

    assert response.category.activity_minor == 0
    assert response.category.available_minor == 0
    row = in_memory_db.execute(
        "SELECT COUNT(*) FROM budget_category_monthly_state WHERE category_id = 'opening_balance'",
        []
    ).fetchone()
    assert row is not None
    assert row[0] == 0


def test_available_to_budget_increases_ready_to_assign(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    baseline_ready = service.ready_to_assign(in_memory_db, month_start)

    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="available_to_budget",
            amount_minor=50000,
            memo="Paycheck",
        ),
    )

    updated_ready = service.ready_to_assign(in_memory_db, month_start)
    assert updated_ready == baseline_ready + 50000


def test_edit_transaction_closes_previous_version(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    first_cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-1000,
    )
    first = service.create(in_memory_db, first_cmd)

    edit_cmd = NewTransactionRequest(
        concept_id=first.concept_id,
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-2000,
        status="cleared",
    )
    updated = service.create(in_memory_db, edit_cmd)

    assert updated.status == "cleared"

    counts = in_memory_db.execute(
        """
        SELECT
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
        FROM transactions
        WHERE concept_id = ?
        """,
        [str(first.concept_id)],
    ).fetchone()
    assert counts is not None
    assert counts[0] == 1

    status_row = in_memory_db.execute(
        "SELECT status FROM transactions WHERE transaction_version_id = ?",
        [str(updated.transaction_version_id)],
    ).fetchone()
    assert status_row is not None
    assert status_row[0] == "cleared"


def test_zero_amount_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=0,
    )
    with pytest.raises(InvalidTransaction):
        service.create(in_memory_db, cmd)


def test_list_recent_transactions_returns_latest_first(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    first = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-100,
            memo="old",
        ),
    )
    second = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-200,
            memo="new",
        ),
    )

    rows = service.list_recent(in_memory_db, limit=5)
    assert rows
    assert rows[0].transaction_version_id == second.transaction_version_id
    assert rows[1].transaction_version_id == first.transaction_version_id


def insert_account(
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
    name: str,
    account_type: str,
    account_class: str,
    account_role: str,
    balance_minor: int,
) -> None:
    conn.execute(
        """
        INSERT INTO accounts (
            account_id,
            name,
            account_type,
            account_class,
            account_role,
            current_balance_minor,
            currency,
            is_active
        ) VALUES (?, ?, ?, ?, ?, ?, 'USD', TRUE)
        """,
        [account_id, name, account_type, account_class, account_role, balance_minor],
    )


def insert_category(conn: duckdb.DuckDBPyConnection, category_id: str, name: str) -> None:
    conn.execute(
        """
        INSERT INTO budget_categories (category_id, name, is_active)
        VALUES (?, ?, TRUE)
        ON CONFLICT (category_id) DO UPDATE SET name = EXCLUDED.name, is_active = TRUE
        """,
        [category_id, name],
    )


def test_transfer_cash_to_investment_updates_balances(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    insert_account(
        in_memory_db,
        "house_investment",
        "House Investment",
        "asset",
        "investment",
        "tracking",
        0,
    )
    insert_category(in_memory_db, "investments", "Investments")

    service = TransactionEntryService()
    amount = 20000
    response = service.transfer(
        in_memory_db,
        CategorizedTransferRequest(
            source_account_id="house_checking",
            destination_account_id="house_investment",
            category_id="investments",
            amount_minor=amount,
            transaction_date=date.today(),
            memo="Move to brokerage",
        ),
    )

    rows = in_memory_db.execute(
        "SELECT COUNT(*) FROM transactions WHERE concept_id = ?",
        [str(response.concept_id)],
    ).fetchone()
    assert rows is not None
    assert rows[0] == 2

    checking = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'"
    ).fetchone()
    investment = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_investment'"
    ).fetchone()
    assert checking is not None
    assert investment is not None
    assert checking[0] == 500000 - amount
    assert investment[0] == amount
    assert response.category.available_minor == -amount


def test_transfer_cash_to_liability_updates_category_state(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    insert_account(
        in_memory_db,
        "house_loan",
        "House Loan",
        "liability",
        "loan",
        "tracking",
        400000,
    )

    service = TransactionEntryService()
    amount = 15000
    response = service.transfer(
        in_memory_db,
        CategorizedTransferRequest(
            source_account_id="house_checking",
            destination_account_id="house_loan",
            category_id="groceries",
            amount_minor=amount,
            transaction_date=date.today(),
            memo="Pay down loan",
        ),
    )

    liability = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_loan'"
    ).fetchone()
    assert liability is not None
    assert liability[0] == 400000 - amount
    assert response.category.available_minor == -amount


def test_allocate_envelope_blocked_for_system_categories(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)

    with pytest.raises(InvalidTransaction):
        service.allocate_envelope(in_memory_db, "opening_balance", 1000, month_start)

    with pytest.raises(InvalidTransaction):
        service.allocate_envelope(
            in_memory_db,
            "groceries",
            500,
            month_start,
            from_category_id="opening_balance",
        )


def test_allocate_envelope_updates_ready_to_assign(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    baseline_ready = service.ready_to_assign(in_memory_db, month_start)

    category_state = service.allocate_envelope(in_memory_db, "groceries", 5000, month_start)

    assert category_state.available_minor == 5000
    updated_ready = service.ready_to_assign(in_memory_db, month_start)
    assert updated_ready == baseline_ready - 5000


def test_allocate_envelope_blocks_when_ready_insufficient(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    ready_minor = service.ready_to_assign(in_memory_db, month_start)
    with pytest.raises(InvalidTransaction):
        service.allocate_envelope(in_memory_db, "groceries", ready_minor + 100, month_start)


def test_reassign_between_categories_updates_both_states(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    service.allocate_envelope(in_memory_db, "groceries", 5000, month_start)

    service.allocate_envelope(
        in_memory_db,
        "housing",
        2000,
        month_start,
        from_category_id="groceries",
        memo="cover rent",
    )

    groceries_state = in_memory_db.execute(
        "SELECT available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",
        ["groceries", month_start],
    ).fetchone()
    housing_state = in_memory_db.execute(
        "SELECT available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",
        ["housing", month_start],
    ).fetchone()
    assert groceries_state is not None
    assert groceries_state[0] == 3000
    assert housing_state is not None
    assert housing_state[0] == 2000
    ledger_row = in_memory_db.execute(
        "SELECT to_category_id, from_category_id, amount_minor, memo FROM budget_allocations ORDER BY created_at DESC LIMIT 1",
        [],
    ).fetchone()
    assert ledger_row is not None
    assert ledger_row[0] == "housing"
    assert ledger_row[1] == "groceries"
    assert ledger_row[2] == 2000
    assert ledger_row[3] == "cover rent"


def test_month_cash_inflow_counts_cash_accounts_only(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="income",
            amount_minor=60000,
        ),
    )
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-1000,
        ),
    )
    insert_account(
        in_memory_db,
        "external_brokerage",
        "External Brokerage",
        "asset",
        "investment",
        "tracking",
        0,
    )
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="external_brokerage",
            category_id="income",
            amount_minor=40000,
        ),
    )

    inflow = service.month_cash_inflow(in_memory_db, month_start)
    assert inflow == 60000


def test_transfer_investment_to_cash_treated_as_income(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    insert_account(
        in_memory_db,
        "house_investment",
        "House Investment",
        "asset",
        "investment",
        "tracking",
        50000,
    )

    service = TransactionEntryService()
    amount = 12000
    response = service.transfer(
        in_memory_db,
        CategorizedTransferRequest(
            source_account_id="house_investment",
            destination_account_id="house_checking",
            category_id="income",
            amount_minor=amount,
            transaction_date=date.today(),
            memo="Rebalance to checking",
        ),
    )

    investment_balance = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_investment'"
    ).fetchone()
    checking_balance = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'"
    ).fetchone()
    assert investment_balance is not None
    assert checking_balance is not None
    assert investment_balance[0] == 50000 - amount
    assert checking_balance[0] == 500000 + amount
    assert response.category.activity_minor == amount


def test_ready_to_assign_with_activity(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    amount = -10000
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=amount,
        ),
    )
    month_start = date.today().replace(day=1)
    ready = service.ready_to_assign(in_memory_db, month_start)
    # House checking and savings are on-budget cash accounts
    expected_cash = 500000 + 1250000 + amount
    # Activity increases by 10000 for the spend so the committed flow equals -10000
    expected = expected_cash + (-amount)
    assert ready == expected
