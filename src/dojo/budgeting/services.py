"""Budgeting domain services."""

import re
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional, cast
from uuid import uuid4

import duckdb

from dojo.budgeting.dao import (
    AccountRecord,
    BudgetAllocationRecord,
    BudgetCategoryDetailRecord,
    BudgetCategoryGroupRecord,
    BudgetingDAO,
    CategoryMonthStateRecord,
    CategoryRecord,
    TransactionListRecord,
    TransactionVersionRecord,
)
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
    AccountClass,
    AccountCreateRequest,
    AccountDetail,
    AccountRole,
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


def derive_payment_category_id(account_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", account_id.lower())
    trimmed = normalized.strip("_")
    return f"payment_{trimmed or 'account'}"


def derive_payment_category_name(account_name: str) -> str:
    label = account_name.strip() if account_name else "Credit Card"
    return label


CREDIT_PAYMENT_GROUP_ID = "credit_card_payments"
CREDIT_PAYMENT_GROUP_NAME = "Credit Card Payments"
CREDIT_PAYMENT_GROUP_SORT_ORDER = -1000


class TransactionEntryService:
    """Insert and manage ledger transactions."""

    MAX_FUTURE_DAYS = 5
    SOURCE = "api"
    TRANSFER_CATEGORY_ID = "account_transfer"

    def create(self, conn: duckdb.DuckDBPyConnection, cmd: NewTransactionRequest) -> TransactionResponse:
        """Insert a transaction using the temporal ledger model."""

        self._validate_payload(cmd)
        dao = BudgetingDAO(conn)
        concept_id = cmd.concept_id or uuid4()
        transaction_version_id = uuid4()
        recorded_at = datetime.now(timezone.utc)
        month_start = cmd.transaction_date.replace(day=1)
        activity_delta = -cmd.amount_minor

        dao.begin()
        try:
            account_record = self._require_active_account(dao, cmd.account_id)
            category_record = self._require_active_category(dao, cmd.category_id)
            track_budget_activity = self._should_track_budget_activity(category_record)

            if cmd.concept_id is not None:
                previous_transaction = dao.get_active_transaction(cmd.concept_id)
                if previous_transaction is not None:
                    self._reverse_transaction_effects(dao, previous_transaction)
                dao.close_active_transaction(concept_id, recorded_at)

            dao.insert_transaction(
                transaction_version_id=transaction_version_id,
                concept_id=concept_id,
                account_id=cmd.account_id,
                category_id=cmd.category_id,
                transaction_date=cmd.transaction_date,
                amount_minor=cmd.amount_minor,
                memo=cmd.memo,
                status=cmd.status,
                recorded_at=recorded_at,
                source=self.SOURCE,
            )
            dao.update_account_balance(cmd.account_id, cmd.amount_minor)

            if track_budget_activity:
                dao.upsert_category_activity(cmd.category_id, month_start, activity_delta)

            if self._should_reserve_credit_payment(account_record, category_record, cmd.amount_minor):
                self._record_credit_payment_reserve(dao, account_record, month_start, cmd.amount_minor)

            account_state = self._account_state_from_record(self._require_active_account(dao, cmd.account_id))
            category_state = self._category_state_from_month(
                dao.get_category_month_state(cmd.category_id, month_start),
                cmd.category_id,
            )

            dao.commit()
        except Exception:
            dao.rollback()
            raise

        return TransactionResponse(
            transaction_version_id=transaction_version_id,
            concept_id=concept_id,
            amount_minor=cmd.amount_minor,
            transaction_date=cmd.transaction_date,
            status=cast(Literal["pending", "cleared"], cmd.status),
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

        dao = BudgetingDAO(conn)
        concept_id = cmd.concept_id or uuid4()
        recorded_at = datetime.now(timezone.utc)
        month_start = cmd.transaction_date.replace(day=1)
        source_amount = -cmd.amount_minor
        destination_amount = cmd.amount_minor

        dao.begin()
        try:
            self._require_active_account(dao, cmd.source_account_id)
            self._require_active_account(dao, cmd.destination_account_id)
            category_record = self._require_active_category(dao, cmd.category_id)
            track_budget_activity = self._should_track_budget_activity(category_record)

            budget_leg_id = uuid4()
            transfer_leg_id = uuid4()

            dao.insert_transaction(
                transaction_version_id=budget_leg_id,
                concept_id=concept_id,
                account_id=cmd.source_account_id,
                category_id=cmd.category_id,
                transaction_date=cmd.transaction_date,
                amount_minor=source_amount,
                memo=cmd.memo,
                status="cleared",
                recorded_at=recorded_at,
                source=self.SOURCE,
            )
            dao.update_account_balance(cmd.source_account_id, source_amount)

            dao.insert_transaction(
                transaction_version_id=transfer_leg_id,
                concept_id=concept_id,
                account_id=cmd.destination_account_id,
                category_id=self.TRANSFER_CATEGORY_ID,
                transaction_date=cmd.transaction_date,
                amount_minor=destination_amount,
                memo=cmd.memo,
                status="cleared",
                recorded_at=recorded_at,
                source=self.SOURCE,
            )
            dao.update_account_balance(cmd.destination_account_id, destination_amount)

            if track_budget_activity:
                activity_delta = -source_amount
                dao.upsert_category_activity(cmd.category_id, month_start, activity_delta)

            source_state = self._account_state_from_record(self._require_active_account(dao, cmd.source_account_id))
            destination_state = self._account_state_from_record(
                self._require_active_account(dao, cmd.destination_account_id)
            )
            category_state = self._category_state_from_month(
                dao.get_category_month_state(cmd.category_id, month_start),
                cmd.category_id,
            )

            dao.commit()
        except Exception:
            dao.rollback()
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
        dao = BudgetingDAO(conn)
        return dao.ready_to_assign(month_start)

    def month_cash_inflow(self, conn: duckdb.DuckDBPyConnection, month_start: date) -> int:
        dao = BudgetingDAO(conn)
        return dao.month_cash_inflow(month_start)

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

        dao = BudgetingDAO(conn)
        allocation_day = allocation_date or date.today()
        month = (month_start or allocation_day).replace(day=1)
        memo_value = memo.strip() if memo else None

        destination_category = self._require_active_category(dao, destination_category_id)
        if destination_category.is_system:
            raise InvalidTransaction("System categories cannot receive allocations.")

        source_state: CategoryState | None = None
        if from_category_id:
            source_category = self._require_active_category(dao, from_category_id)
            if source_category.is_system:
                raise InvalidTransaction("System categories cannot provide allocations.")
            source_state = self._category_state_from_month(
                dao.get_category_month_state(from_category_id, month),
                from_category_id,
            )
            if source_state.available_minor < amount_minor:
                raise InvalidTransaction("Source category does not have enough available funds.")
        else:
            ready_minor = self.ready_to_assign(conn, month)
            if ready_minor < amount_minor:
                raise InvalidTransaction("Ready-to-Assign is insufficient for this allocation.")

        allocation_id = uuid4()
        dao.begin()
        try:
            dao.insert_budget_allocation(
                allocation_id=allocation_id,
                allocation_date=allocation_day,
                month_start=month,
                from_category_id=from_category_id,
                to_category_id=destination_category_id,
                amount_minor=amount_minor,
                memo=memo_value,
            )
            dao.adjust_category_allocation(destination_category_id, month, amount_minor, amount_minor)
            if from_category_id:
                dao.adjust_category_allocation(from_category_id, month, -amount_minor, -amount_minor)
            category_state = self._category_state_from_month(
                dao.get_category_month_state(destination_category_id, month),
                destination_category_id,
            )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        return category_state

    def list_recent(
        self,
        conn: duckdb.DuckDBPyConnection,
        limit: int,
    ) -> list[TransactionListItem]:
        dao = BudgetingDAO(conn)
        records = dao.list_recent_transactions(limit)
        return [self._record_to_transaction_item(record) for record in records]

    def list_allocations(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        dao = BudgetingDAO(conn)
        records = dao.list_budget_allocations(month_start, limit)
        return [self._record_to_allocation(row) for row in records]

    def _record_to_transaction_item(self, record: TransactionListRecord) -> TransactionListItem:
        return TransactionListItem(
            transaction_version_id=record.transaction_version_id,
            concept_id=record.concept_id,
            transaction_date=record.transaction_date,
            account_id=record.account_id,
            account_name=record.account_name,
            category_id=record.category_id,
            category_name=record.category_name,
            amount_minor=record.amount_minor,
            status=cast(Literal["pending", "cleared"], record.status),
            memo=record.memo,
            recorded_at=record.recorded_at,
        )

    def _record_to_allocation(self, record: BudgetAllocationRecord) -> dict[str, Any]:
        return {
            "allocation_id": record.allocation_id,
            "allocation_date": record.allocation_date,
            "amount_minor": record.amount_minor,
            "memo": record.memo,
            "from_category_id": record.from_category_id,
            "from_category_name": record.from_category_name,
            "to_category_id": record.to_category_id,
            "to_category_name": record.to_category_name,
            "created_at": record.created_at,
        }

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

    def _require_active_account(self, dao: BudgetingDAO, account_id: str) -> AccountRecord:
        record = dao.get_active_account(account_id)
        if record is None or not record.is_active:
            raise UnknownAccount(f"Account `{account_id}` is not active.")
        return record

    def _require_active_category(self, dao: BudgetingDAO, category_id: str) -> CategoryRecord:
        record = dao.get_active_category(category_id)
        if record is None or not record.is_active:
            raise UnknownCategory(f"Category `{category_id}` is not active.")
        return record

    def _account_state_from_record(self, record: AccountRecord) -> AccountState:
        account_type = _coerce_account_type(record.account_type)
        account_class = _coerce_account_class(record.account_class)
        account_role = _coerce_account_role(record.account_role)
        return AccountState(
            account_id=record.account_id,
            name=record.name,
            account_type=account_type,
            account_class=account_class,
            account_role=account_role,
            current_balance_minor=record.current_balance_minor,
        )

    def _category_state_from_month(
        self,
        record: CategoryMonthStateRecord | None,
        category_id: str,
    ) -> CategoryState:
        if record is None:
            return CategoryState(
                category_id=category_id,
                name="Unknown",
                available_minor=0,
                activity_minor=0,
            )
        return CategoryState(
            category_id=record.category_id,
            name=record.name,
            available_minor=record.available_minor,
            activity_minor=record.activity_minor,
        )

    def _reverse_transaction_effects(
        self,
        dao: BudgetingDAO,
        transaction: TransactionVersionRecord,
    ) -> None:
        month_start = transaction.transaction_date.replace(day=1)
        dao.update_account_balance(transaction.account_id, -transaction.amount_minor)
        category_record = dao.get_category_optional(transaction.category_id)
        if category_record and not category_record.is_system:
            dao.upsert_category_activity(transaction.category_id, month_start, transaction.amount_minor)
        if category_record:
            account_record = self._require_active_account(dao, transaction.account_id)
            if self._should_reserve_credit_payment(account_record, category_record, transaction.amount_minor):
                self._record_credit_payment_reserve(
                    dao,
                    account_record,
                    month_start,
                    -transaction.amount_minor,
                )

    @staticmethod
    def _should_track_budget_activity(category_record: CategoryRecord) -> bool:
        return not category_record.is_system

    def _should_reserve_credit_payment(
        self,
        account_record: AccountRecord,
        category_record: CategoryRecord,
        amount_minor: int,
    ) -> bool:
        if amount_minor == 0:
            return False
        if not account_record.is_credit_liability:
            return False
        if category_record.is_system:
            return False
        return True

    def _record_credit_payment_reserve(
        self,
        dao: BudgetingDAO,
        account_record: AccountRecord,
        month_start: date,
        amount_minor: int,
    ) -> None:
        payment_category_id = derive_payment_category_id(account_record.account_id)
        payment_category = dao.get_category_optional(payment_category_id)
        if payment_category is None:
            return
        delta = abs(amount_minor)
        if delta == 0:
            return
        sign = 1 if amount_minor < 0 else -1
        dao.adjust_category_inflow(payment_category.category_id, month_start, sign * delta, sign * delta)


def _coerce_account_type(value: str) -> Literal["asset", "liability"]:
    if value not in {"asset", "liability"}:
        raise BudgetingError(f"Invalid account_type `{value}` encountered.")
    return cast(Literal["asset", "liability"], value)


def _coerce_account_class(value: str) -> AccountClass:
    if value not in {"cash", "credit", "investment", "accessible", "loan", "tangible"}:
        raise BudgetingError(f"Invalid account_class `{value}` encountered.")
    return cast(AccountClass, value)


def _coerce_account_role(value: str) -> AccountRole:
    if value not in {"on_budget", "tracking"}:
        raise BudgetingError(f"Invalid account_role `{value}` encountered.")
    return cast(AccountRole, value)


class AccountAdminService:
    """Manage CRUD flows for accounts exposed to the SPA."""

    def list_accounts(self, conn: duckdb.DuckDBPyConnection) -> list[AccountDetail]:
        dao = BudgetingDAO(conn)
        records = dao.list_accounts()
        return [self._record_to_account(record) for record in records]

    def create_account(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: AccountCreateRequest,
    ) -> AccountDetail:
        dao = BudgetingDAO(conn)
        if dao.get_account_detail(payload.account_id) is not None:
            raise AccountAlreadyExists(f"Account `{payload.account_id}` already exists.")

        currency = payload.currency.upper()
        dao.begin()
        try:
            dao.insert_account(
                account_id=payload.account_id,
                name=payload.name,
                account_type=payload.account_type,
                account_class=payload.account_class,
                account_role=payload.account_role,
                current_balance_minor=payload.current_balance_minor,
                currency=currency,
                is_active=payload.is_active,
                opened_on=payload.opened_on,
            )
            if self._should_create_payment_category(payload.account_type, payload.account_class):
                self._ensure_credit_payment_category(
                    dao,
                    account_id=payload.account_id,
                    account_name=payload.name,
                )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        return self._require_account(dao, payload.account_id)

    def update_account(
        self,
        conn: duckdb.DuckDBPyConnection,
        account_id: str,
        payload: AccountUpdateRequest,
    ) -> AccountDetail:
        dao = BudgetingDAO(conn)
        self._require_account(dao, account_id)
        currency = payload.currency.upper()
        dao.begin()
        try:
            dao.update_account(
                account_id=account_id,
                name=payload.name,
                account_type=payload.account_type,
                account_class=payload.account_class,
                account_role=payload.account_role,
                current_balance_minor=payload.current_balance_minor,
                currency=currency,
                opened_on=payload.opened_on,
                is_active=payload.is_active,
            )
            if self._should_create_payment_category(payload.account_type, payload.account_class):
                self._ensure_credit_payment_category(
                    dao,
                    account_id=account_id,
                    account_name=payload.name,
                )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        return self._require_account(dao, account_id)

    def deactivate_account(self, conn: duckdb.DuckDBPyConnection, account_id: str) -> None:
        dao = BudgetingDAO(conn)
        self._require_account(dao, account_id)
        dao.begin()
        try:
            dao.deactivate_account(account_id)
            dao.commit()
        except Exception:
            dao.rollback()
            raise

    def _require_account(self, dao: BudgetingDAO, account_id: str) -> AccountDetail:
        record = dao.get_account_detail(account_id)
        if record is None:
            raise AccountNotFound(f"Account `{account_id}` was not found.")
        return self._record_to_account(record)

    def _record_to_account(self, record: AccountRecord) -> AccountDetail:
        if record.created_at is None or record.updated_at is None:
            raise BudgetingError("Account record missing timestamps.")
        account_type = _coerce_account_type(record.account_type)
        account_class = _coerce_account_class(record.account_class)
        account_role = _coerce_account_role(record.account_role)
        return AccountDetail(
            account_id=record.account_id,
            name=record.name,
            account_type=account_type,
            account_class=account_class,
            account_role=account_role,
            current_balance_minor=record.current_balance_minor,
            currency=record.currency,
            is_active=record.is_active,
            opened_on=record.opened_on,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _should_create_payment_category(account_type: str, account_class: str) -> bool:
        return account_type == "liability" and account_class == "credit"

    def _ensure_credit_payment_category(
        self,
        dao: BudgetingDAO,
        account_id: str,
        account_name: str,
    ) -> None:
        dao.upsert_credit_payment_group(
            group_id=CREDIT_PAYMENT_GROUP_ID,
            name=CREDIT_PAYMENT_GROUP_NAME,
            sort_order=CREDIT_PAYMENT_GROUP_SORT_ORDER,
        )
        dao.upsert_credit_payment_category(
            category_id=derive_payment_category_id(account_id),
            group_id=CREDIT_PAYMENT_GROUP_ID,
            name=derive_payment_category_name(account_name),
        )


class BudgetCategoryAdminService:
    """CRUD surface for budget categories."""

    def list_categories(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date | None = None,
    ) -> list[BudgetCategoryDetail]:
        dao = BudgetingDAO(conn)
        month = self._coerce_month_start(month_start)
        if month.month == 1:
            prev_month = date(month.year - 1, 12, 1)
        else:
            prev_month = date(month.year, month.month - 1, 1)
        records = dao.list_budget_categories(month, prev_month)
        return [self._record_to_category(record) for record in records]

    def create_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryCreateRequest,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        dao = BudgetingDAO(conn)
        category_id = payload.category_id
        if not category_id:
            normalized = payload.name.lower()
            normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
            category_id = normalized.strip("_") or f"category_{int(datetime.now().timestamp())}"
        category_id = str(category_id)

        if dao.get_budget_category_detail(category_id, self._coerce_month_start(month_start)) is not None:
            raise CategoryAlreadyExists(f"Category `{category_id}` already exists.")

        dao.begin()
        try:
            dao.insert_budget_category(
                category_id=category_id,
                group_id=payload.group_id,
                name=payload.name,
                is_active=payload.is_active,
                goal_type=payload.goal_type,
                goal_amount_minor=payload.goal_amount_minor,
                goal_target_date=payload.goal_target_date,
                goal_frequency=payload.goal_frequency,
            )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        return self._require_category(dao, category_id, month_start)

    def update_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        payload: BudgetCategoryUpdateRequest,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        dao = BudgetingDAO(conn)
        self._require_category(dao, category_id, month_start)
        dao.begin()
        try:
            dao.update_budget_category(
                category_id=category_id,
                name=payload.name,
                group_id=payload.group_id,
                is_active=payload.is_active,
                goal_type=payload.goal_type,
                goal_amount_minor=payload.goal_amount_minor,
                goal_target_date=payload.goal_target_date,
                goal_frequency=payload.goal_frequency,
            )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        return self._require_category(dao, category_id, month_start)

    def deactivate_category(self, conn: duckdb.DuckDBPyConnection, category_id: str) -> None:
        dao = BudgetingDAO(conn)
        self._require_category(dao, category_id)
        dao.begin()
        try:
            dao.deactivate_budget_category(category_id)
            dao.commit()
        except Exception:
            dao.rollback()
            raise

    def list_groups(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[BudgetCategoryGroupDetail]:
        dao = BudgetingDAO(conn)
        records = dao.list_budget_category_groups()
        return [self._record_to_group(record) for record in records]

    def create_group(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryGroupCreateRequest,
    ) -> BudgetCategoryGroupDetail:
        dao = BudgetingDAO(conn)
        dao.begin()
        try:
            record = dao.insert_budget_category_group(
                group_id=payload.group_id,
                name=payload.name,
                sort_order=payload.sort_order,
            )
            if record is None:
                raise BudgetingError("Failed to create group")
            dao.commit()
            return self._record_to_group(record)
        except duckdb.ConstraintException as exc:
            dao.rollback()
            raise GroupAlreadyExists(
                f"Group `{payload.group_id}` already exists."
            ) from exc
        except Exception:
            dao.rollback()
            raise

    def update_group(
        self,
        conn: duckdb.DuckDBPyConnection,
        group_id: str,
        payload: BudgetCategoryGroupUpdateRequest,
    ) -> BudgetCategoryGroupDetail:
        dao = BudgetingDAO(conn)
        dao.begin()
        try:
            record = dao.update_budget_category_group(
                group_id=group_id,
                name=payload.name,
                sort_order=payload.sort_order,
            )
            if record is None:
                raise GroupNotFound(f"Group `{group_id}` not found.")
            dao.commit()
            return self._record_to_group(record)
        except Exception:
            dao.rollback()
            raise

    def deactivate_group(
        self, conn: duckdb.DuckDBPyConnection, group_id: str
    ) -> None:
        dao = BudgetingDAO(conn)
        dao.begin()
        try:
            dao.deactivate_budget_category_group(group_id)
            dao.commit()
        except Exception:
            dao.rollback()
            raise

    def _record_to_group(self, record: BudgetCategoryGroupRecord) -> BudgetCategoryGroupDetail:
        return BudgetCategoryGroupDetail(
            group_id=record.group_id,
            name=record.name,
            sort_order=record.sort_order,
            is_active=record.is_active,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _require_category(
        self,
        dao: BudgetingDAO,
        category_id: str,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        record = dao.get_budget_category_detail(category_id, self._coerce_month_start(month_start))
        if record is None:
            raise CategoryNotFound(f"Category `{category_id}` was not found.")
        return self._record_to_category(record)

    def _record_to_category(self, record: BudgetCategoryDetailRecord) -> BudgetCategoryDetail:
        goal_type = cast(Optional[Literal["target_date", "recurring"]], record.goal_type)
        goal_frequency = cast(Optional[Literal["monthly", "quarterly", "yearly"]], record.goal_frequency)
        return BudgetCategoryDetail(
            category_id=record.category_id,
            group_id=record.group_id,
            name=record.name,
            is_active=record.is_active,
            created_at=record.created_at,
            updated_at=record.updated_at,
            goal_type=goal_type,
            goal_amount_minor=record.goal_amount_minor,
            goal_target_date=record.goal_target_date,
            goal_frequency=goal_frequency,
            available_minor=record.available_minor,
            activity_minor=record.activity_minor,
            allocated_minor=record.allocated_minor,
            last_month_allocated_minor=record.last_month_allocated_minor,
            last_month_activity_minor=record.last_month_activity_minor,
            last_month_available_minor=record.last_month_available_minor,
        )

    @staticmethod
    def _coerce_month_start(month_start: date | None) -> date:
        if month_start is None:
            today = date.today()
            return today.replace(day=1)
        return month_start.replace(day=1)
