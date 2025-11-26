"""
Unit tests for the transaction entry service.

This module contains unit tests that verify the correct behavior of the
`TransactionEntryService`, focusing on transaction creation, updates,
transfers, account and category state changes, and error handling.
"""

from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID

import duckdb
import pytest

from dojo.budgeting.dao import BudgetingDAO
from dojo.budgeting.errors import InvalidTransactionError
from dojo.budgeting.schemas import CategorizedTransferRequest, NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> SimpleNamespace:
    """
    Executes an SQL query and fetches a single row as a SimpleNamespace.

    This helper function is used within tests to retrieve data directly
    from the database and provide attribute-style access to the columns.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    sql : str
        The SQL query string to execute.
    params : list[object] | tuple[object, ...] | None, optional
        Parameters to bind to the SQL query.

    Returns
    -------
    SimpleNamespace
        A SimpleNamespace object representing the fetched row.

    Raises
    ------
    AssertionError
        If no row is fetched (i.e., `fetchone()` returns None).
    """
    row = conn.execute(sql, params or []).fetchone()
    assert row is not None, "Expected to fetch a row, but got None."
    # Extract column names from the cursor description.
    columns = [column[0] for column in conn.description or ()]
    # Map column names to row values and create a SimpleNamespace.
    data = {columns[idx]: row[idx] for idx in range(len(columns))}
    return SimpleNamespace(**data)


def test_create_transaction_updates_account_and_category(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that creating a new transaction correctly updates the associated
    account's balance and the budget category's activity and available funds.
    """
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-12345,  # Spending transaction
        memo="weekly groceries",
    )

    response = service.create(in_memory_db, cmd)

    # Assert that the transaction status is as expected.
    assert response.status == "pending"
    # Assert account balance reflects the transaction. (Initial 500000 - 12345)
    assert response.account.current_balance_minor == 500000 - 12345
    # Assert category available funds reflect the transaction. (Initial 0 - 12345)
    # Note: For spending, available_minor decreases, activity_minor increases (positive value for outflow).
    # The initial available for groceries is 0, then allocated + activity_minor.
    # The base_budgeting.sql sets groceries to 0, so the available will be 0 - 12345.
    assert response.category.available_minor == -12345
    # Verify that exactly one transaction version exists for this concept.
    count_row = _fetch_namespace(
        in_memory_db,
        "SELECT COUNT(*) AS concept_total FROM transactions WHERE concept_id = ?",
        [str(response.concept_id)],
    )
    assert count_row.concept_total == 1


def test_system_category_transactions_skip_budget_activity(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that transactions assigned to system categories (e.g., 'opening_balance')
    do not affect budget category activity or available funds.
    """
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="opening_balance",  # A system category
        amount_minor=25000,
        memo="Seed balance",
    )

    response = service.create(in_memory_db, cmd)

    # Assert that activity and available funds for a system category remain 0.
    assert response.category.activity_minor == 0
    assert response.category.available_minor == 0
    # Further verify that no monthly state record is created for system categories.
    state_row = _fetch_namespace(
        in_memory_db,
        (
            "SELECT COUNT(*) AS monthly_state_count FROM budget_category_monthly_state "
            "WHERE category_id = 'opening_balance'"
        ),
        [],
    )
    assert state_row.monthly_state_count == 0


def test_available_to_budget_increases_ready_to_assign(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that transactions categorized as 'available_to_budget' correctly
    increase the "Ready to Assign" amount for the current month.
    """
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    # Get the baseline "Ready to Assign" amount.
    baseline_ready = service.ready_to_assign(in_memory_db, month_start)

    # Create an inflow transaction categorized as 'available_to_budget'.
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

    # Get the updated "Ready to Assign" amount.
    updated_ready = service.ready_to_assign(in_memory_db, month_start)
    # Assert that "Ready to Assign" increased by the transaction amount.
    assert updated_ready == baseline_ready + 50000


def test_edit_transaction_closes_previous_version(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that editing an existing transaction (by reusing its concept_id)
    correctly deactivates the previous version, leaving only one active version.
    """
    service = TransactionEntryService()
    first_cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-1000,
    )
    # Create the initial version of the transaction.
    first = service.create(in_memory_db, first_cmd)

    edit_cmd = NewTransactionRequest(
        concept_id=first.concept_id,  # Reuse concept_id to edit.
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-2000,
        status="cleared",
    )
    # Create an updated version of the transaction.
    updated = service.create(in_memory_db, edit_cmd)

    # Assert the status of the new version.
    assert updated.status == "cleared"

    # Query to count active transaction versions for the given concept_id.
    counts = _fetch_namespace(
        in_memory_db,
        """
        SELECT
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
        FROM transactions
        WHERE concept_id = ?
        """,
        [str(first.concept_id)],
    )
    # Assert that only one active version exists for this concept.
    assert counts.active_rows == 1

    # Verify the status of the latest transaction version directly.
    status_row = _fetch_namespace(
        in_memory_db,
        "SELECT status FROM transactions WHERE transaction_version_id = ?",
        [str(updated.transaction_version_id)],
    )
    assert status_row.status == "cleared"


