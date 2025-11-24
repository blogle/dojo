"""Budgeting domain services."""

import re
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional, cast
from uuid import UUID, uuid4

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
    """
    Derives a consistent category ID for credit card payment categories based on an account ID.

    Parameters
    ----------
    account_id : str
        The ID of the credit card account.

    Returns
    -------
    str
        A slug-like category ID for the payment category.
    """
    # Normalize the account ID to create a valid slug.
    normalized = re.sub(r"[^a-z0-9]+", "_", account_id.lower())
    trimmed = normalized.strip("_")
    # Prepend "payment_" to clearly identify it as a payment category.
    return f"payment_{trimmed or 'account'}"


def derive_payment_category_name(account_name: str) -> str:
    """
    Derives a user-friendly name for a credit card payment category.

    Parameters
    ----------
    account_name : str
        The name of the credit card account.

    Returns
    -------
    str
        A descriptive name for the payment category.
    """
    label = account_name.strip() if account_name else "Credit Card"
    return label


# Constant for the ID of the credit card payment category group.
CREDIT_PAYMENT_GROUP_ID = "credit_card_payments"
# Constant for the display name of the credit card payment category group.
CREDIT_PAYMENT_GROUP_NAME = "Credit Card Payments"
# Constant for the sort order of the credit card payment category group, ensuring it appears prominently.
CREDIT_PAYMENT_GROUP_SORT_ORDER = -1000


