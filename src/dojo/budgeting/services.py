"""Budgeting domain services."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal, Optional, Tuple
from uuid import UUID, uuid4

import duckdb

from dojo.budgeting.errors import (
    AccountAlreadyExists,
    AccountNotFound,
    BudgetingError,
    CategoryAlreadyExists,
    CategoryNotFound,
    GroupAlreadyExists,
    GroupNotFound,
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
    BudgetCategoryGroupCreateRequest,
    BudgetCategoryGroupDetail,
    BudgetCategoryGroupUpdateRequest,
    BudgetCategoryUpdateRequest,
    CategoryState,
    CategorizedTransferLeg,
    CategorizedTransferRequest,
    CategorizedTransferResponse,
    NewTransactionRequest,
    TransactionListItem,
    TransactionResponse,
)
from dojo.budgeting.sql import load_sql


class TransactionEntryService:
    """Insert and manage ledger transactions."""

    MAX_FUTURE_DAYS = 5
    SOURCE = "api"
    TRANSFER_CATEGORY_ID = "account_transfer"

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

            self._insert_transaction_row(
                conn=conn,
                transaction_version_id=transaction_version_id,
                concept_id=concept_id,
                account_id=cmd.account_id,
                category_id=cmd.category_id,
                transaction_date=cmd.transaction_date,
                amount_minor=cmd.amount_minor,
                memo=cmd.memo,
                status=cmd.status,
                recorded_at=recorded_at,
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
            status=cmd.status,
            memo=cmd.memo,
            account=account_state,
            category=category_state,
        )

    def transfer(
        self,
        conn: duckdb.DuckDBPyConnection,
        cmd: CategorizedTransferRequest,
    ) -> CategorizedTransferResponse:
        """Perform a categorized transfer with two ledger entries."""

        self._validate_transfer_payload(cmd)
        if cmd.source_account_id == cmd.destination_account_id:
            raise InvalidTransaction("Source and destination accounts must differ.")
        concept_id = cmd.concept_id or uuid4()
        recorded_at = datetime.now(timezone.utc)
        month_start = cmd.transaction_date.replace(day=1)
        source_amount = -cmd.amount_minor
        destination_amount = cmd.amount_minor

        conn.execute("BEGIN")
        try:
            source_row = self._fetch_account(conn, cmd.source_account_id)
            destination_row = self._fetch_account(conn, cmd.destination_account_id)
            category_row = self._fetch_category(conn, cmd.category_id)

            budget_leg_id = uuid4()
            transfer_leg_id = uuid4()

            self._insert_transaction_row(
                conn=conn,
                transaction_version_id=budget_leg_id,
                concept_id=concept_id,
                account_id=cmd.source_account_id,
                category_id=cmd.category_id,
                transaction_date=cmd.transaction_date,
                amount_minor=source_amount,
                memo=cmd.memo,
                status="cleared",
                recorded_at=recorded_at,
            )
            update_account_sql = load_sql("update_account_balance.sql")
            conn.execute(
                update_account_sql,
                [source_amount, source_amount, cmd.source_account_id],
            )

            self._insert_transaction_row(
                conn=conn,
                transaction_version_id=transfer_leg_id,
                concept_id=concept_id,
                account_id=cmd.destination_account_id,
                category_id=self.TRANSFER_CATEGORY_ID,
                transaction_date=cmd.transaction_date,
                amount_minor=destination_amount,
                memo=cmd.memo,
                status="cleared",
                recorded_at=recorded_at,
            )
            conn.execute(
                update_account_sql,
                [destination_amount, destination_amount, cmd.destination_account_id],
            )

            upsert_category_sql = load_sql("upsert_category_monthly_state.sql")
            activity_delta = -source_amount
            conn.execute(
                upsert_category_sql,
                [cmd.category_id, month_start, activity_delta, activity_delta],
            )

            source_state = self._account_state_from_row(self._fetch_account(conn, cmd.source_account_id))
            destination_state = self._account_state_from_row(self._fetch_account(conn, cmd.destination_account_id))
            category_state = self._fetch_category_month_state(conn, cmd.category_id, month_start)

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        return CategorizedTransferResponse(
            concept_id=concept_id,
            budget_leg=CategorizedTransferLeg(
                transaction_version_id=budget_leg_id,
                account=source_state,
            ),
            transfer_leg=CategorizedTransferLeg(
                transaction_version_id=transfer_leg_id,
                account=destination_state,
            ),
            category=category_state,
        )

    def ready_to_assign(self, conn: duckdb.DuckDBPyConnection, month_start: date) -> int:
        sql = load_sql("select_ready_to_assign.sql")
        row = conn.execute(sql, [month_start]).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def allocate_envelope(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        amount_minor: int,
        month_start: date | None = None,
        *,
        from_category_id: str | None = None,
        memo: str | None = None,
        allocation_date: date | None = None,
    ) -> CategoryState:
        if amount_minor <= 0:
            raise InvalidTransaction("amount_minor must be positive for allocations.")
        destination_category_id = category_id
        if not destination_category_id:
            raise InvalidTransaction("to_category_id is required for allocations.")
        if from_category_id and from_category_id == destination_category_id:
            raise InvalidTransaction("Source and destination categories must differ.")
        allocation_day = allocation_date or date.today()
        month = (month_start or allocation_day).replace(day=1)
        memo_value = memo.strip() if memo else None

        # Ensure the categories exist and states are available before mutating balances.
        self._fetch_category(conn, destination_category_id)
        source_state: CategoryState | None = None
        if from_category_id:
            self._fetch_category(conn, from_category_id)
            source_state = self._fetch_category_month_state(conn, from_category_id, month)
            if source_state.available_minor < amount_minor:
                raise InvalidTransaction("Source category does not have enough available funds.")
        else:
            ready_minor = self.ready_to_assign(conn, month)
            if ready_minor < amount_minor:
                raise InvalidTransaction("Ready-to-Assign is insufficient for this allocation.")

        adjust_sql = load_sql("adjust_category_allocation.sql")
        insert_sql = load_sql("insert_budget_allocation.sql")
        allocation_id = uuid4()
        conn.execute("BEGIN")
        try:
            conn.execute(
                insert_sql,
                [
                    str(allocation_id),
                    allocation_day,
                    month,
                    from_category_id,
                    destination_category_id,
                    amount_minor,
                    memo_value,
                ],
            )
            conn.execute(
                adjust_sql,
                [destination_category_id, month, amount_minor, amount_minor],
            )
            if from_category_id:
                conn.execute(
                    adjust_sql,
                    [from_category_id, month, -amount_minor, -amount_minor],
                )
            category_state = self._fetch_category_month_state(conn, destination_category_id, month)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return category_state

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
                status=row[8],
                memo=row[9],
                recorded_at=row[10],
            )
            for row in rows
        ]

    def list_allocations(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        sql = load_sql("select_budget_allocations.sql")
        rows = conn.execute(sql, [month_start, limit]).fetchall()
        return [
            {
                "allocation_id": row[0],
                "allocation_date": row[1],
                "amount_minor": int(row[2]),
                "memo": row[3],
                "from_category_id": row[4],
                "from_category_name": row[5],
                "to_category_id": row[6],
                "to_category_name": row[7],
                "created_at": row[8],
            }
            for row in rows
        ]

    def month_cash_inflow(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date,
    ) -> int:
        sql = load_sql("sum_month_cash_inflows.sql")
        row = conn.execute(sql, [month_start, month_start]).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def _validate_payload(self, cmd: NewTransactionRequest) -> None:
        if cmd.amount_minor == 0:
            raise InvalidTransaction("amount_minor must be non-zero.")
        future_delta = (cmd.transaction_date - date.today()).days
        if future_delta > self.MAX_FUTURE_DAYS:
            raise InvalidTransaction(
                f"transaction_date may not be more than {self.MAX_FUTURE_DAYS} days in the future."
            )

    def _validate_transfer_payload(self, cmd: CategorizedTransferRequest) -> None:
        future_delta = (cmd.transaction_date - date.today()).days
        if future_delta > self.MAX_FUTURE_DAYS:
            raise InvalidTransaction(
                f"transaction_date may not be more than {self.MAX_FUTURE_DAYS} days in the future."
            )

    def _insert_transaction_row(
        self,
        conn: duckdb.DuckDBPyConnection,
        transaction_version_id: UUID,
        concept_id: UUID,
        account_id: str,
        category_id: str,
        transaction_date: date,
        amount_minor: int,
        memo: Optional[str],
        status: Literal["pending", "cleared"],
        recorded_at: datetime,
    ) -> None:
        insert_sql = load_sql("insert_transaction.sql")
        conn.execute(
            insert_sql,
            [
                str(transaction_version_id),
                str(concept_id),
                account_id,
                category_id,
                transaction_date,
                amount_minor,
                memo,
                status,
                recorded_at,
                recorded_at,
                self.SOURCE,
            ],
        )

    def _fetch_account(self, conn: duckdb.DuckDBPyConnection, account_id: str) -> Tuple[Any, ...]:
        sql = load_sql("select_active_account.sql")
        row = conn.execute(sql, [account_id]).fetchone()
        if row is None or not row[7]:
            raise UnknownAccount(f"Account `{account_id}` is not active.")
        return row

    def _account_state_from_row(self, row) -> AccountState:
        return AccountState(
            account_id=row[0],
            name=row[1],
            account_type=row[2],
            account_class=row[3],
            account_role=row[4],
            current_balance_minor=int(row[5]),
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
            return CategoryState(
                category_id=category_id,
                name="Unknown",
                available_minor=0,
                activity_minor=0,
            )
        return CategoryState(
            category_id=row[0],
            name=row[1],
            available_minor=int(row[2]),
            activity_minor=int(row[3]),
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
                    payload.account_class,
                    payload.account_role,
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
                    payload.account_class,
                    payload.account_role,
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
            account_class=row[3],
            account_role=row[4],
            current_balance_minor=int(row[5]),
            currency=row[6],
            is_active=bool(row[7]),
            opened_on=row[8],
            created_at=row[9],
            updated_at=row[10],
        )


class BudgetCategoryAdminService:
    """CRUD surface for budget categories."""

    def list_categories(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date | None = None,
    ) -> list[BudgetCategoryDetail]:
        month = self._coerce_month_start(month_start)
        sql = load_sql("select_budget_categories_admin.sql")
        rows = conn.execute(sql, [month]).fetchall()
        return [self._row_to_category(row) for row in rows]

    def create_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryCreateRequest,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        if self._fetch_category_optional(conn, payload.category_id, month_start) is not None:
            raise CategoryAlreadyExists(f"Category `{payload.category_id}` already exists.")
        sql = load_sql("insert_budget_category.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(
                sql,
                [
                    payload.category_id,
                    payload.group_id,
                    payload.name,
                    payload.is_active,
                    payload.goal_type,
                    payload.goal_amount_minor,
                    payload.goal_target_date,
                    payload.goal_frequency,
                ],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self._require_category(conn, payload.category_id, month_start)

    def update_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        payload: BudgetCategoryUpdateRequest,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        self._require_category(conn, category_id, month_start)
        sql = load_sql("update_budget_category.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(
                sql,
                [
                    payload.name,
                    payload.group_id,
                    payload.is_active,
                    payload.goal_type,
                    payload.goal_amount_minor,
                    payload.goal_target_date,
                    payload.goal_frequency,
                    category_id,
                ],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self._require_category(conn, category_id, month_start)

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

    def list_groups(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[BudgetCategoryGroupDetail]:
        sql = load_sql("select_budget_category_groups.sql")
        rows = conn.execute(sql).fetchall()
        return [
            BudgetCategoryGroupDetail(
                group_id=row[0],
                name=row[1],
                sort_order=row[2],
                is_active=bool(row[3]),
                created_at=row[4],
                updated_at=row[5],
            )
            for row in rows
        ]

    def create_group(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryGroupCreateRequest,
    ) -> BudgetCategoryGroupDetail:
        sql = load_sql("insert_budget_category_group.sql")
        conn.execute("BEGIN")
        try:
            row = conn.execute(
                sql,
                [payload.group_id, payload.name, payload.sort_order],
            ).fetchone()
            if row is None:
                raise BudgetingError("Failed to create group")
            conn.execute("COMMIT")
            return BudgetCategoryGroupDetail(
                group_id=row[0],
                name=row[1],
                sort_order=row[2],
                is_active=bool(row[3]),
                created_at=row[4],
                updated_at=row[5],
            )
        except duckdb.ConstraintException as exc:
            conn.execute("ROLLBACK")
            raise GroupAlreadyExists(
                f"Group `{payload.group_id}` already exists."
            ) from exc
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def update_group(
        self,
        conn: duckdb.DuckDBPyConnection,
        group_id: str,
        payload: BudgetCategoryGroupUpdateRequest,
    ) -> BudgetCategoryGroupDetail:
        sql = load_sql("update_budget_category_group.sql")
        conn.execute("BEGIN")
        try:
            row = conn.execute(
                sql,
                [payload.name, payload.sort_order, group_id],
            ).fetchone()
            if row is None:
                raise GroupNotFound(f"Group `{group_id}` not found.")
            conn.execute("COMMIT")
            return BudgetCategoryGroupDetail(
                group_id=row[0],
                name=row[1],
                sort_order=row[2],
                is_active=bool(row[3]),
                created_at=row[4],
                updated_at=row[5],
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def deactivate_group(
        self, conn: duckdb.DuckDBPyConnection, group_id: str
    ) -> None:
        sql = load_sql("deactivate_budget_category_group.sql")
        conn.execute("BEGIN")
        try:
            conn.execute(sql, [group_id])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _require_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        row = self._fetch_category_optional(conn, category_id, month_start)
        if row is None:
            raise CategoryNotFound(f"Category `{category_id}` was not found.")
        return self._row_to_category(row)

    def _fetch_category_optional(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        month_start: date | None = None,
    ) -> Tuple[Any, ...] | None:
        sql = load_sql("select_budget_category_detail.sql")
        month = self._coerce_month_start(month_start)
        return conn.execute(sql, [month, category_id]).fetchone()

    def _row_to_category(self, row: Tuple[Any, ...]) -> BudgetCategoryDetail:
        return BudgetCategoryDetail(
            category_id=row[0],
            group_id=row[1],
            name=row[2],
            is_active=bool(row[3]),
            created_at=row[4],
            updated_at=row[5],
            goal_type=row[6],
            goal_amount_minor=row[7],
            goal_target_date=row[8],
            goal_frequency=row[9],
            available_minor=int(row[10]),
            activity_minor=int(row[11]),
            allocated_minor=int(row[12]),
        )

    @staticmethod
    def _coerce_month_start(month_start: date | None) -> date:
        if month_start is None:
            today = date.today()
            return today.replace(day=1)
        return month_start.replace(day=1)