def test_edit_transaction_failure_rolls_back(
    in_memory_db: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Verifies that if an update to a transaction fails, all changes
    (including the deactivation of the previous version) are rolled back,
    and the database state remains unchanged.
    """
    service = TransactionEntryService()
    first_cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-1000,
    )
    # Create an initial transaction which will be "edited".
    first = service.create(in_memory_db, first_cmd)
    month_start = date.today().replace(day=1)

    # Record baseline account balance and category state before the failing edit.
    baseline_balance_row = _fetch_namespace(
        in_memory_db,
        "SELECT current_balance_minor FROM accounts WHERE account_id = ?",
        ["house_checking"],
    )
    baseline_balance = int(baseline_balance_row.current_balance_minor)

    baseline_category_row = _fetch_namespace(
        in_memory_db,
        """
        SELECT available_minor, activity_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        ["groceries", month_start],
    )
    baseline_available = int(baseline_category_row.available_minor)
    baseline_activity = int(baseline_category_row.activity_minor)

    failing_cmd = NewTransactionRequest(
        concept_id=first.concept_id,
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-2000,
    )

    # Monkeypatch the `insert_transaction` method to simulate a failure.
    original_insert = BudgetingDAO.insert_transaction
    error_message = "forced failure for atomicity"
    tripped = {"value": False}

    def failing_insert(
        self: BudgetingDAO,
        transaction_version_id: UUID,
        concept_id: UUID,
        account_id: str,
        category_id: str,
        transaction_date: date,
        amount_minor: int,
        memo: str | None,
        status: str,
        recorded_at: datetime,
        source: str,
    ) -> None:
        # Raise an exception only for the specific failing command.
        if not tripped["value"] and concept_id == failing_cmd.concept_id:
            tripped["value"] = True
            raise RuntimeError(error_message)
        # Otherwise, call the original insert method.
        original_insert(
            self,
            transaction_version_id,
            concept_id,
            account_id,
            category_id,
            transaction_date,
            amount_minor,
            memo,
            status,
            recorded_at,
            source,
        )

    monkeypatch.setattr(BudgetingDAO, "insert_transaction", failing_insert)

    # Attempt the failing transaction and assert that the expected error is raised.
    with pytest.raises(RuntimeError, match=error_message):
        service.create(in_memory_db, failing_cmd)

    # Verify that the previous version of the transaction is still active (rollback successful).
    counts = _fetch_namespace(
        in_memory_db,
        """
        SELECT SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
        FROM transactions
        WHERE concept_id = ?
        """,
        [str(first.concept_id)],
    )
    assert counts.active_rows == 1

    # Verify that the account balance has been rolled back to its baseline.
    reloaded_balance_row = _fetch_namespace(
        in_memory_db,
        "SELECT current_balance_minor FROM accounts WHERE account_id = ?",
        ["house_checking"],
    )
    assert int(reloaded_balance_row.current_balance_minor) == baseline_balance

    # Verify that the category state has been rolled back to its baseline.
    reloaded_category_row = _fetch_namespace(
        in_memory_db,
        """
        SELECT available_minor, activity_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        ["groceries", month_start],
    )
    assert int(reloaded_category_row.available_minor) == baseline_available
    assert int(reloaded_category_row.activity_minor) == baseline_activity


def test_zero_amount_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies that creating a transaction with a zero `amount_minor` is rejected.
    """
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=0,  # Zero amount
    )
    # Assert that an InvalidTransactionError error is raised.
    with pytest.raises(InvalidTransactionError):
        service.create(in_memory_db, cmd)


