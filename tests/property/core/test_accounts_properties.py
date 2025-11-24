"""Property-based tests for accounts service invariants."""

import string
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace
import duckdb
from uuid import uuid4

from hypothesis import given, settings, strategies as st

from dojo.budgeting.schemas import (
    NewTransactionRequest,
    AccountClass,
    AccountCreateRequest,
)
from dojo.budgeting.services import (
    TransactionEntryService,
    AccountAdminService,
    derive_payment_category_id,
    derive_payment_category_name,
)
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create an in-memory DuckDB connection with all migrations and base fixtures applied."""
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    apply_base_budgeting_fixture(conn)
    try:
        yield conn
    finally:
        conn.close()


def build_transaction_service() -> TransactionEntryService:
    return TransactionEntryService()


def build_account_admin_service() -> AccountAdminService:
    return AccountAdminService()


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> SimpleNamespace:
    cursor = conn.execute(sql, params or [])
    row = cursor.fetchone()
    assert row is not None
    columns = [column[0] for column in cursor.description or ()]
    data = {columns[idx]: row[idx] for idx in range(len(columns))}
    return SimpleNamespace(**data)


# Strategies
account_id_strategy = st.text(
    min_size=3, max_size=20, alphabet=string.ascii_lowercase + string.digits + "_"
)
account_name_strategy = st.text(min_size=3, max_size=50)
account_class_strategy = st.sampled_from([c for c in AccountClass.__args__ if c not in ["tangible", "accessible"]])
amount_strategy = st.integers(min_value=-50_000, max_value=50_000).filter(lambda x: x != 0)


@st.composite
def cash_account_strategy(draw):
    return {
        "account_id": draw(account_id_strategy),
        "name": draw(account_name_strategy),
        "account_type": "asset",
        "account_class": "cash",
        "account_role": "on_budget",
        "current_balance_minor": 0,
        "currency": "USD",
        "is_active": True,
        "opened_on": date.today(),
    }


@st.composite
def account_create_request_strategy(draw):
    account_class = draw(account_class_strategy)
    account_type = "liability" if account_class in ["credit", "loan"] else "asset"
    return AccountCreateRequest(
        account_id=draw(account_id_strategy),
        name=draw(account_name_strategy),
        account_type=account_type,
        account_class=account_class,
        account_role="on_budget",
        current_balance_minor=0,
        currency="USD",
        is_active=True,
        opened_on=date.today(),
    )


@st.composite
def credit_account_create_request_strategy(draw):
    return AccountCreateRequest(
        account_id=draw(account_id_strategy),
        name=draw(account_name_strategy),
        account_type="liability",
        account_class="credit",
        account_role="on_budget",
        current_balance_minor=0,
        currency="USD",
        is_active=True,
        opened_on=date.today(),
    )


DETAIL_TABLES = {
    "cash": "cash_account_details",
    "credit": "credit_account_details",
    "investment": "investment_account_details",
    "loan": "loan_account_details",
    # "tangible": "tangible_asset_details",
    # "accessible": "accessible_asset_details",
}


@given(
    account_data=cash_account_strategy(),
    initial_balance=st.integers(min_value=-100000, max_value=100000),
    transactions=st.lists(amount_strategy, min_size=1, max_size=10),
)
@settings(max_examples=10, deadline=None)
def test_balance_synchronization(account_data, initial_balance, transactions):
    """
    Verify that accounts.current_balance_minor is always equal to the sum
    of the corresponding transactions.
    """
    with ledger_connection() as conn:
        transaction_service = build_transaction_service()

        # Manually create account because service does not handle details tables.
        conn.execute(
            """
            INSERT INTO accounts (account_id, name, account_type, account_class, account_role, current_balance_minor, currency, is_active, opened_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(account_data.values()),
        )
        conn.execute(
            """
            INSERT INTO cash_account_details (detail_id, account_id) VALUES (?, ?)
            """,
            [str(uuid4()), account_data["account_id"]],
        )

        # 1. Create opening balance transaction.
        if initial_balance != 0:
            transaction_service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id=account_data["account_id"],
                    category_id="opening_balance",
                    amount_minor=initial_balance,
                ),
            )

        # 2. Create a series of transactions.
        for amount in transactions:
            transaction_service.create(
                conn,
                NewTransactionRequest(
                    transaction_date=date.today(),
                    account_id=account_data["account_id"],
                    category_id="groceries",  # An arbitrary existing category
                    amount_minor=amount,
                ),
            )

        # 3. Verify final balance.
        final_balance_row = _fetch_namespace(
            conn,
            "SELECT current_balance_minor FROM accounts WHERE account_id = ?",
            [account_data["account_id"]],
        )
        final_balance = final_balance_row.current_balance_minor

        total_transactions_row = _fetch_namespace(
            conn,
            "SELECT SUM(amount_minor) AS total_amount_minor FROM transactions WHERE account_id = ?",
            [account_data["account_id"]],
        )
        total_transactions = total_transactions_row.total_amount_minor

        assert final_balance == total_transactions


@given(payload=account_create_request_strategy())
@settings(max_examples=10, deadline=None)
def test_one_to_one_account_details(payload: AccountCreateRequest):
    """
    Verify that every account in the `accounts` table has exactly one
    corresponding record in one of the `*_account_details` tables.
    NOTE: This test is expected to fail, as the service does not currently
    create entries in the details tables.
    """
    with ledger_connection() as conn:
        service = build_account_admin_service()
        service.create_account(conn, payload)

        target_table = DETAIL_TABLES[payload.account_class]

        # Check that the target detail table has the record.
        count_row = _fetch_namespace(
            conn,
            f"SELECT COUNT(*) AS row_count FROM {target_table} WHERE account_id = ?",
            [payload.account_id],
        )
        assert count_row.row_count == 1, f"Expected 1 record in {target_table}, found {count_row.row_count}"

        # Check that other detail tables do not have the record.
        for account_class, detail_table in DETAIL_TABLES.items():
            if account_class == payload.account_class:
                continue
            count_row = _fetch_namespace(
                conn,
                f"SELECT COUNT(*) AS row_count FROM {detail_table} WHERE account_id = ?",
                [payload.account_id],
            )
            assert count_row.row_count == 0, f"Expected 0 records in {detail_table}, found {count_row.row_count}"


@given(payload=credit_account_create_request_strategy())
@settings(max_examples=10, deadline=None)
def test_credit_account_creates_payment_category(payload: AccountCreateRequest):
    """
    For every `credit` class account, a corresponding "payment" category
    must exist in the `budget_categories` table.
    """
    with ledger_connection() as conn:
        service = build_account_admin_service()
        service.create_account(conn, payload)

        expected_category_id = derive_payment_category_id(payload.account_id)
        expected_category_name = derive_payment_category_name(payload.name)
        
        category_row = _fetch_namespace(
            conn,
            "SELECT name, group_id FROM budget_categories WHERE category_id = ?",
            [expected_category_id],
        )

        assert category_row.name == expected_category_name, "Payment category was not created"
        assert category_row.group_id == "credit_card_payments"
        
        group_row = _fetch_namespace(
            conn,
            "SELECT name FROM budget_category_groups WHERE group_id = 'credit_card_payments'",
        )
        
        assert group_row.name == "Credit Card Payments", "Credit card payment group does not exist"


