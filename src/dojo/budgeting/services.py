"""Budgeting domain services."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Tuple
from uuid import UUID, uuid4

import duckdb

from dojo.budgeting.errors import (
    AccountAlreadyExists,
    AccountNotFound,
    CategoryAlreadyExists,
    CategoryNotFound,
    InvalidTransaction,
    UnknownAccount,
    UnknownCategory,
)
from dojo.budgeting.schemas import (
    AccountCreateRequest,
    AccountDetail,
    AccountState,
    AccountUpdateRequest,
    BudgetCategoryCreateRequest,
    BudgetCategoryDetail,
    BudgetCategoryUpdateRequest,
    CategoryState,
    NewTransactionRequest,
    TransactionListItem,
    TransactionResponse,
)
from dojo.budgeting.sql import load_sql


class TransactionEntryService:
    """Insert and manage ledger transactions."""

    MAX_FUTURE_DAYS = 5
    SOURCE = "api"

    def create(self, conn: duckdb.DuckDBPyConnection, cmd: NewTransactionRequest) -> TransactionResponse:
        """Insert a transaction using the temporal ledger model."""

        self._validate_payload(cmd)
        concept_id = cmd.concept_id or uuid4()
        transaction_version_id = uuid4()
        recorded_at = datetime.now(timezone.utc)
        month_start = cmd.transaction_date.replace(day=1)
        activity_delta = -cmd.amount_minor

        conn.execute("BEGIN")
        try:
            account_row = self._fetch_account(conn, cmd.account_id)
            category_row = self._fetch_category(conn, cmd.category_id)

            if cmd.concept_id is not None:
                close_sql = load_sql("close_active_transaction.sql")
                conn.execute(
                    close_sql,
                    [recorded_at, recorded_at, str(concept_id)],
                )

            insert_sql = load_sql("insert_transaction.sql")
            conn.execute(
                insert_sql,
                [
                    str(transaction_version_id),
                    str(concept_id),
                    cmd.account_id,
                    cmd.category_id,
                    cmd.transaction_date,
                    cmd.amount_minor,
                    cmd.memo,
                    recorded_at,
                    recorded_at,
                    self.SOURCE,
                ],
            )

            update_account_sql = load_sql("update_account_balance.sql")
            conn.execute(
                update_account_sql,
                [cmd.amount_minor, cmd.amount_minor, cmd.account_id],
            )

            upsert_category_sql = load_sql("upsert_category_monthly_state.sql")
            conn.execute(
                upsert_category_sql,
                [cmd.category_id, month_start, activity_delta, activity_delta],
            )

            account_state = self._account_state_from_row(
                self._fetch_account(conn, cmd.account_id)
            )
            category_state = self._fetch_category_month_state(conn, cmd.category_id, month_start)

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        return TransactionResponse(
            transaction_version_id=transaction_version_id,
            concept_id=concept_id,
            amount_minor=cmd.amount_minor,
            transaction_date=cmd.transaction_date,
            memo=cmd.memo,
            account=account_state,
            category=category_state,
        )

    def list_recent(
        self,
        conn: duckdb.DuckDBPyConnection,
        limit: int,
    ) -> list[TransactionListItem]:
        sql = load_sql("select_recent_transactions.sql")
        rows = conn.execute(sql, [limit]).fetchall()
        return [
            TransactionListItem(
                transaction_version_id=row[0],
                concept_id=row[1],
                transaction_date=row[2],
                account_id=row[3],
                account_name=row[4],
                category_id=row[5],
                category_name=row[6],
                amount_minor=int(row[7]),
                memo=row[8],
                recorded_at=row[9],
            )
            for row in rows
        ]

    def _validate_payload(self, cmd: NewTransactionRequest) -> None:
        if cmd.amount_minor == 0:
            raise InvalidTransaction("amount_minor must be non-zero.")
        future_delta = (cmd.transaction_date - date.today()).days
        if future_delta > self.MAX_FUTURE_DAYS:
            raise InvalidTransaction(
                f"transaction_date may not be more than {self.MAX_FUTURE_DAYS} days in the future."
            )

    def _fetch_account(self, conn: duckdb.DuckDBPyConnection, account_id: str) -> Tuple[Any, ...]:
        sql = load_sql("select_active_account.sql")
        row = conn.execute(sql, [account_id]).fetchone()
        if row is None or not row[5]:
            raise UnknownAccount(f"Account `{account_id}` is not active.")
        return row

    def _account_state_from_row(self, row) -> AccountState:
        return AccountState(
            account_id=row[0],
            name=row[1],
            current_balance_minor=int(row[3]),
        )

    def _fetch_category(self, conn: duckdb.DuckDBPyConnection, category_id: str) -> Tuple[Any, ...]:
        sql = load_sql("select_active_category.sql")
        row = conn.execute(sql, [category_id]).fetchone()
        if row is None or not row[2]:
            raise UnknownCategory(f"Category `{category_id}` is not active.")
        return row

    def _fetch_category_month_state(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        month_start: date,
    ) -> CategoryState:
        sql = load_sql("select_category_month_state.sql")
        row = conn.execute(sql, [month_start, category_id]).fetchone()
        if row is None:
            # Should not happen because category existence validated.
            return CategoryState(category_id=category_id, name="Unknown", available_minor=0)
        return CategoryState(
            category_id=row[0],
            name=row[1],
            available_minor=int(row[2]),
        )


class AccountAdminService:
    """Manage CRUD flows for accounts exposed to the SPA."""

    def list_accounts(self, conn: duckdb.DuckDBPyConnection) -> list[AccountDetail]:
        sql = load_sql("select_accounts_admin.sql")
        rows = conn.execute(sql).fetchall()
        return [self._row_to_account(row) for row in rows]

    def create_account(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: AccountCreateRequest,
    ) -> AccountDetail:
        if self._fetch_account_optional(conn, payload.account_id) is not None:
            raise AccountAlreadyExists(f"Account `{payload.account_id}` already exists.")

        currency = payload.currency.upper()
        sql = load_sql("insert_account.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(
                sql,
                [
                    payload.account_id,
                    payload.name,
                    payload.account_type,
                    payload.current_balance_minor,
                    currency,
                    payload.is_active,
                    payload.opened_on,
                ],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self._require_account(conn, payload.account_id)

    def update_account(
        self,
        conn: duckdb.DuckDBPyConnection,
        account_id: str,
        payload: AccountUpdateRequest,
    ) -> AccountDetail:
        self._require_account(conn, account_id)
        currency = payload.currency.upper()
        sql = load_sql("update_account.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(
                sql,
                [
                    payload.name,
                    payload.account_type,
                    payload.current_balance_minor,
                    currency,
                    payload.opened_on,
                    payload.is_active,
                    account_id,
                ],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self._require_account(conn, account_id)

    def deactivate_account(self, conn: duckdb.DuckDBPyConnection, account_id: str) -> None:
        self._require_account(conn, account_id)
        sql = load_sql("deactivate_account.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(sql, [account_id])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _require_account(self, conn: duckdb.DuckDBPyConnection, account_id: str) -> AccountDetail:
        row = self._fetch_account_optional(conn, account_id)
        if row is None:
            raise AccountNotFound(f"Account `{account_id}` was not found.")
        return self._row_to_account(row)

    def _fetch_account_optional(
        self, conn: duckdb.DuckDBPyConnection, account_id: str
    ) -> Tuple[Any, ...] | None:
        sql = load_sql("select_account_detail.sql")
        return conn.execute(sql, [account_id]).fetchone()

    def _row_to_account(self, row: Tuple[Any, ...]) -> AccountDetail:
        return AccountDetail(
            account_id=row[0],
            name=row[1],
            account_type=row[2],
            current_balance_minor=int(row[3]),
            currency=row[4],
            is_active=bool(row[5]),
            opened_on=row[6],
            created_at=row[7],
            updated_at=row[8],
        )


class BudgetCategoryAdminService:
    """CRUD surface for budget categories."""

    def list_categories(self, conn: duckdb.DuckDBPyConnection) -> list[BudgetCategoryDetail]:
        sql = load_sql("select_budget_categories_admin.sql")
        rows = conn.execute(sql).fetchall()
        return [self._row_to_category(row) for row in rows]

    def create_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryCreateRequest,
    ) -> BudgetCategoryDetail:
        if self._fetch_category_optional(conn, payload.category_id) is not None:
            raise CategoryAlreadyExists(f"Category `{payload.category_id}` already exists.")
        sql = load_sql("insert_budget_category.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(sql, [payload.category_id, payload.name, payload.is_active])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self._require_category(conn, payload.category_id)

    def update_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        payload: BudgetCategoryUpdateRequest,
    ) -> BudgetCategoryDetail:
        self._require_category(conn, category_id)
        sql = load_sql("update_budget_category.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(sql, [payload.name, payload.is_active, category_id])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self._require_category(conn, category_id)

    def deactivate_category(self, conn: duckdb.DuckDBPyConnection, category_id: str) -> None:
        self._require_category(conn, category_id)
        sql = load_sql("deactivate_budget_category.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(sql, [category_id])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _require_category(
        self, conn: duckdb.DuckDBPyConnection, category_id: str
    ) -> BudgetCategoryDetail:
        row = self._fetch_category_optional(conn, category_id)
        if row is None:
            raise CategoryNotFound(f"Category `{category_id}` was not found.")
        return self._row_to_category(row)

    def _fetch_category_optional(
        self, conn: duckdb.DuckDBPyConnection, category_id: str
    ) -> Tuple[Any, ...] | None:
        sql = load_sql("select_budget_category_detail.sql")
        return conn.execute(sql, [category_id]).fetchone()

    def _row_to_category(self, row: Tuple[Any, ...]) -> BudgetCategoryDetail:
        return BudgetCategoryDetail(
            category_id=row[0],
            name=row[1],
            is_active=bool(row[2]),
            created_at=row[3],
            updated_at=row[4],
        )