def test_list_recent_transactions_returns_latest_first(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that `list_recent_transactions` returns transactions ordered by
    `recorded_at` in descending order (latest first).
    """
    service = TransactionEntryService()
    # Create a first transaction.
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
    # Create a second transaction (later than the first).
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

    # List recent transactions with a limit.
    rows = service.list_recent(in_memory_db, limit=5)
    assert rows
    # Assert that the second (most recent) transaction appears first in the list.
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
    """
    Helper function to insert an account directly into the database for testing.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    account_id : str
        Unique identifier for the account.
    name : str
        Name of the account.
    account_type : str
        Type of the account (e.g., "asset", "liability").
    account_class : str
        Class of the account (e.g., "cash", "investment").
    account_role : str
        Role of the account (e.g., "on_budget", "tracking").
    balance_minor : int
        Initial balance in minor units.
    """
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
    """
    Helper function to insert a budget category directly into the database for testing.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    category_id : str
        Unique identifier for the category.
    name : str
        Name of the category.
    """
    conn.execute(
        """
        INSERT INTO budget_categories (category_id, name, is_active)
        VALUES (?, ?, TRUE)
        ON CONFLICT (category_id) DO UPDATE SET name = EXCLUDED.name, is_active = TRUE
        """,
        [category_id, name],
    )


def test_transfer_cash_to_investment_updates_balances(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that transferring funds from a cash account to an investment account
    correctly updates both account balances and impacts the budgeting category.
    """
    # Insert a new investment account.
    insert_account(
        in_memory_db,
        "house_investment",
        "House Investment",
        "asset",
        "investment",
        "tracking",
        0,
    )
    # Insert an 'Investments' category.
    insert_category(in_memory_db, "investments", "Investments")

    service = TransactionEntryService()
    amount = 20000  # 200.00 USD
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

    # Verify that two transaction records were created for the transfer.
    rows = in_memory_db.execute(
        "SELECT COUNT(*) FROM transactions WHERE concept_id = ?",
        [str(response.concept_id)],
    ).fetchone()
    assert rows is not None
    assert rows[0] == 2

    # Fetch updated account balances.
    checking = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'"
    ).fetchone()
    investment = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_investment'"
    ).fetchone()
    assert checking is not None
    assert investment is not None
    # Assert balances reflect the transfer.
    assert checking[0] == 500000 - amount
    assert investment[0] == amount
    # Assert category available minor reflects the outflow.
    assert response.category.available_minor == -amount


def test_transfer_cash_to_liability_updates_category_state(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that transferring funds from a cash account to a liability account
    (e.g., paying down a loan) correctly updates the liability balance and
    impacts the budgeting category.
    """
    # Insert a new loan liability account.
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
    amount = 15000  # 150.00 USD
    response = service.transfer(
        in_memory_db,
        CategorizedTransferRequest(
            source_account_id="house_checking",
            destination_account_id="house_loan",
            category_id="groceries",  # Using 'groceries' as an example category.
            amount_minor=amount,
            transaction_date=date.today(),
            memo="Pay down loan",
        ),
    )

    # Fetch updated liability account balance.
    liability = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_loan'"
    ).fetchone()
    assert liability is not None
    # Assert liability balance decreased by the transfer amount.
    assert liability[0] == 400000 - amount
    # Assert category available minor reflects the outflow.
    assert response.category.available_minor == -amount


def test_allocate_envelope_blocked_for_system_categories(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that attempts to allocate funds to system categories are blocked.
    System categories are not meant to receive direct allocations.
    """
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)

    # Attempt to allocate to 'opening_balance' (a system category).
    with pytest.raises(InvalidTransactionError):
        service.allocate_envelope(in_memory_db, "opening_balance", 1000, month_start)

    # Attempt to reallocate from 'opening_balance' (a system category).
    with pytest.raises(InvalidTransactionError):
        service.allocate_envelope(
            in_memory_db,
            "groceries",
            500,
            month_start,
            from_category_id="opening_balance",
        )


