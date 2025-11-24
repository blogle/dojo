"""Data access helpers for the budgeting domain."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from types import SimpleNamespace
from typing import Any, Generator, Literal, Sequence, cast
from uuid import UUID, uuid4

import duckdb

from dojo.budgeting.schemas import AccountClass, AccountRole
from dojo.budgeting.sql import load_sql


@lru_cache(maxsize=None)
def _sql(name: str) -> str:
    return load_sql(name)


def _row_to_namespace(
    description: Sequence[tuple[Any, ...]] | None,
    row: Sequence[Any],
) -> SimpleNamespace:
    if description is None:
        raise ValueError("Cannot convert row without column metadata.")
    values = {column[0]: row[idx] for idx, column in enumerate(description)}
    return SimpleNamespace(**values)


@dataclass(frozen=True)
class AccountRecord:
    account_id: str
    name: str
    account_type: Literal["asset", "liability"]
    account_class: AccountClass
    account_role: AccountRole
    current_balance_minor: int
    currency: str
    is_active: bool
    opened_on: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "AccountRecord":
        opened_on = getattr(row, "opened_on", None)
        created_at = getattr(row, "created_at", None)
        updated_at = getattr(row, "updated_at", None)
        currency_value = getattr(row, "currency", "USD")
        return cls(
            account_id=str(row.account_id),
            name=str(row.name),
            account_type=cast(Literal["asset", "liability"], str(row.account_type)),
            account_class=cast(AccountClass, str(row.account_class)),
            account_role=cast(AccountRole, str(row.account_role)),
            current_balance_minor=int(row.current_balance_minor),
            currency=str(currency_value),
            is_active=bool(getattr(row, "is_active", True)),
            opened_on=opened_on,
            created_at=created_at,
            updated_at=updated_at,
        )

    @property
    def is_credit_liability(self) -> bool:
        return self.account_type == "liability" and self.account_class == "credit"


@dataclass(frozen=True)
class ReferenceAccountRecord:
    account_id: str
    name: str
    account_type: Literal["asset", "liability"]
    account_class: AccountClass
    account_role: AccountRole
    current_balance_minor: int

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "ReferenceAccountRecord":
        return cls(
            account_id=str(row.account_id),
            name=str(row.name),
            account_type=cast(Literal["asset", "liability"], str(row.account_type)),
            account_class=cast(AccountClass, str(row.account_class)),
            account_role=cast(AccountRole, str(row.account_role)),
            current_balance_minor=int(row.current_balance_minor),
        )

    @property
    def is_credit_liability(self) -> bool:
        return self.account_type == "liability" and self.account_class == "credit"


ACCOUNT_DETAIL_INSERTS: dict[AccountClass, str] = {
    "cash": "insert_cash_account_detail.sql",
    "credit": "insert_credit_account_detail.sql",
    "investment": "insert_investment_account_detail.sql",
    "loan": "insert_loan_account_detail.sql",
    "accessible": "insert_accessible_asset_detail.sql",
    "tangible": "insert_tangible_asset_detail.sql",
}


@dataclass(frozen=True)
class CategoryRecord:
    category_id: str
    name: str
    is_active: bool
    is_system: bool

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "CategoryRecord":
        return cls(
            category_id=str(row.category_id),
            name=str(row.name),
            is_active=bool(getattr(row, "is_active", True)),
            is_system=bool(getattr(row, "is_system", False)),
        )


@dataclass(frozen=True)
class ReferenceCategoryRecord:
    category_id: str
    name: str
    available_minor: int

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "ReferenceCategoryRecord":
        return cls(
            category_id=str(row.category_id),
            name=str(row.name),
            available_minor=int(row.available_minor),
        )


@dataclass(frozen=True)
class CategoryMonthStateRecord:
    category_id: str
    name: str
    available_minor: int
    activity_minor: int

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "CategoryMonthStateRecord":
        return cls(
            category_id=str(row.category_id),
            name=str(row.name),
            available_minor=int(row.available_minor),
            activity_minor=int(row.activity_minor),
        )


@dataclass(frozen=True)
class BudgetCategoryDetailRecord:
    category_id: str
    group_id: str | None
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    goal_type: str | None
    goal_amount_minor: int | None
    goal_target_date: date | None
    goal_frequency: str | None
    available_minor: int
    activity_minor: int
    allocated_minor: int
    last_month_allocated_minor: int = 0
    last_month_activity_minor: int = 0
    last_month_available_minor: int = 0

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "BudgetCategoryDetailRecord":
        last_month_allocated = int(getattr(row, "last_month_allocated_minor", 0) or 0)
        last_month_activity = int(getattr(row, "last_month_activity_minor", 0) or 0)
        last_month_available = int(getattr(row, "last_month_available_minor", 0) or 0)
        group_id = getattr(row, "group_id", None)
        goal_type = getattr(row, "goal_type", None)
        goal_amount_minor = getattr(row, "goal_amount_minor", None)
        goal_frequency = getattr(row, "goal_frequency", None)
        return cls(
            category_id=str(row.category_id),
            group_id=str(group_id) if group_id is not None else None,
            name=str(row.name),
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
            goal_type=str(goal_type) if goal_type is not None else None,
            goal_amount_minor=int(goal_amount_minor) if goal_amount_minor is not None else None,
            goal_target_date=getattr(row, "goal_target_date", None),
            goal_frequency=str(goal_frequency) if goal_frequency is not None else None,
            available_minor=int(row.available_minor),
            activity_minor=int(row.activity_minor),
            allocated_minor=int(row.allocated_minor),
            last_month_allocated_minor=last_month_allocated,
            last_month_activity_minor=last_month_activity,
            last_month_available_minor=last_month_available,
        )


@dataclass(frozen=True)
class BudgetCategoryGroupRecord:
    group_id: str
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "BudgetCategoryGroupRecord":
        return cls(
            group_id=str(row.group_id),
            name=str(row.name),
            sort_order=int(row.sort_order),
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


@dataclass(frozen=True)
class TransactionVersionRecord:
    transaction_version_id: UUID
    account_id: str
    category_id: str
    transaction_date: date
    amount_minor: int
    status: str

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "TransactionVersionRecord":
        return cls(
            transaction_version_id=UUID(str(row.transaction_version_id)),
            account_id=str(row.account_id),
            category_id=str(row.category_id),
            transaction_date=row.transaction_date,
            amount_minor=int(row.amount_minor),
            status=str(row.status),
        )


@dataclass(frozen=True)
class TransactionListRecord:
    transaction_version_id: UUID
    concept_id: UUID
    transaction_date: date
    account_id: str
    account_name: str
    category_id: str
    category_name: str
    amount_minor: int
    status: str
    memo: str | None
    recorded_at: datetime

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "TransactionListRecord":
        return cls(
            transaction_version_id=UUID(str(row.transaction_version_id)),
            concept_id=UUID(str(row.concept_id)),
            transaction_date=row.transaction_date,
            account_id=str(row.account_id),
            account_name=str(row.account_name),
            category_id=str(row.category_id),
            category_name=str(row.category_name),
            amount_minor=int(row.amount_minor),
            status=str(row.status),
            memo=str(row.memo) if getattr(row, "memo", None) is not None else None,
            recorded_at=row.recorded_at,
        )


@dataclass(frozen=True)
class BudgetAllocationRecord:
    allocation_id: UUID
    allocation_date: date
    amount_minor: int
    memo: str | None
    from_category_id: str | None
    from_category_name: str | None
    to_category_id: str
    to_category_name: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "BudgetAllocationRecord":
        return cls(
            allocation_id=UUID(str(row.allocation_id)),
            allocation_date=row.allocation_date,
            amount_minor=int(row.amount_minor),
            memo=str(row.memo) if getattr(row, "memo", None) is not None else None,
            from_category_id=str(row.from_category_id) if getattr(row, "from_category_id", None) is not None else None,
            from_category_name=str(row.from_category_name) if getattr(row, "from_category_name", None) is not None else None,
            to_category_id=str(row.to_category_id),
            to_category_name=str(row.to_category_name),
            created_at=row.created_at,
        )


class BudgetingDAO:
    """Encapsulates DuckDB reads and writes for budgeting services."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _fetchone_namespace(self, sql: str, params: Sequence[Any] | None = None) -> SimpleNamespace | None:
        cursor = self._conn.execute(sql, params or [])
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_namespace(cursor.description, row)

    def _fetchall_namespaces(self, sql: str, params: Sequence[Any] | None = None) -> list[SimpleNamespace]:
        cursor = self._conn.execute(sql, params or [])
        rows = cursor.fetchall()
        if not rows:
            return []
        return [_row_to_namespace(cursor.description, row) for row in rows]

    # Transaction control -------------------------------------------------
    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        self._conn.execute("COMMIT")

    def rollback(self) -> None:
        self._conn.execute("ROLLBACK")

    @contextmanager
    def transaction(self) -> Generator["BudgetingDAO", None, None]:
        self.begin()
        try:
            yield self
        except Exception:
            self.rollback()
            raise
        else:
            self.commit()

    # Account queries -----------------------------------------------------
    def get_active_account(self, account_id: str) -> AccountRecord | None:
        row = self._fetchone_namespace(_sql("select_active_account.sql"), [account_id])
        if row is None:
            return None
        return AccountRecord.from_row(row)

    def get_account_detail(self, account_id: str) -> AccountRecord | None:
        row = self._fetchone_namespace(_sql("select_account_detail.sql"), [account_id])
        if row is None:
            return None
        return AccountRecord.from_row(row)

    def list_accounts(self) -> list[AccountRecord]:
        sql = _sql("select_accounts_admin.sql")
        rows = self._fetchall_namespaces(sql)
        return [AccountRecord.from_row(row) for row in rows]

    def list_reference_accounts(self) -> list[ReferenceAccountRecord]:
        sql = _sql("select_reference_accounts.sql")
        rows = self._fetchall_namespaces(sql)
        return [ReferenceAccountRecord.from_row(row) for row in rows]

    def insert_account(
        self,
        account_id: str,
        name: str,
        account_type: str,
        account_class: str,
        account_role: str,
        current_balance_minor: int,
        currency: str,
        is_active: bool,
        opened_on: date | None,
    ) -> None:
        sql = _sql("insert_account.sql")
        self._conn.execute(
            sql,
            [
                account_id,
                name,
                account_type,
                account_class,
                account_role,
                current_balance_minor,
                currency,
                is_active,
                opened_on,
            ],
        )

    def insert_account_detail(self, account_class: AccountClass, account_id: str) -> str:
        try:
            sql_name = ACCOUNT_DETAIL_INSERTS[account_class]
        except KeyError as exc:
            raise ValueError(f"Unsupported account_class `{account_class}` for detail insert.") from exc
        detail_id = str(uuid4())
        sql = _sql(sql_name)
        self._conn.execute(sql, [detail_id, account_id, account_id])
        return detail_id

    def update_account(
        self,
        account_id: str,
        name: str,
        account_type: str,
        account_class: str,
        account_role: str,
        current_balance_minor: int,
        currency: str,
        opened_on: date | None,
        is_active: bool,
    ) -> None:
        sql = _sql("update_account.sql")
        self._conn.execute(
            sql,
            [
                name,
                account_type,
                account_class,
                account_role,
                current_balance_minor,
                currency,
                opened_on,
                is_active,
                account_id,
            ],
        )

    def deactivate_account(self, account_id: str) -> None:
        self._conn.execute(_sql("deactivate_account.sql"), [account_id])

    # Category queries ----------------------------------------------------
    def get_active_category(self, category_id: str) -> CategoryRecord | None:
        row = self._fetchone_namespace(_sql("select_active_category.sql"), [category_id])
        if row is None:
            return None
        return CategoryRecord.from_row(row)

    def get_category_optional(self, category_id: str) -> CategoryRecord | None:
        row = self._fetchone_namespace(_sql("select_active_category.sql"), [category_id])
        if row is None:
            return None
        if not bool(getattr(row, "is_active", True)):
            return None
        return CategoryRecord.from_row(row)

    def get_category_month_state(self, category_id: str, month_start: date) -> CategoryMonthStateRecord | None:
        sql = _sql("select_category_month_state.sql")
        row = self._fetchone_namespace(sql, [month_start, category_id])
        if row is None:
            return None
        return CategoryMonthStateRecord.from_row(row)

    def get_budget_category_detail(self, category_id: str, month_start: date) -> BudgetCategoryDetailRecord | None:
        sql = _sql("select_budget_category_detail.sql")
        row = self._fetchone_namespace(sql, [month_start, category_id])
        if row is None:
            return None
        return BudgetCategoryDetailRecord.from_row(row)

    def list_budget_categories(self, month: date, previous_month: date) -> list[BudgetCategoryDetailRecord]:
        sql = _sql("select_budget_categories_admin.sql")
        params = [month, previous_month]
        rows = self._fetchall_namespaces(sql, params)
        return [BudgetCategoryDetailRecord.from_row(row) for row in rows]

    def list_reference_categories(self) -> list[ReferenceCategoryRecord]:
        sql = _sql("select_reference_categories.sql")
        rows = self._fetchall_namespaces(sql)
        return [ReferenceCategoryRecord.from_row(row) for row in rows]

    def insert_budget_category(
        self,
        category_id: str,
        group_id: str | None,
        name: str,
        is_active: bool,
        goal_type: str | None,
        goal_amount_minor: int | None,
        goal_target_date: date | None,
        goal_frequency: str | None,
    ) -> None:
        sql = _sql("insert_budget_category.sql")
        self._conn.execute(
            sql,
            [
                category_id,
                group_id,
                name,
                is_active,
                goal_type,
                goal_amount_minor,
                goal_target_date,
                goal_frequency,
            ],
        )

    def update_budget_category(
        self,
        category_id: str,
        name: str,
        group_id: str | None,
        is_active: bool,
        goal_type: str | None,
        goal_amount_minor: int | None,
        goal_target_date: date | None,
        goal_frequency: str | None,
    ) -> None:
        sql = _sql("update_budget_category.sql")
        self._conn.execute(
            sql,
            [
                name,
                group_id,
                is_active,
                goal_type,
                goal_amount_minor,
                goal_target_date,
                goal_frequency,
                category_id,
            ],
        )

    def deactivate_budget_category(self, category_id: str) -> None:
        self._conn.execute(_sql("deactivate_budget_category.sql"), [category_id])

    # Category groups -----------------------------------------------------
    def list_budget_category_groups(self) -> list[BudgetCategoryGroupRecord]:
        sql = _sql("select_budget_category_groups.sql")
        rows = self._fetchall_namespaces(sql)
        return [BudgetCategoryGroupRecord.from_row(row) for row in rows]

    def insert_budget_category_group(
        self,
        group_id: str,
        name: str,
        sort_order: int,
    ) -> BudgetCategoryGroupRecord | None:
        sql = _sql("insert_budget_category_group.sql")
        row = self._fetchone_namespace(sql, [group_id, name, sort_order])
        if row is None:
            return None
        return BudgetCategoryGroupRecord.from_row(row)

    def update_budget_category_group(
        self,
        group_id: str,
        name: str,
        sort_order: int,
    ) -> BudgetCategoryGroupRecord | None:
        sql = _sql("update_budget_category_group.sql")
        row = self._fetchone_namespace(sql, [name, sort_order, group_id])
        if row is None:
            return None
        return BudgetCategoryGroupRecord.from_row(row)

    def deactivate_budget_category_group(self, group_id: str) -> None:
        self._conn.execute(_sql("deactivate_budget_category_group.sql"), [group_id])

    def get_budget_category_group(self, group_id: str) -> BudgetCategoryGroupRecord | None:
        sql = _sql("select_budget_category_group.sql")
        row = self._fetchone_namespace(sql, [group_id])
        if row is None:
            return None
        return BudgetCategoryGroupRecord.from_row(row)

    # Transactions --------------------------------------------------------
    def get_active_transaction(self, concept_id: UUID | str) -> TransactionVersionRecord | None:
        sql = _sql("select_active_transaction.sql")
        row = self._fetchone_namespace(sql, [str(concept_id)])
        if row is None:
            return None
        return TransactionVersionRecord.from_row(row)

    def close_active_transaction(self, concept_id: UUID | str, recorded_at: datetime) -> None:
        sql = _sql("close_active_transaction.sql")
        self._conn.execute(sql, [recorded_at, recorded_at, str(concept_id)])

    def insert_transaction(
        self,
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
        sql = _sql("insert_transaction.sql")
        self._conn.execute(
            sql,
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
                source,
            ],
        )

    def update_account_balance(self, account_id: str, amount_minor: int) -> None:
        sql = _sql("update_account_balance.sql")
        self._conn.execute(sql, [amount_minor, account_id])

    def upsert_category_activity(self, category_id: str, month_start: date, activity_delta: int) -> None:
        sql = _sql("upsert_category_monthly_state.sql")
        self._conn.execute(sql, [category_id, month_start, activity_delta, activity_delta])

    def adjust_category_allocation(
        self,
        category_id: str,
        month_start: date,
        allocated_delta: int,
        available_delta: int,
    ) -> None:
        sql = _sql("adjust_category_allocation.sql")
        self._conn.execute(sql, [category_id, month_start, allocated_delta, available_delta])

    def adjust_category_inflow(
        self,
        category_id: str,
        month_start: date,
        inflow_delta: int,
        available_delta: int,
    ) -> None:
        sql = _sql("adjust_category_inflow.sql")
        self._conn.execute(sql, [category_id, month_start, inflow_delta, available_delta])

    def insert_budget_allocation(
        self,
        allocation_id: UUID,
        allocation_date: date,
        month_start: date,
        from_category_id: str | None,
        to_category_id: str,
        amount_minor: int,
        memo: str | None,
    ) -> None:
        sql = _sql("insert_budget_allocation.sql")
        self._conn.execute(
            sql,
            [
                str(allocation_id),
                allocation_date,
                month_start,
                from_category_id,
                to_category_id,
                amount_minor,
                memo,
            ],
        )

    def list_recent_transactions(self, limit: int) -> list[TransactionListRecord]:
        sql = _sql("select_recent_transactions.sql")
        rows = self._fetchall_namespaces(sql, [limit])
        return [TransactionListRecord.from_row(row) for row in rows]

    def list_budget_allocations(self, month_start: date, limit: int) -> list[BudgetAllocationRecord]:
        sql = _sql("select_budget_allocations.sql")
        rows = self._fetchall_namespaces(sql, [month_start, limit])
        return [BudgetAllocationRecord.from_row(row) for row in rows]

    def ready_to_assign(self, month_start: date) -> int:
        sql = _sql("select_ready_to_assign.sql")
        try:
            row = self._fetchone_namespace(sql, [month_start])
        except duckdb.CatalogException:
            return 0
        if row is None:
            return 0
        return int(getattr(row, "ready_to_assign_minor", 0))

    def month_cash_inflow(self, month_start: date) -> int:
        sql = _sql("sum_month_cash_inflows.sql")
        try:
            row = self._fetchone_namespace(sql, [month_start, month_start])
        except duckdb.CatalogException:
            return 0
        if row is None:
            return 0
        return int(getattr(row, "inflow_minor", 0))

    # Credit payment helpers ---------------------------------------------
    def upsert_credit_payment_group(
        self,
        group_id: str,
        name: str,
        sort_order: int,
    ) -> None:
        sql = _sql("upsert_credit_payment_group.sql")
        self._conn.execute(sql, [group_id, name, sort_order])

    def upsert_credit_payment_category(
        self,
        category_id: str,
        group_id: str,
        name: str,
    ) -> None:
        sql = _sql("upsert_credit_payment_category.sql")
        self._conn.execute(sql, [category_id, group_id, name])