class TransactionEntryService:
    """
    Handles the creation, management, and processing of ledger transactions.

    This service implements the business logic for recording new transactions,
    performing categorized transfers, and managing budget envelope allocations.
    It interacts with the `BudgetingDAO` to persist and retrieve data.
    """

    # Maximum number of days in the future a transaction date can be.
    MAX_FUTURE_DAYS = 5
    # Source identifier for transactions created via the API.
    SOURCE = "api"
    # Special category ID used for the transfer leg of categorized transfers.
    TRANSFER_CATEGORY_ID = "account_transfer"

    def create(
        self, conn: duckdb.DuckDBPyConnection, cmd: NewTransactionRequest
    ) -> TransactionResponse:
        """
        Inserts a new transaction using the temporal ledger model.

        This method validates the incoming transaction request, applies the transaction
        to the ledger, updates account balances, and adjusts category activities.
        It handles both new transactions and updates to existing conceptual transactions.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        cmd : NewTransactionRequest
            The incoming request payload for the new transaction.

        Returns
        -------
        TransactionResponse
            The response object containing details of the created/updated transaction
            and the resulting account/category states.

        Raises
        ------
        InvalidTransaction
            If the transaction payload is invalid (e.g., zero amount, future date too far).
        UnknownAccount
            If the referenced account does not exist or is inactive.
        UnknownCategory
            If the referenced category does not exist or is inactive.
        """
        # Validate the incoming transaction payload.
        self._validate_payload(cmd)
        dao = BudgetingDAO(conn)
        # Generate a new concept_id if not provided, for grouping related transactions.
        concept_id = cmd.concept_id or uuid4()
        # Generate a unique ID for this specific version of the transaction.
        transaction_version_id = uuid4()
        # Record the current UTC time as the transaction's recorded_at timestamp.
        recorded_at = datetime.now(timezone.utc)
        # Determine the start of the month for budgeting purposes.
        month_start = cmd.transaction_date.replace(day=1)
        # Calculate the activity delta for the category. Outflows are positive activity.
        activity_delta = -cmd.amount_minor

        # Start a database transaction to ensure atomicity of all changes.
        with dao.transaction():
            # Retrieve and validate the account and category, ensuring they are active.
            account_record = self._require_active_account(dao, cmd.account_id)
            category_record = self._require_active_category(dao, cmd.category_id)
            # Determine if this transaction should affect budget category activity.
            track_budget_activity = self._should_track_budget_activity(category_record)
            # Calculate the impact on the account balance.
            balance_delta = self._account_balance_delta(
                cmd.amount_minor, account_record
            )

            # If a concept_id is provided, it indicates an update or a reversal of a previous transaction.
            if cmd.concept_id is not None:
                # Check for an existing active version of this conceptual transaction.
                previous_transaction = dao.get_active_transaction(cmd.concept_id)
                if previous_transaction is not None:
                    # Reverse the effects of the previous transaction to ensure a clean update.
                    self._reverse_transaction_effects(dao, previous_transaction)
                # Close the previous active version of the conceptual transaction.
                dao.close_active_transaction(concept_id, recorded_at)

            # Insert the new version of the transaction into the ledger.
            dao.insert_transaction(
                transaction_version_id=transaction_version_id,
                concept_id=concept_id,
                account_id=cmd.account_id,
                category_id=cmd.category_id,
                transaction_date=cmd.transaction_date,
                amount_minor=cmd.amount_minor,
                memo=cmd.memo,
                status=cast(Literal["pending", "cleared"], cmd.status),
                recorded_at=recorded_at,
                source=self.SOURCE,
            )
            # Update the account's current balance.
            dao.update_account_balance(cmd.account_id, balance_delta)

            # If the category tracks budget activity, update its monthly activity.
            if track_budget_activity:
                dao.upsert_category_activity(
                    cmd.category_id, month_start, activity_delta
                )

            # Check if this transaction involves a credit account and needs a payment reserve adjustment.
            if self._should_reserve_credit_payment(
                account_record, category_record, cmd.amount_minor
            ):
                self._record_credit_payment_reserve(
                    dao, account_record, month_start, cmd.amount_minor
                )

            # Retrieve the updated state of the account and category for the response.
            account_state = self._account_state_from_record(
                self._require_active_account(dao, cmd.account_id)
            )
            category_state = self._category_state_from_month(
                dao.get_category_month_state(cmd.category_id, month_start),
                cmd.category_id,
            )

            # Return the transaction response.
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
        """
        Performs a categorized transfer with two ledger entries (legs).

        A categorized transfer typically involves an outflow from a source account
        to a budgeting category (budget leg) and an inflow to a destination account
        from a transfer category (transfer leg).

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        cmd : CategorizedTransferRequest
            The incoming request payload for the categorized transfer.

        Returns
        -------
        CategorizedTransferResponse
            The response object containing details of the transfer, including
            the created transaction legs and updated category state.

        Raises
        ------
        InvalidTransaction
            If the transfer payload is invalid (e.g., source and destination accounts are the same,
            future date too far).
        UnknownAccount
            If either the source or destination account does not exist or is inactive.
        UnknownCategory
            If the referenced category does not exist or is inactive.
        """
        # Validate the incoming transfer payload.
        self._validate_transfer_payload(cmd)
        # Ensure source and destination accounts are different.
        if cmd.source_account_id == cmd.destination_account_id:
            raise InvalidTransaction("Source and destination accounts must differ.")

        dao = BudgetingDAO(conn)
        # Generate a new concept_id if not provided.
        concept_id = cmd.concept_id or uuid4()
        # Record the current UTC time.
        recorded_at = datetime.now(timezone.utc)
        # Determine the start of the month for budgeting purposes.
        month_start = cmd.transaction_date.replace(day=1)
        # Generate unique IDs for each leg of the transfer.
        budget_leg_id = uuid4()
        transfer_leg_id = uuid4()

        # Start a database transaction to ensure atomicity.
        with dao.transaction():
            # Retrieve and validate accounts and category.
            source_account = self._require_active_account(dao, cmd.source_account_id)
            destination_account = self._require_active_account(
                dao, cmd.destination_account_id
            )
            category_record = self._require_active_category(dao, cmd.category_id)
            # Determine if the budget category tracks activity.
            track_budget_activity = self._should_track_budget_activity(category_record)

            # Calculate the amount deltas for each account based on their type and direction.
            source_amount = self._transfer_delta(
                cmd.amount_minor, source_account, "outgoing"
            )
            destination_amount = self._transfer_delta(
                cmd.amount_minor, destination_account, "incoming"
            )

            # Record the budget leg of the transfer.
            self._record_transfer_leg(
                dao,
                budget_leg_id,
                concept_id,
                cmd.source_account_id,
                cmd.category_id,
                cmd.transaction_date,
                source_amount,
                cmd.memo,
                "cleared",
                recorded_at,
            )
            # Record the transfer leg of the transfer.
            self._record_transfer_leg(
                dao,
                transfer_leg_id,
                concept_id,
                cmd.destination_account_id,
                self.TRANSFER_CATEGORY_ID,  # Use a special category for transfers between accounts.
                cmd.transaction_date,
                destination_amount,
                cmd.memo,
                "cleared",
                recorded_at,
            )

            # If the budget category tracks activity, record the activity.
            if track_budget_activity:
                self._record_category_activity(
                    dao, cmd.category_id, month_start, cmd.amount_minor
                )

            # Retrieve updated states of accounts and category for the response.
            source_state = self._account_state_for(dao, cmd.source_account_id)
            destination_state = self._account_state_for(dao, cmd.destination_account_id)
            category_state = self._category_state_for_month(
                dao, cmd.category_id, month_start
            )

        # Return the categorized transfer response.
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

    def ready_to_assign(
        self, conn: duckdb.DuckDBPyConnection, month_start: date
    ) -> int:
        """
        Retrieves the "Ready to Assign" amount for a given month.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        month_start : date
            The start date of the month for which to retrieve RTA.

        Returns
        -------
        int
            The "Ready to Assign" amount in minor units.
        """
        dao = BudgetingDAO(conn)
        return dao.ready_to_assign(month_start)

    def month_cash_inflow(
        self, conn: duckdb.DuckDBPyConnection, month_start: date
    ) -> int:
        """
        Retrieves the total cash inflow for a given month.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        month_start : date
            The start date of the month for which to retrieve cash inflow.

        Returns
        -------
        int
            The total cash inflow amount in minor units.
        """
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
        """
        Allocates funds to a budgeting category (envelope).

        This method supports allocating funds from "Ready to Assign" or
        reallocating from one category to another.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        category_id : str
            The ID of the category to which funds will be allocated (destination).
        amount_minor : int
            The amount of funds to allocate in minor units.
        month_start : date | None, optional
            The start date of the month for which the allocation is made.
            Defaults to the allocation date's month start if not provided.
        from_category_id : str | None, optional
            The ID of the category from which funds are reallocated.
            If None, funds are assumed to come from "Ready to Assign".
        memo : str | None, optional
            An optional memo for the allocation.
        allocation_date : date | None, optional
            The date of the allocation. Defaults to today if not provided.

        Returns
        -------
        CategoryState
            The updated state of the destination category after allocation.

        Raises
        ------
        InvalidTransaction
            If the allocation amount is non-positive, destination category is invalid,
            source category is invalid, or insufficient funds are available.
        UnknownCategory
            If a referenced category (source or destination) is not found or inactive.
        """
        # Validate that the allocation amount is positive.
        self._validate_allocation_amount(amount_minor)
        # Determine and validate the destination category, ensuring it's not the same as source if specified.
        destination_category_id = self._require_allocation_destination(
            category_id, from_category_id
        )
        # Determine the allocation date, defaulting to today.
        allocation_day = allocation_date or date.today()
        # Coerce month_start to the first day of the month, defaulting to allocation_day's month if not provided.
        month = self._coerce_month_start(month_start or allocation_day)
        # Clean up memo if provided.
        memo_value = memo.strip() if memo else None

        dao = BudgetingDAO(conn)
        # Retrieve and validate the destination category.
        destination_category = self._require_active_category(
            dao, destination_category_id
        )
        # Assert that the destination category can receive allocations (e.g., not a system category).
        self._assert_destination_category_can_receive_allocations(destination_category)

        # Handle reallocation from a source category.
        if from_category_id:
            self._ensure_allocation_source_can_allocate(
                dao, from_category_id, month, amount_minor
            )
        else:
            # Handle allocation from "Ready to Assign".
            self._ensure_ready_to_assign(dao, month, amount_minor)

        # Generate a unique ID for this allocation.
        allocation_id = uuid4()
        # Start a database transaction for atomicity.
        with dao.transaction():
            # Persist the allocation record.
            self._persist_allocation(
                dao,
                allocation_id,
                allocation_day,
                month,
                from_category_id,
                destination_category_id,
                amount_minor,
                memo_value,
            )
            # Retrieve the updated state of the destination category for the response.
            category_state = self._category_state_for_month(
                dao, destination_category_id, month
            )
        return category_state

    def list_recent(
        self,
        conn: duckdb.DuckDBPyConnection,
        limit: int,
    ) -> list[TransactionListItem]:
        """
        Lists a specified number of the most recent transactions.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        limit : int
            The maximum number of recent transactions to retrieve.

        Returns
        -------
        list[TransactionListItem]
            A list of `TransactionListItem` objects representing recent transactions.
        """
        dao = BudgetingDAO(conn)
        # Retrieve recent transaction records from the DAO.
        records = dao.list_recent_transactions(limit)
        # Convert DAO records to Pydantic TransactionListItem models.
        return [self._record_to_transaction_item(record) for record in records]

    def list_allocations(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Lists budget allocations for a specific month.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        month_start : date
            The start date of the month for which to list allocations.
        limit : int
            The maximum number of allocations to retrieve.

        Returns
        -------
        list[dict[str, Any]]
            A list of dictionaries, each representing a budget allocation entry.
        """
        dao = BudgetingDAO(conn)
        # Retrieve budget allocation records from the DAO.
        records = dao.list_budget_allocations(month_start, limit)
        # Convert DAO records to a list of dictionaries.
        return [self._record_to_allocation(row) for row in records]

    def _record_to_transaction_item(
        self, record: TransactionListRecord
    ) -> TransactionListItem:
        """
        Converts a `TransactionListRecord` DAO object to a `TransactionListItem` schema.

        Parameters
        ----------
        record : TransactionListRecord
            The DAO record representing a transaction list item.

        Returns
        -------
        TransactionListItem
            A Pydantic model for transaction list display.
        """
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
        """
        Converts a `BudgetAllocationRecord` DAO object to a dictionary.

        This method is used to prepare allocation data for conversion into a Pydantic model.

        Parameters
        ----------
        record : BudgetAllocationRecord
            The DAO record representing a budget allocation.

        Returns
        -------
        dict[str, Any]
            A dictionary containing the allocation details.
        """
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

    def _record_transfer_leg(
        self,
        dao: BudgetingDAO,
        transaction_version_id: UUID,
        concept_id: UUID,
        account_id: str,
        category_id: str,
        transaction_date: date,
        amount_minor: int,
        memo: str | None,
        status: Literal["pending", "cleared"],
        recorded_at: datetime,
    ) -> None:
        """
        Records a single leg of a transfer transaction.

        This involves inserting the transaction and updating the account balance.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        transaction_version_id : UUID
            Unique ID for this specific transaction version.
        concept_id : UUID
            The conceptual ID linking related transaction versions.
        account_id : str
            The ID of the account involved.
        category_id : str
            The ID of the category associated.
        transaction_date : date
            The date of the transaction.
        amount_minor : int
            The amount in minor units.
        memo : str | None
            Optional memo.
        status : Literal["pending", "cleared"]
            The status of the transaction.
        recorded_at : datetime
            Timestamp when recorded.
        """
        dao.insert_transaction(
            transaction_version_id=transaction_version_id,
            concept_id=concept_id,
            account_id=account_id,
            category_id=category_id,
            transaction_date=transaction_date,
            amount_minor=amount_minor,
            memo=memo,
            status=status,
            recorded_at=recorded_at,
            source=self.SOURCE,
        )
        dao.update_account_balance(account_id, amount_minor)

    def _record_category_activity(
        self,
        dao: BudgetingDAO,
        category_id: str,
        month_start: date,
        activity_delta: int,
    ) -> None:
        """
        Records activity for a budgeting category in a given month.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the month.
        activity_delta : int
            The change in activity amount (in minor units).
        """
        dao.upsert_category_activity(category_id, month_start, activity_delta)

    def _account_state_for(self, dao: BudgetingDAO, account_id: str) -> AccountState:
        """
        Retrieves the `AccountState` for a given account ID.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        account_id : str
            The ID of the account.

        Returns
        -------
        AccountState
            The current state of the account.
        """
        return self._account_state_from_record(
            self._require_active_account(dao, account_id)
        )

    def _category_state_for_month(
        self, dao: BudgetingDAO, category_id: str, month_start: date
    ) -> CategoryState:
        """
        Retrieves the `CategoryState` for a given category and month.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the month.

        Returns
        -------
        CategoryState
            The state of the category for the specified month.
        """
        record = dao.get_category_month_state(category_id, month_start)
        return self._category_state_from_month(record, category_id)

    def _validate_allocation_amount(self, amount_minor: int) -> None:
        """
        Validates that an allocation amount is positive.

        Parameters
        ----------
        amount_minor : int
            The amount to validate in minor units.

        Raises
        ------
        InvalidTransaction
            If the amount is not positive.
        """
        if amount_minor <= 0:
            raise InvalidTransaction("amount_minor must be positive for allocations.")

    def _require_allocation_destination(
        self,
        destination_category_id: str,
        from_category_id: str | None,
    ) -> str:
        """
        Validates and returns the destination category ID for an allocation.

        Ensures that a destination ID is provided and that it's not the same
        as the source category ID if a source is specified.

        Parameters
        ----------
        destination_category_id : str
            The proposed destination category ID.
        from_category_id : str | None
            The optional source category ID.

        Returns
        -------
        str
            The validated destination category ID.

        Raises
        ------
        InvalidTransaction
            If `to_category_id` is missing or if source and destination are the same.
        """
        if not destination_category_id:
            raise InvalidTransaction("to_category_id is required for allocations.")
        if from_category_id and from_category_id == destination_category_id:
            raise InvalidTransaction("Source and destination categories must differ.")
        return destination_category_id

    def _assert_destination_category_can_receive_allocations(
        self, category_record: CategoryRecord
    ) -> None:
        """
        Asserts that the destination category is not a system category.

        System categories are generally reserved and cannot receive direct allocations.

        Parameters
        ----------
        category_record : CategoryRecord
            The category record of the destination category.

        Raises
        ------
        InvalidTransaction
            If the destination category is a system category.
        """
        if category_record.is_system:
            raise InvalidTransaction("System categories cannot receive allocations.")

    def _ensure_allocation_source_can_allocate(
        self,
        dao: BudgetingDAO,
        from_category_id: str,
        month_start: date,
        amount_minor: int,
    ) -> None:
        """
        Ensures the source category has sufficient funds for reallocation.

        Validates that the source category is active, not a system category,
        and has enough available funds.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        from_category_id : str
            The ID of the source category.
        month_start : date
            The start date of the month for the allocation.
        amount_minor : int
            The amount to be reallocated in minor units.

        Raises
        ------
        UnknownCategory
            If the source category is not found or inactive.
        InvalidTransaction
            If the source category is a system category or has insufficient funds.
        """
        source_category = self._require_active_category(dao, from_category_id)
        if source_category.is_system:
            raise InvalidTransaction("System categories cannot provide allocations.")
        source_state = self._category_state_from_month(
            dao.get_category_month_state(from_category_id, month_start),
            from_category_id,
        )
        if source_state.available_minor < amount_minor:
            raise InvalidTransaction(
                "Source category does not have enough available funds."
            )

    def _ensure_ready_to_assign(
        self, dao: BudgetingDAO, month_start: date, amount_minor: int
    ) -> None:
        """
        Ensures there is sufficient "Ready to Assign" funds for an allocation.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        month_start : date
            The start date of the month.
        amount_minor : int
            The amount to be allocated from "Ready to Assign" in minor units.

        Raises
        ------
        InvalidTransaction
            If "Ready to Assign" funds are insufficient.
        """
        ready_minor = dao.ready_to_assign(month_start)
        if ready_minor < amount_minor:
            raise InvalidTransaction(
                "Ready-to-Assign is insufficient for this allocation."
            )

    def _persist_allocation(
        self,
        dao: BudgetingDAO,
        allocation_id: UUID,
        allocation_date: date,
        month_start: date,
        from_category_id: str | None,
        destination_category_id: str,
        amount_minor: int,
        memo: str | None,
    ) -> None:
        """
        Persists a budget allocation in the database and adjusts category balances.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        allocation_id : UUID
            Unique ID for the allocation.
        allocation_date : date
            The date of the allocation.
        month_start : date
            The start date of the month the allocation applies to.
        from_category_id : str | None
            Source category ID (if reallocation).
        destination_category_id : str
            Destination category ID.
        amount_minor : int
            Amount allocated in minor units.
        memo : str | None
            Optional memo.
        """
        # Insert the allocation record.
        dao.insert_budget_allocation(
            allocation_id=allocation_id,
            allocation_date=allocation_date,
            month_start=month_start,
            from_category_id=from_category_id,
            to_category_id=destination_category_id,
            amount_minor=amount_minor,
            memo=memo,
        )
        # Adjust the allocated and available amounts for the destination category.
        dao.adjust_category_allocation(
            destination_category_id, month_start, amount_minor, amount_minor
        )
        # If there's a source category, adjust its allocated and available amounts negatively.
        if from_category_id:
            dao.adjust_category_allocation(
                from_category_id, month_start, -amount_minor, -amount_minor
            )

    @staticmethod
    def _coerce_month_start(month_start: date | None) -> date:
        """
        Coerces a given date to the first day of its month, or the current month's first day.

        Parameters
        ----------
        month_start : date | None
            The date to coerce, or None to use today's date.

        Returns
        -------
        date
            A date object representing the first day of the relevant month.
        """
        reference = month_start or date.today()
        return reference.replace(day=1)

    def _validate_payload(self, cmd: NewTransactionRequest) -> None:
        """
        Validates the payload for a new transaction request.

        Ensures the transaction amount is non-zero and the transaction date
        is not too far in the future.

        Parameters
        ----------
        cmd : NewTransactionRequest
            The incoming transaction request payload.

        Raises
        ------
        InvalidTransaction
            If the amount is zero or the transaction date is too far in the future.
        """
        if cmd.amount_minor == 0:
            raise InvalidTransaction("amount_minor must be non-zero.")
        # Calculate the difference in days between the transaction date and today.
        future_delta = (cmd.transaction_date - date.today()).days
        if future_delta > self.MAX_FUTURE_DAYS:
            raise InvalidTransaction(
                f"transaction_date may not be more than {self.MAX_FUTURE_DAYS} days in the future."
            )

    def _validate_transfer_payload(self, cmd: CategorizedTransferRequest) -> None:
        """
        Validates the payload for a categorized transfer request.

        Ensures the transfer date is not too far in the future.

        Parameters
        ----------
        cmd : CategorizedTransferRequest
            The incoming categorized transfer request payload.

        Raises
        ------
        InvalidTransaction
            If the transaction date is too far in the future.
        """
        # Calculate the difference in days between the transaction date and today.
        future_delta = (cmd.transaction_date - date.today()).days
        if future_delta > self.MAX_FUTURE_DAYS:
            raise InvalidTransaction(
                f"transaction_date may not be more than {self.MAX_FUTURE_DAYS} days in the future."
            )

    def _transfer_delta(
        self,
        amount_minor: int,
        account: AccountRecord,
        direction: Literal["incoming", "outgoing"],
    ) -> int:
        """
        Calculates the actual change in account balance for a transfer leg.

        Considers account type (asset/liability) and transfer direction to
        determine the correct signed amount for database updates.

        Parameters
        ----------
        amount_minor : int
            The absolute amount of the transfer in minor units.
        account : AccountRecord
            The account record involved in the transfer.
        direction : Literal["incoming", "outgoing"]
            The direction of the transfer relative to the account.

        Returns
        -------
        int
            The signed amount representing the change in the account's balance.
        """
        # Determine the base sign based on incoming/outgoing.
        sign = 1 if direction == "incoming" else -1
        # Invert the sign for liability accounts, as increases in liabilities are negative balance changes.
        if account.account_type == "liability":
            sign *= -1
        return amount_minor * sign

    def _account_balance_delta(self, amount_minor: int, account: AccountRecord) -> int:
        """
        Calculates the change in account balance based on transaction amount and account type.

        For asset accounts, a positive amount increases balance; for liability accounts,
        a positive amount decreases balance.

        Parameters
        ----------
        amount_minor : int
            The amount of the transaction in minor units.
        account : AccountRecord
            The account record being impacted.

        Returns
        -------
        int
            The signed amount to be applied to the account's balance.
        """
        # For liability accounts, the amount is inverted because an increase in a liability
        # is a decrease in net worth (and conceptually a negative balance adjustment).
        if account.account_type == "liability":
            return -amount_minor
        return amount_minor

    def _require_active_account(
        self, dao: BudgetingDAO, account_id: str
    ) -> AccountRecord:
        """
        Retrieves an active account record or raises an error if not found/active.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        account_id : str
            The ID of the account to retrieve.

        Returns
        -------
        AccountRecord
            The active account record.

        Raises
        ------
        UnknownAccount
            If the account does not exist or is not active.
        """
        record = dao.get_active_account(account_id)
        if record is None or not record.is_active:
            raise UnknownAccount(f"Account `{account_id}` is not active.")
        return record

    def _require_active_category(
        self, dao: BudgetingDAO, category_id: str
    ) -> CategoryRecord:
        """
        Retrieves an active category record or raises an error if not found/active.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        category_id : str
            The ID of the category to retrieve.

        Returns
        -------
        CategoryRecord
            The active category record.

        Raises
        ------
        UnknownCategory
            If the category does not exist or is not active.
        """
        record = dao.get_active_category(category_id)
        if record is None or not record.is_active:
            raise UnknownCategory(f"Category `{category_id}` is not active.")
        return record

    def _account_state_from_record(self, record: AccountRecord) -> AccountState:
        """
        Converts an `AccountRecord` DAO object to an `AccountState` schema.

        Parameters
        ----------
        record : AccountRecord
            The DAO record representing an account.

        Returns
        -------
        AccountState
            A Pydantic model representing the account's state.
        """
        # Coerce string values from the record to their specific Literal types for the schema.
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
        """
        Converts a `CategoryMonthStateRecord` DAO object to a `CategoryState` schema.

        If no monthly state record is found, it returns a default `CategoryState`
        with zero available and activity, and an "Unknown" name.

        Parameters
        ----------
        record : CategoryMonthStateRecord | None
            The DAO record representing a category's monthly state, or None if not found.
        category_id : str
            The ID of the category.

        Returns
        -------
        CategoryState
            A Pydantic model representing the category's state for the month.
        """
        if record is None:
            return CategoryState(
                category_id=category_id,
                name="Unknown",  # Default name if category monthly state not found.
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
        """
        Reverses the financial effects of a given transaction version.

        This is used when an existing transaction is updated or replaced,
        to undo its impact on account balances and category activities
        before applying the new version.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        transaction : TransactionVersionRecord
            The transaction version whose effects are to be reversed.
        """
        month_start = transaction.transaction_date.replace(day=1)
        account_record = self._require_active_account(dao, transaction.account_id)
        # Calculate the balance delta for the original transaction.
        balance_delta = self._account_balance_delta(
            transaction.amount_minor, account_record
        )
        # Apply the negative of the original delta to reverse the account balance change.
        dao.update_account_balance(transaction.account_id, -balance_delta)
        # Get the category record for the transaction.
        category_record = dao.get_category_optional(transaction.category_id)
        # If the category exists and is not a system category, reverse its activity.
        if category_record and not category_record.is_system:
            dao.upsert_category_activity(
                transaction.category_id, month_start, transaction.amount_minor
            )
        # If it was a credit payment reservation, reverse that as well.
        if category_record:
            account_record = self._require_active_account(dao, transaction.account_id)
            if self._should_reserve_credit_payment(
                account_record, category_record, transaction.amount_minor
            ):
                self._record_credit_payment_reserve(
                    dao,
                    account_record,
                    month_start,
                    # Reverse the amount for the credit payment reserve.
                    -transaction.amount_minor,
                )

    @staticmethod
    def _should_track_budget_activity(category_record: CategoryRecord) -> bool:
        """
        Determines if a category's activity should be tracked in the budget.

        Parameters
        ----------
        category_record : CategoryRecord
            The category record to evaluate.

        Returns
        -------
        bool
            True if the category is not a system category (i.e., user-managed), False otherwise.
        """
        return not category_record.is_system

    def _should_reserve_credit_payment(
        self,
        account_record: AccountRecord,
        category_record: CategoryRecord,
        amount_minor: int,
    ) -> bool:
        """
        Determines if a transaction should trigger a credit payment reserve adjustment.

        This logic applies to transactions involving credit liability accounts
        and non-system categories, where the transaction amount is non-zero.

        Parameters
        ----------
        account_record : AccountRecord
            The account involved in the transaction.
        category_record : CategoryRecord
            The category involved in the transaction.
        amount_minor : int
            The amount of the transaction in minor units.

        Returns
        -------
        bool
            True if a credit payment reserve should be recorded, False otherwise.
        """
        if amount_minor == 0:
            return False
        # Only applies to credit liability accounts.
        if not account_record.is_credit_liability:
            return False
        # System categories do not trigger payment reserves.
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
        """
        Adjusts the credit payment reserve category for a given account.

        This method ensures that funds are correctly moved into or out of
        the dedicated payment category for a credit card.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        account_record : AccountRecord
            The credit card account record.
        month_start : date
            The start date of the month for which the adjustment is made.
        amount_minor : int
            The amount of the transaction in minor units.
            A negative amount indicates an increase in spending (more to reserve),
            a positive amount indicates a decrease in spending (less to reserve).
        """
        # Derive the payment category ID for the credit card account.
        payment_category_id = derive_payment_category_id(account_record.account_id)
        # Attempt to retrieve the payment category.
        payment_category = dao.get_category_optional(payment_category_id)
        if payment_category is None:
            # If no payment category exists for the credit card, do nothing.
            return
        # The delta for the reserve is the absolute value of the transaction amount.
        delta = abs(amount_minor)
        if delta == 0:
            return
        # The sign of the adjustment depends on whether spending increased or decreased.
        # Negative transaction amount (spending) means more to reserve (positive delta).
        # Positive transaction amount (return) means less to reserve (negative delta).
        sign = 1 if amount_minor < 0 else -1
        # Adjust the inflow and available amounts of the payment category.
        dao.adjust_category_inflow(
            payment_category.category_id, month_start, sign * delta, sign * delta
        )


def _coerce_account_type(value: str) -> Literal["asset", "liability"]:
    """
    Coerces a string value to an `AccountType` literal.

    Parameters
    ----------
    value : str
        The string value to coerce.

    Returns
    -------
    Literal["asset", "liability"]
        The coerced account type.

    Raises
    ------
    BudgetingError
        If the value is not a valid account type.
    """
    # Validate the value against the allowed literal types.
    if value not in {"asset", "liability"}:
        raise BudgetingError(f"Invalid account_type `{value}` encountered.")
    # Cast to the Literal type for static analysis.
    return cast(Literal["asset", "liability"], value)


def _coerce_account_class(value: str) -> AccountClass:
    """
    Coerces a string value to an `AccountClass` literal.

    Parameters
    ----------
    value : str
        The string value to coerce.

    Returns
    -------
    AccountClass
        The coerced account class.

    Raises
    ------
    BudgetingError
        If the value is not a valid account class.
    """
    # Validate the value against the allowed literal types.
    if value not in {"cash", "credit", "investment", "accessible", "loan", "tangible"}:
        raise BudgetingError(f"Invalid account_class `{value}` encountered.")
    # Cast to the AccountClass Literal type for static analysis.
    return cast(AccountClass, value)


def _coerce_account_role(value: str) -> AccountRole:
    """
    Coerces a string value to an `AccountRole` literal.

    Parameters
    ----------
    value : str
        The string value to coerce.

    Returns
    -------
    AccountRole
        The coerced account role.

    Raises
    ------
    BudgetingError
        If the value is not a valid account role.
    """
    # Validate the value against the allowed literal types.
    if value not in {"on_budget", "tracking"}:
        raise BudgetingError(f"Invalid account_role `{value}` encountered.")
    # Cast to the AccountRole Literal type for static analysis.
    return cast(AccountRole, value)


class AccountAdminService:
    """
    Manages administrative operations related to financial accounts.

    This service provides CRUD (Create, Read, Update, Delete/Deactivate)
    functionalities for accounts, exposed to the administrative user interface.
    It interacts with the `BudgetingDAO` to persist and retrieve account data.
    """

    def list_accounts(self, conn: duckdb.DuckDBPyConnection) -> list[AccountDetail]:
        """
        Retrieves a list of all accounts for administration purposes.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.

        Returns
        -------
        list[AccountDetail]
            A list of `AccountDetail` objects, providing full details for each account.
        """
        dao = BudgetingDAO(conn)
        records = dao.list_accounts()
        # Convert DAO records to Pydantic AccountDetail models for the API response.
        return [self._record_to_account(record) for record in records]

    def create_account(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: AccountCreateRequest,
    ) -> AccountDetail:
        """
        Creates a new financial account.

        This method validates the incoming account creation request,
        inserts the new account into the database, and creates any
        associated detail records (e.g., for credit accounts).

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        payload : AccountCreateRequest
            The data for creating the new account.

        Returns
        -------
        AccountDetail
            The detailed record of the newly created account.

        Raises
        ------
        AccountAlreadyExists
            If an account with the provided `account_id` already exists.
        BudgetingError
            For other budgeting-related errors during account creation.
        """
        dao = BudgetingDAO(conn)
        # Check if an account with the given ID already exists to prevent duplicates.
        if dao.get_account_detail(payload.account_id) is not None:
            raise AccountAlreadyExists(
                f"Account `{payload.account_id}` already exists."
            )

        # Ensure currency code is uppercase for consistency.
        currency = payload.currency.upper()
        dao.begin()
        try:
            # Insert the main account record.
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
            # Insert specific detail records based on the account class.
            dao.insert_account_detail(payload.account_class, payload.account_id)
            # If it's a credit account, ensure a corresponding payment category exists.
            if self._should_create_payment_category(
                payload.account_type, payload.account_class
            ):
                self._ensure_credit_payment_category(
                    dao,
                    account_id=payload.account_id,
                    account_name=payload.name,
                )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        # Retrieve and return the full details of the newly created account.
        return self._require_account(dao, payload.account_id)

    def update_account(
        self,
        conn: duckdb.DuckDBPyConnection,
        account_id: str,
        payload: AccountUpdateRequest,
    ) -> AccountDetail:
        """
        Updates an existing financial account's details.

        This method modifies the attributes of an existing account in the database.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        account_id : str
            The ID of the account to update.
        payload : AccountUpdateRequest
            The updated data for the account.

        Returns
        -------
        AccountDetail
            The detailed record of the updated account.

        Raises
        ------
        AccountNotFound
            If the account with the provided `account_id` does not exist.
        BudgetingError
            For other budgeting-related errors during account update.
        """
        dao = BudgetingDAO(conn)
        # Ensure the account exists before attempting to update.
        self._require_account(dao, account_id)
        # Ensure currency code is uppercase for consistency.
        currency = payload.currency.upper()
        dao.begin()
        try:
            # Update the main account record.
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
            # Update specific account detail records, if necessary.
            dao.insert_account_detail(payload.account_class, account_id)
            # If it's a credit account, ensure a corresponding payment category exists (or is updated).
            if self._should_create_payment_category(
                payload.account_type, payload.account_class
            ):
                self._ensure_credit_payment_category(
                    dao,
                    account_id=account_id,
                    account_name=payload.name,
                )
            dao.commit()
        except Exception:
            dao.rollback()
            raise
        # Retrieve and return the full details of the updated account.
        return self._require_account(dao, account_id)

    def deactivate_account(
        self, conn: duckdb.DuckDBPyConnection, account_id: str
    ) -> None:
        """
        Deactivates an existing financial account.

        Deactivation marks an account as inactive, preventing further transactions,
        but retains its historical data.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        account_id : str
            The ID of the account to deactivate.

        Raises
        ------
        AccountNotFound
            If the account with the provided `account_id` does not exist.
        BudgetingError
            For other budgeting-related errors during account deactivation.
        """
        dao = BudgetingDAO(conn)
        # Ensure the account exists and is active before attempting to deactivate.
        self._require_account(dao, account_id)
        dao.begin()
        try:
            # Deactivate the account.
            dao.deactivate_account(account_id)
            dao.commit()
        except Exception:
            dao.rollback()
            raise

    def _require_account(self, dao: BudgetingDAO, account_id: str) -> AccountDetail:
        """
        Retrieves a detailed account record or raises an error if not found.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        account_id : str
            The ID of the account to retrieve.

        Returns
        -------
        AccountDetail
            The detailed account record.

        Raises
        ------
        AccountNotFound
            If the account does not exist.
        """
        record = dao.get_account_detail(account_id)
        if record is None:
            raise AccountNotFound(f"Account `{account_id}` was not found.")
        # Convert the DAO record to an AccountDetail schema.
        return self._record_to_account(record)

    def _record_to_account(self, record: AccountRecord) -> AccountDetail:
        """
        Converts an `AccountRecord` DAO object to an `AccountDetail` schema.

        Parameters
        ----------
        record : AccountRecord
            The DAO record representing an account.

        Returns
        -------
        AccountDetail
            A Pydantic model for displaying full account details.

        Raises
        ------
        BudgetingError
            If the account record is missing required timestamps.
        """
        # Ensure that timestamps are present, which are expected for a detailed view.
        if record.created_at is None or record.updated_at is None:
            raise BudgetingError("Account record missing timestamps.")
        # Coerce string values from the record to their specific Literal types for the schema.
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
        """
        Determines if a credit payment category should be created for an account.

        Credit payment categories are automatically generated for liability accounts
        of the "credit" class.

        Parameters
        ----------
        account_type : str
            The type of the account (e.g., "asset", "liability").
        account_class : str
            The class of the account (e.g., "cash", "credit").

        Returns
        -------
        bool
            True if a credit payment category should be created, False otherwise.
        """
        return account_type == "liability" and account_class == "credit"

    def _ensure_credit_payment_category(
        self,
        dao: BudgetingDAO,
        account_id: str,
        account_name: str,
    ) -> None:
        """
        Ensures that a credit payment category and its group exist for a credit account.

        This method creates or updates the necessary budget structures to manage
        credit card payments as a dedicated budgeting category.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        account_id : str
            The ID of the credit card account.
        account_name : str
            The name of the credit card account.
        """
        # Upsert the credit payment category group.
        dao.upsert_credit_payment_group(
            group_id=CREDIT_PAYMENT_GROUP_ID,
            name=CREDIT_PAYMENT_GROUP_NAME,
            sort_order=CREDIT_PAYMENT_GROUP_SORT_ORDER,
        )
        # Upsert the specific credit payment category for this account.
        dao.upsert_credit_payment_category(
            category_id=derive_payment_category_id(account_id),
            group_id=CREDIT_PAYMENT_GROUP_ID,
            name=derive_payment_category_name(account_name),
        )


class BudgetCategoryAdminService:
    """
    Manages administrative operations for budgeting categories and groups.

    This service provides CRUD (Create, Read, Update, Delete/Deactivate)
    functionalities for budget categories and their organizational groups.
    It interacts with the `BudgetingDAO` to persist and retrieve budgeting data.
    """

    def list_categories(
        self,
        conn: duckdb.DuckDBPyConnection,
        month_start: date | None = None,
    ) -> list[BudgetCategoryDetail]:
        """
        Retrieves a list of all budgeting categories, optionally for a specific month.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        month_start : date | None, optional
            The start date of the month (YYYY-MM-01) for which to retrieve category states.
            If None, the current month is used.

        Returns
        -------
        list[BudgetCategoryDetail]
            A list of `BudgetCategoryDetail` objects, providing comprehensive details
            for each budgeting category.
        """
        dao = BudgetingDAO(conn)
        # Coerce the month_start to the first day of the month.
        month = self._coerce_month_start(month_start)
        # Calculate the start of the previous month for historical data retrieval.
        if month.month == 1:
            prev_month = date(month.year - 1, 12, 1)
        else:
            prev_month = date(month.year, month.month - 1, 1)
        # Retrieve budget category records from the DAO.
        records = dao.list_budget_categories(month, prev_month)
        # Convert DAO records to Pydantic BudgetCategoryDetail models.
        return [self._record_to_category(record) for record in records]

    def create_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryCreateRequest,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        """
        Creates a new budgeting category.

        This method generates a `category_id` if not provided, validates
        uniqueness, and persists the new category in the database.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        payload : BudgetCategoryCreateRequest
            The data for creating the new budgeting category.
        month_start : date | None, optional
            The start date of the month (YYYY-MM-01) relevant for initial category state.

        Returns
        -------
        BudgetCategoryDetail
            The detailed record of the newly created budgeting category.

        Raises
        ------
        CategoryAlreadyExists
            If a category with the generated or provided `category_id` already exists.
        """
        dao = BudgetingDAO(conn)
        category_id = payload.category_id
        # Generate a category_id if one is not provided.
        if not category_id:
            normalized = payload.name.lower()
            normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
            category_id = (
                normalized.strip("_") or f"category_{int(datetime.now().timestamp())}"
            )
        category_id = str(category_id)

        # Check if a category with the determined ID already exists.
        if (
            dao.get_budget_category_detail(
                category_id, self._coerce_month_start(month_start)
            )
            is not None
        ):
            raise CategoryAlreadyExists(f"Category `{category_id}` already exists.")

        dao.begin()
        try:
            # Insert the new budget category record.
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
        # Retrieve and return the full details of the newly created category.
        return self._require_category(dao, category_id, month_start)

    def update_category(
        self,
        conn: duckdb.DuckDBPyConnection,
        category_id: str,
        payload: BudgetCategoryUpdateRequest,
        month_start: date | None = None,
    ) -> BudgetCategoryDetail:
        """
        Updates an existing budgeting category's details.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        category_id : str
            The ID of the category to update.
        payload : BudgetCategoryUpdateRequest
            The updated data for the budgeting category.
        month_start : date | None, optional
            The start date of the month (YYYY-MM-01) relevant for updating category state.

        Returns
        -------
        BudgetCategoryDetail
            The detailed record of the updated budgeting category.

        Raises
        ------
        CategoryNotFound
            If the category with the provided `category_id` does not exist.
        """
        dao = BudgetingDAO(conn)
        # Ensure the category exists before attempting to update.
        self._require_category(dao, category_id, month_start)
        dao.begin()
        try:
            # Update the budget category record.
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
        # Retrieve and return the full details of the updated category.
        return self._require_category(dao, category_id, month_start)

    def deactivate_category(
        self, conn: duckdb.DuckDBPyConnection, category_id: str
    ) -> None:
        """
        Deactivates a budgeting category.

        Deactivating a category marks it as inactive, preventing further use in budgeting,
        but retains its historical data.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        category_id : str
            The ID of the category to deactivate.

        Raises
        ------
        CategoryNotFound
            If the category with the provided `category_id` does not exist.
        """
        dao = BudgetingDAO(conn)
        # Ensure the category exists before attempting to deactivate.
        self._require_category(dao, category_id)
        dao.begin()
        try:
            # Deactivate the budget category.
            dao.deactivate_budget_category(category_id)
            dao.commit()
        except Exception:
            dao.rollback()
            raise

    def list_groups(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[BudgetCategoryGroupDetail]:
        """
        Retrieves a list of all budgeting category groups.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.

        Returns
        -------
        list[BudgetCategoryGroupDetail]
            A list of `BudgetCategoryGroupDetail` objects.
        """
        dao = BudgetingDAO(conn)
        records = dao.list_budget_category_groups()
        # Convert DAO records to Pydantic BudgetCategoryGroupDetail models.
        return [self._record_to_group(record) for record in records]

    def create_group(
        self,
        conn: duckdb.DuckDBPyConnection,
        payload: BudgetCategoryGroupCreateRequest,
    ) -> BudgetCategoryGroupDetail:
        """
        Creates a new budgeting category group.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        payload : BudgetCategoryGroupCreateRequest
            The data for creating the new category group.

        Returns
        -------
        BudgetCategoryGroupDetail
            The detailed record of the newly created category group.

        Raises
        ------
        GroupAlreadyExists
            If a category group with the provided `group_id` already exists.
        BudgetingError
            If the group creation fails for other reasons.
        """
        dao = BudgetingDAO(conn)
        dao.begin()
        try:
            # Insert the new budget category group record.
            record = dao.insert_budget_category_group(
                group_id=payload.group_id,
                name=payload.name,
                sort_order=payload.sort_order,
            )
            if record is None:
                raise BudgetingError("Failed to create group")
            dao.commit()
            # Convert the DAO record to a Pydantic model.
            return self._record_to_group(record)
        except duckdb.ConstraintException as exc:
            dao.rollback()
            # Handle unique constraint violation for group_id.
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
        """
        Updates an existing budgeting category group's details.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        group_id : str
            The ID of the category group to update.
        payload : BudgetCategoryGroupUpdateRequest
            The updated data for the category group.

        Returns
        -------
        BudgetCategoryGroupDetail
            The detailed record of the updated category group.

        Raises
        ------
        GroupNotFound
            If the category group with the provided `group_id` does not exist.
        """
        dao = BudgetingDAO(conn)
        dao.begin()
        try:
            # Update the budget category group record.
            record = dao.update_budget_category_group(
                group_id=group_id,
                name=payload.name,
                sort_order=payload.sort_order,
            )
            if record is None:
                raise GroupNotFound(f"Group `{group_id}` not found.")
            dao.commit()
            # Convert the DAO record to a Pydantic model.
            return self._record_to_group(record)
        except Exception:
            dao.rollback()
            raise

    def deactivate_group(self, conn: duckdb.DuckDBPyConnection, group_id: str) -> None:
        """
        Deactivates a budgeting category group.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object.
        group_id : str
            The ID of the category group to deactivate.

        Raises
        ------
        GroupNotFound
            If the category group with the provided `group_id` does not exist.
        """
        dao = BudgetingDAO(conn)
        dao.begin()
        try:
            # Deactivate the budget category group.
            dao.deactivate_budget_category_group(group_id)
            dao.commit()
        except Exception:
            dao.rollback()
            raise

    def _record_to_group(
        self, record: BudgetCategoryGroupRecord
    ) -> BudgetCategoryGroupDetail:
        """
        Converts a `BudgetCategoryGroupRecord` DAO object to a `BudgetCategoryGroupDetail` schema.

        Parameters
        ----------
        record : BudgetCategoryGroupRecord
            The DAO record representing a category group.

        Returns
        -------
        BudgetCategoryGroupDetail
            A Pydantic model for displaying full category group details.
        """
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
        """
        Retrieves a detailed category record or raises an error if not found.

        Parameters
        ----------
        dao : BudgetingDAO
            The Data Access Object for budgeting operations.
        category_id : str
            The ID of the category to retrieve.
        month_start : date | None, optional
            The start date of the month (YYYY-MM-01) to get category details for.

        Returns
        -------
        BudgetCategoryDetail
            The detailed budgeting category record.

        Raises
        ------
        CategoryNotFound
            If the category does not exist.
        """
        # Retrieve budget category details, coercing month_start if necessary.
        record = dao.get_budget_category_detail(
            category_id, self._coerce_month_start(month_start)
        )
        if record is None:
            raise CategoryNotFound(f"Category `{category_id}` was not found.")
        # Convert the DAO record to a BudgetCategoryDetail schema.
        return self._record_to_category(record)

    def _record_to_category(
        self, record: BudgetCategoryDetailRecord
    ) -> BudgetCategoryDetail:
        """
        Converts a `BudgetCategoryDetailRecord` DAO object to a `BudgetCategoryDetail` schema.

        Parameters
        ----------
        record : BudgetCategoryDetailRecord
            The DAO record representing a detailed budget category.

        Returns
        -------
        BudgetCategoryDetail
            A Pydantic model for displaying full budget category details.
        """
        # Cast goal types and frequencies to their specific Literal types for the schema.
        goal_type = cast(
            Optional[Literal["target_date", "recurring"]], record.goal_type
        )
        goal_frequency = cast(
            Optional[Literal["monthly", "quarterly", "yearly"]], record.goal_frequency
        )
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
        """
        Coerces a given date to the first day of its month, or the current month's first day.

        Parameters
        ----------
        month_start : date | None
            The date to coerce, or None to use today's date.

        Returns
        -------
        date
            A date object representing the first day of the relevant month.
        """
        if month_start is None:
            today = date.today()
            return today.replace(day=1)
        return month_start.replace(day=1)