def test_allocate_envelope_updates_ready_to_assign(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that allocating funds from "Ready to Assign" correctly
    decreases the "Ready to Assign" amount for the current month.
    """
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    # Get baseline "Ready to Assign" amount.
    baseline_ready = service.ready_to_assign(in_memory_db, month_start)

    # Allocate funds to a category.
    category_state = service.allocate_envelope(in_memory_db, "groceries", 5000, month_start)

    # Assert that the category's available funds increased.
    assert category_state.available_minor == 5000
    # Get updated "Ready to Assign" amount.
    updated_ready = service.ready_to_assign(in_memory_db, month_start)
    # Assert that "Ready to Assign" decreased by the allocated amount.
    assert updated_ready == baseline_ready - 5000


def test_allocate_envelope_blocks_when_ready_insufficient(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that allocating more funds than available in "Ready to Assign" is blocked.
    """
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    # Get the current "Ready to Assign" amount.
    ready_minor = service.ready_to_assign(in_memory_db, month_start)
    # Attempt to allocate an amount greater than what's available.
    with pytest.raises(InvalidTransactionError):
        service.allocate_envelope(in_memory_db, "groceries", ready_minor + 100, month_start)


def test_reassign_between_categories_updates_both_states(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that reassigning funds between two categories correctly updates
    the available balances of both source and destination categories.
    """
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    # Allocate initial funds to 'groceries'.
    service.allocate_envelope(in_memory_db, "groceries", 5000, month_start)

    # Reassign funds from 'groceries' to 'housing'.
    service.allocate_envelope(
        in_memory_db,
        "housing",
        2000,  # Amount to reassign.
        month_start,
        from_category_id="groceries",
        memo="cover rent",
    )

    # Fetch updated available funds for both categories directly from the database.
    groceries_state = _fetch_namespace(
        in_memory_db,
        "SELECT available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",
        ["groceries", month_start],
    )
    housing_state = _fetch_namespace(
        in_memory_db,
        "SELECT available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",
        ["housing", month_start],
    )
    # Assert that 'groceries' available decreased by 2000, and 'housing' available increased by 2000.
    assert groceries_state.available_minor == 3000  # 5000 - 2000
    assert housing_state.available_minor == 2000
    # Verify the allocation ledger entry details.
    ledger_row = _fetch_namespace(
        in_memory_db,
        (
            "SELECT to_category_id, from_category_id, amount_minor, memo FROM budget_allocations "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        [],
    )
    assert ledger_row.to_category_id == "housing"
    assert ledger_row.from_category_id == "groceries"
    assert ledger_row.amount_minor == 2000
    assert ledger_row.memo == "cover rent"


def test_month_cash_inflow_counts_cash_accounts_only(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that `month_cash_inflow` correctly aggregates inflows only from
    cash-type accounts that are "on_budget".
    """
    service = TransactionEntryService()
    month_start = date.today().replace(day=1)
    # Create an inflow transaction into a cash account.
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="income",
            amount_minor=60000,
        ),
    )
    # Create an outflow transaction from a cash account (should not affect inflow calculation).
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-1000,
        ),
    )
    # Insert a non-cash (investment) account that is "tracking" and not "on_budget".
    insert_account(
        in_memory_db,
        "external_brokerage",
        "External Brokerage",
        "asset",
        "investment",
        "tracking",
        0,
    )
    # Create an inflow transaction into the non-cash account (should not be counted towards cash inflow).
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="external_brokerage",
            category_id="income",
            amount_minor=40000,
        ),
    )

    # Get the total cash inflow for the month.
    inflow = service.month_cash_inflow(in_memory_db, month_start)
    # Assert that only the inflow from the on-budget cash account is counted.
    assert inflow == 60000


def test_transfer_investment_to_cash_treated_as_income(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verifies that a transfer from an investment account to a cash account
    is correctly treated as income into the cash account and impacts category activity.
    """
    # Insert an investment account with an initial balance.
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
            category_id="income",  # Categorized as income.
            amount_minor=amount,
            transaction_date=date.today(),
            memo="Rebalance to checking",
        ),
    )

    # Fetch updated account balances.
    investment_balance = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_investment'"
    ).fetchone()
    checking_balance = in_memory_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'house_checking'"
    ).fetchone()
    assert investment_balance is not None
    assert checking_balance is not None
    # Assert investment account balance decreased.
    assert investment_balance[0] == 50000 - amount
    # Assert checking account balance increased by the transfer amount.
    assert checking_balance[0] == 500000 + amount
    # Assert category activity reflects the inflow amount.
    assert response.category.activity_minor == amount


def test_ready_to_assign_with_activity(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    """
    Verifies the calculation of "Ready to Assign" (RTA) in the presence of spending activity.

    This test confirms how `ready_to_assign` reflects the overall cash in on-budget accounts
    after a transaction, illustrating a specific interpretation of RTA within this system.

    Notes
    -----
    The `ready_to_assign` value calculated by the system, as reflected in this test,
    appears to represent the initial total cash in on-budget accounts before any spending,
    plus net income, and then adjusted by allocated amounts to categories.
    However, the test's assertion explicitly calculates `expected = expected_cash + (-amount)`,
    where `expected_cash` is the total cash *after* the transaction, and `(-amount)`
    effectively re-adds the absolute value of the spending. This results in the `ready_to_assign`
    value being equal to the initial total on-budget cash *before* any transactions.
    This behavior might deviate from common budgeting software (e.g., YNAB)
    where spending reduces the "Ready to Assign" amount or reduces the amount available
    within a category. This test documents the current system's behavior.
    """
    service = TransactionEntryService()
    amount = -10000  # A spending transaction amount.
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

    # Calculate expected cash in on-budget accounts after the transaction.
    # Initial 'house_checking' balance: 500,000. 'house_savings' balance: 1,250,000.
    # Total initial on-budget cash: 1,750,000.
    # After spending -10,000 from 'house_checking', its balance becomes 490,000.
    # `expected_cash` then correctly reflects the total current cash in on-budget accounts:
    # 490,000 (checking) + 1,250,000 (savings) = 1,740,000.
    expected_cash = 500000 + 1250000 + amount  # This evaluates to 1,740,000.

    # The assertion `assert ready == expected_cash + (-amount)` then computes:
    # 1,740,000 + (-(-10,000)) = 1,740,000 + 10,000 = 1,750,000.
    # This means the test effectively asserts that `ready_to_assign` equals the
    # initial total cash balance of on-budget accounts before the spending occurred.
    expected = expected_cash + (-amount)
    assert ready == expected
