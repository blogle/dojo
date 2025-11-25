"""Data access helpers for the budgeting domain."""

from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache
from types import SimpleNamespace
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import duckdb

from dojo.budgeting.schemas import AccountClass, AccountRole
from dojo.budgeting.sql import load_sql


@cache
def _sql(name: str) -> str:
    # Caches the loaded SQL queries to avoid repeated disk I/O.
    return load_sql(name)


def _previous_month_start(month_start: date) -> date:
    """
    Calculates the start date of the month immediately preceding the given month_start.

    Parameters
    ----------
    month_start : date
        A date object representing the start of a month.

    Returns
    -------
    date
        A date object representing the start of the previous month.
    """
    # Set the day to 1 to ensure consistent month-start calculation.
    first_day = month_start.replace(day=1)
    # Subtract one day to get into the previous month, then set to the first day of that month.
    prev_last_day = first_day - timedelta(days=1)
    return prev_last_day.replace(day=1)


def _row_to_namespace(
    description: Sequence[tuple[Any, ...]], row: tuple[Any, ...]
) -> SimpleNamespace:
    """
    Converts a database row and its description into a SimpleNamespace object.

    This utility function maps column names from the cursor description to their
    corresponding values in the row, providing attribute-style access to row data.

    Parameters
    ----------
    description : Sequence[tuple[Any, ...]]
        The cursor description, containing column metadata.
    row : tuple[Any, ...]
        A single row of data fetched from the database.

    Returns
    -------
    SimpleNamespace
        An object with attributes corresponding to column names and their values.
    """
    # Extract column names from the cursor description.
    columns = [desc[0] for desc in description]
    # Create a SimpleNamespace object, mapping column names to row values.
    return SimpleNamespace(**{name: value for name, value in zip(columns, row)})


@dataclass(frozen=True)
class AccountRecord:
    """
    Represents a single financial account.

    Attributes
    ----------
    account_id : str
        Unique identifier for the account.
    name : str
        Human-readable name of the account.
    account_type : Literal["asset", "liability"]
        The type of the account (asset or liability).
    account_class : AccountClass
        The class of the account (e.g., 'cash', 'credit', 'investment').
    account_role : AccountRole
        The role of the account (e.g., 'checking', 'savings', 'credit_card').
    current_balance_minor : int
        The current balance of the account in minor units (e.g., cents).
    currency : str
        The currency of the account (e.g., "USD").
    is_active : bool
        Indicates if the account is currently active.
    opened_on : date | None
        The date the account was opened, if available.
    created_at : datetime | None
        Timestamp when the record was created.
    updated_at : datetime | None
        Timestamp when the record was last updated.
    """

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
        """
        Creates an AccountRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing account data, typically from a database query.

        Returns
        -------
        AccountRecord
            An instance of AccountRecord.
        """
        return cls(
            account_id=str(row.account_id),
            name=str(row.name),
            account_type=cast(Literal["asset", "liability"], str(row.account_type)),
            account_class=cast(AccountClass, str(row.account_class)),
            account_role=cast(AccountRole, str(row.account_role)),
            current_balance_minor=int(row.current_balance_minor),
            currency=str(row.currency),
            is_active=bool(row.is_active),
            opened_on=row.opened_on,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @property
    def is_credit_liability(self) -> bool:
        """
        Checks if the account is a credit liability account.

        Returns
        -------
        bool
            True if the account is a liability of type credit, False otherwise.
        """
        return self.account_type == "liability" and self.account_class == "credit"


@dataclass(frozen=True)
class ReferenceAccountRecord:
    """
    Represents a simplified view of a financial account, suitable for reference lists.

    This dataclass provides essential details for displaying accounts in selection lists
    or summaries, omitting audit fields for brevity.

    Attributes
    ----------
    account_id : str
        Unique identifier for the account.
    name : str
        Human-readable name of the account.
    account_type : Literal["asset", "liability"]
        The type of the account (asset or liability).
    account_class : AccountClass
        The class of the account (e.g., 'cash', 'credit', 'investment').
    account_role : AccountRole
        The role of the account (e.g., 'checking', 'savings', 'credit_card').
    current_balance_minor : int
        The current balance of the account in minor units (e.g., cents).
    """

    account_id: str
    name: str
    account_type: Literal["asset", "liability"]
    account_class: AccountClass
    account_role: AccountRole
    current_balance_minor: int

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "ReferenceAccountRecord":
        """
        Creates a ReferenceAccountRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing account data, typically from a database query.

        Returns
        -------
        ReferenceAccountRecord
            An instance of ReferenceAccountRecord.
        """
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
        """
        Checks if the account is a credit liability account.

        Returns
        -------
        bool
            True if the account is a liability of type credit, False otherwise.
        """
        return self.account_type == "liability" and self.account_class == "credit"



# Maps account classes to the SQL file names used for inserting their detailed records.
# This dictionary centralizes the logic for selecting the correct SQL script
# when adding specific detail entries for different types of accounts.
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
    """
    Represents a budgeting category.

    Attributes
    ----------
    category_id : str
        Unique identifier for the category.
    name : str
        Human-readable name of the category.
    is_active : bool
        Indicates if the category is currently active.
    is_system : bool
        Indicates if the category is a system-defined category.
    """

    category_id: str
    name: str
    is_active: bool
    is_system: bool

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "CategoryRecord":
        """
        Creates a CategoryRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing category data, typically from a database query.

        Returns
        -------
        CategoryRecord
            An instance of CategoryRecord.
        """
        return cls(
            category_id=str(row.category_id),
            name=str(row.name),
            is_active=bool(row.is_active),
            is_system=bool(row.is_system),
        )


@dataclass(frozen=True)
class ReferenceCategoryRecord:
    """
    Represents a simplified view of a budgeting category, suitable for reference lists.

    This dataclass provides essential details for displaying categories in selection lists
    or summaries, specifically including the available balance.

    Attributes
    ----------
    category_id : str
        Unique identifier for the category.
    name : str
        Human-readable name of the category.
    available_minor : int
        The available balance in the category in minor units (e.g., cents).
    """

    category_id: str
    name: str
    available_minor: int

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "ReferenceCategoryRecord":
        """
        Creates a ReferenceCategoryRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing category data, typically from a database query.

        Returns
        -------
        ReferenceCategoryRecord
            An instance of ReferenceCategoryRecord.
        """
        return cls(
            category_id=str(row.category_id),
            name=str(row.name),
            available_minor=int(row.available_minor),
        )


@dataclass(frozen=True)
class CategoryMonthStateRecord:
    """
    Represents the state of a budgeting category for a specific month.

    Attributes
    ----------
    category_id : str
        Unique identifier for the category.
    name : str
        Human-readable name of the category.
    available_minor : int
        The total available amount in the category for the month, in minor units.
    activity_minor : int
        The total activity (inflows/outflows) for the category during the month, in minor units.
    """

    category_id: str
    name: str
    available_minor: int
    activity_minor: int

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "CategoryMonthStateRecord":
        """
        Creates a CategoryMonthStateRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing category month state data, typically from a database query.

        Returns
        -------
        CategoryMonthStateRecord
            An instance of CategoryMonthStateRecord.
        """
        return cls(
            category_id=str(row.category_id),
            name=str(row.name),
            available_minor=int(row.available_minor),
            activity_minor=int(row.activity_minor),
        )


@dataclass(frozen=True)
class BudgetCategoryDetailRecord:
    """
    Represents a detailed record of a budgeting category, including monthly state.

    This dataclass provides a comprehensive view of a budgeting category,
    incorporating details about its goals, current availability, activity,
    and historical allocated/activity figures from the previous month.

    Attributes
    ----------
    category_id : str
        Unique identifier for the category.
    group_id : str | None
        Identifier for the category group this category belongs to, if any.
    name : str
        Human-readable name of the category.
    is_active : bool
        Indicates if the category is currently active.
    created_at : datetime
        Timestamp when the category record was created.
    updated_at : datetime
        Timestamp when the category record was last updated.
    goal_type : str | None
        The type of budgeting goal for this category (e.g., "target_balance", "monthly_savings").
    goal_amount_minor : int | None
        The target amount for the goal in minor units, if a goal is set.
    goal_target_date : date | None
        The target date for the goal, if applicable.
    goal_frequency : str | None
        The frequency of the goal (e.g., "monthly", "yearly").
    available_minor : int
        The total available amount in the category for the current month, in minor units.
    activity_minor : int
        The total activity (inflows/outflows) for the category during the current month, in minor units.
    allocated_minor : int
        The amount allocated to this category for the current month, in minor units.
    last_month_allocated_minor : int
        The amount allocated to this category for the previous month, in minor units.
    last_month_activity_minor : int
        The total activity for this category during the previous month, in minor units.
    last_month_available_minor : int
        The total available amount in the category from the previous month, in minor units.
    """

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
        """
        Creates a BudgetCategoryDetailRecord instance from a SimpleNamespace object.

        Handles optional fields and provides default values for previous month's data.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing detailed category data, typically from a database query.

        Returns
        -------
        BudgetCategoryDetailRecord
            An instance of BudgetCategoryDetailRecord.
        """
        # Ensure that previous month's data defaults to 0 if not present in the row.
        last_month_allocated = int(row.last_month_allocated_minor or 0)
        last_month_activity = int(row.last_month_activity_minor or 0)
        last_month_available = int(row.last_month_available_minor or 0)
        return cls(
            category_id=str(row.category_id),
            group_id=str(row.group_id) if row.group_id is not None else None,
            name=str(row.name),
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
            goal_type=str(row.goal_type) if row.goal_type is not None else None,
            goal_amount_minor=int(row.goal_amount_minor)
            if row.goal_amount_minor is not None
            else None,
            goal_target_date=row.goal_target_date,
            goal_frequency=str(row.goal_frequency)
            if row.goal_frequency is not None
            else None,
            available_minor=int(row.available_minor),
            activity_minor=int(row.activity_minor),
            allocated_minor=int(row.allocated_minor),
            last_month_allocated_minor=last_month_allocated,
            last_month_activity_minor=last_month_activity,
            last_month_available_minor=last_month_available,
        )


@dataclass(frozen=True)
class BudgetCategoryGroupRecord:
    """
    Represents a group of budgeting categories.

    Budget category groups help organize categories for better usability and reporting.

    Attributes
    ----------
    group_id : str
        Unique identifier for the category group.
    name : str
        Human-readable name of the category group.
    sort_order : int
        An integer indicating the display order of the group.
    is_active : bool
        Indicates if the category group is currently active.
    created_at : datetime
        Timestamp when the group record was created.
    updated_at : datetime
        Timestamp when the group record was last updated.
    """

    group_id: str
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "BudgetCategoryGroupRecord":
        """
        Creates a BudgetCategoryGroupRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing category group data, typically from a database query.

        Returns
        -------
        BudgetCategoryGroupRecord
            An instance of BudgetCategoryGroupRecord.
        """
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
    """
    Represents a specific version of a transaction.

    Transactions in the system can have multiple versions, and this record captures
    the details of one such version.

    Attributes
    ----------
    transaction_version_id : UUID
        Unique identifier for this specific transaction version.
    account_id : str
        The ID of the account involved in this transaction.
    category_id : str
        The ID of the category associated with this transaction.
    transaction_date : date
        The date on which the transaction occurred.
    amount_minor : int
        The amount of the transaction in minor units (e.g., cents).
    status : str
        The current status of the transaction (e.g., "cleared", "pending").
    """

    transaction_version_id: UUID
    account_id: str
    category_id: str
    transaction_date: date
    amount_minor: int
    status: str

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> "TransactionVersionRecord":
        """
        Creates a TransactionVersionRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing transaction version data, typically from a database query.

        Returns
        -------
        TransactionVersionRecord
            An instance of TransactionVersionRecord.
        """
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
    """
    Represents a transaction with expanded details for listing purposes.

    This dataclass includes additional descriptive fields like account and category names,
    making it suitable for displaying a list of transactions to the user.

    Attributes
    ----------
    transaction_version_id : UUID
        Unique identifier for the specific version of the transaction.
    concept_id : UUID
        The conceptual ID of the transaction, linking different versions of the same transaction.
    transaction_date : date
        The date on which the transaction occurred.
    account_id : str
        The ID of the account involved in this transaction.
    account_name : str
        The name of the account involved in this transaction.
    category_id : str
        The ID of the category associated with this transaction.
    category_name : str
        The name of the category associated with this transaction.
    amount_minor : int
        The amount of the transaction in minor units (e.g., cents).
    status : str
        The current status of the transaction (e.g., "cleared", "pending").
    memo : str | None
        An optional memo or description for the transaction.
    recorded_at : datetime
        Timestamp when this transaction version was recorded in the system.
    """

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
        """
        Creates a TransactionListRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing transaction data, typically from a database query.

        Returns
        -------
        TransactionListRecord
            An instance of TransactionListRecord.
        """
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
            memo=str(row.memo) if row.memo is not None else None,
            recorded_at=row.recorded_at,
        )


@dataclass(frozen=True)
class BudgetAllocationRecord:
    """
    Represents a record of an allocation of funds between budgeting categories.

    Attributes
    ----------
    allocation_id : UUID
        Unique identifier for this specific allocation event.
    allocation_date : date
        The date on which the allocation was made.
    amount_minor : int
        The amount of funds allocated, in minor units (e.g., cents).
    memo : str | None
        An optional memo or description for the allocation.
    from_category_id : str | None
        The ID of the category from which funds were allocated, if applicable.
    from_category_name : str | None
        The name of the category from which funds were allocated, if applicable.
    to_category_id : str
        The ID of the category to which funds were allocated.
    to_category_name : str
        The name of the category to which funds were allocated.
    created_at : datetime
        Timestamp when this allocation record was created.
    """

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
        """
        Creates a BudgetAllocationRecord instance from a SimpleNamespace object.

        Parameters
        ----------
        row : SimpleNamespace
            A SimpleNamespace object containing budget allocation data, typically from a database query.

        Returns
        -------
        BudgetAllocationRecord
            An instance of BudgetAllocationRecord.
        """
        return cls(
            allocation_id=UUID(str(row.allocation_id)),
            allocation_date=row.allocation_date,
            amount_minor=int(row.amount_minor),
            memo=str(row.memo) if row.memo is not None else None,
            from_category_id=str(row.from_category_id)
            if row.from_category_id is not None
            else None,
            from_category_name=str(row.from_category_name)
            if row.from_category_name is not None
            else None,
            to_category_id=str(row.to_category_id),
            to_category_name=str(row.to_category_name),
            created_at=row.created_at,
        )


class BudgetingDAO:
    """
    Encapsulates DuckDB reads and writes for budgeting services.

    This class provides a data access layer for budgeting-related operations,
    abstracting away direct SQL interactions. It manages database connections
    and provides methods for retrieving and manipulating budgeting data.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initializes the BudgetingDAO with a DuckDB connection.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object to be used for database operations.
        """
        self._conn = conn

    def _fetchone_namespace(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> SimpleNamespace | None:
        """
        Executes a SQL query and fetches a single row, returning it as a SimpleNamespace.

        Parameters
        ----------
        sql : str
            The SQL query string to execute.
        params : Sequence[Any] | None, optional
            A sequence of parameters to bind to the SQL query.

        Returns
        -------
        SimpleNamespace | None
            A SimpleNamespace object representing the fetched row, or None if no row is found.
        """
        # Execute the SQL query with optional parameters.
        cursor = self._conn.execute(sql, params or [])
        # Fetch a single row from the result.
        row = cursor.fetchone()
        if row is None:
            return None
        # Convert the fetched row into a SimpleNamespace for attribute-style access.
        return _row_to_namespace(cursor.description, row)

    def _fetchall_namespaces(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> list[SimpleNamespace]:
        """
        Executes a SQL query and fetches all rows, returning them as a list of SimpleNamespace objects.

        Parameters
        ----------
        sql : str
            The SQL query string to execute.
        params : Sequence[Any] | None, optional
            A sequence of parameters to bind to the SQL query.

        Returns
        -------
        list[SimpleNamespace]
            A list of SimpleNamespace objects, each representing a row from the query result.
            Returns an empty list if no rows are found.
        """
        # Execute the SQL query with optional parameters.
        cursor = self._conn.execute(sql, params or [])
        # Fetch all rows from the result.
        rows = cursor.fetchall()
        if not rows:
            return []
        # Convert each fetched row into a SimpleNamespace object.
        return [_row_to_namespace(cursor.description, row) for row in rows]

    # Transaction control -------------------------------------------------
    def begin(self) -> None:
        """
        Starts a new database transaction.
        All subsequent operations will be part of this transaction until committed or rolled back.
        """
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        """
        Commits the current database transaction.
        Makes all changes made since the last BEGIN permanent.
        """
        self._conn.execute("COMMIT")

    def rollback(self) -> None:
        """
        Rolls back the current database transaction.
        Discards all changes made since the last BEGIN.
        """
        self._conn.execute("ROLLBACK")

    @contextmanager
    def transaction(self) -> Generator["BudgetingDAO", None, None]:
        """
        Provides a transactional context for database operations.

        Usage
        -----
        with dao.transaction() as tx_dao:
            tx_dao.insert_something(...)
            tx_dao.update_something_else(...)

        All operations within the 'with' block are part of a single transaction.
        The transaction is committed if the block completes successfully,
        and rolled back if an exception occurs.

        Yields
        ------
        Generator["BudgetingDAO", None, None]
            The DAO instance itself, operating within the transaction.
        """
        self.begin()
        try:
            yield self
        except Exception:
            # If an error occurs, roll back the transaction to ensure data consistency.
            self.rollback()
            raise
        else:
            # If no errors, commit the transaction to persist changes.
            self.commit()

    # Account queries -----------------------------------------------------
    def get_active_account(self, account_id: str) -> AccountRecord | None:
        """
        Retrieves an active account by its ID.

        Parameters
        ----------
        account_id : str
            The ID of the account to retrieve.

        Returns
        -------
        AccountRecord | None
            An AccountRecord if an active account with the given ID is found, otherwise None.
        """
        # Execute SQL to select an active account and fetch a single row.
        row = self._fetchone_namespace(_sql("select_active_account.sql"), [account_id])
        if row is None:
            return None
        # Convert the fetched row into an AccountRecord.
        return AccountRecord.from_row(row)

    def get_account_detail(self, account_id: str) -> AccountRecord | None:
        """
        Retrieves a detailed account record by its ID, regardless of its active status.

        Parameters
        ----------
        account_id : str
            The ID of the account to retrieve.

        Returns
        -------
        AccountRecord | None
            An AccountRecord if an account with the given ID is found, otherwise None.
        """
        # Execute SQL to select account details and fetch a single row.
        row = self._fetchone_namespace(_sql("select_account_detail.sql"), [account_id])
        if row is None:
            return None
        # Convert the fetched row into an AccountRecord.
        return AccountRecord.from_row(row)

    def list_accounts(self) -> list[AccountRecord]:
        """
        Lists all accounts in the system.

        Returns
        -------
        list[AccountRecord]
            A list of all AccountRecord instances.
        """
        # Load the SQL query for selecting all accounts.
        sql = _sql("select_accounts_admin.sql")
        # Execute the query and fetch all rows.
        rows = self._fetchall_namespaces(sql)
        # Convert each fetched row into an AccountRecord.
        return [AccountRecord.from_row(row) for row in rows]

    def list_reference_accounts(self) -> list[ReferenceAccountRecord]:
        """
        Lists simplified account records suitable for reference or selection.

        Returns
        -------
        list[ReferenceAccountRecord]
            A list of ReferenceAccountRecord instances.
        """
        # Load the SQL query for selecting reference accounts.
        sql = _sql("select_reference_accounts.sql")
        # Execute the query and fetch all rows.
        rows = self._fetchall_namespaces(sql)
        # Convert each fetched row into a ReferenceAccountRecord.
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
        """
        Inserts a new account into the database.

        Parameters
        ----------
        account_id : str
            Unique identifier for the new account.
        name : str
            Name of the account.
        account_type : str
            Type of the account (e.g., "asset", "liability").
        account_class : str
            Class of the account (e.g., "cash", "credit").
        account_role : str
            Role of the account (e.g., "checking", "credit_card").
        current_balance_minor : int
            Initial balance in minor units.
        currency : str
            Currency of the account (e.g., "USD").
        is_active : bool
            Whether the account is active.
        opened_on : date | None
            Optional date when the account was opened.
        """
        # Load the SQL query for inserting a new account.
        sql = _sql("insert_account.sql")
        # Execute the insert query with the provided parameters.
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

    def insert_account_detail(
        self, account_class: AccountClass, account_id: str
    ) -> str:
        """
        Inserts a detailed record for a specific account class.

        This method uses a mapping to select the correct SQL insert statement
        based on the `account_class` and generates a new UUID for the detail record.

        Parameters
        ----------
        account_class : AccountClass
            The class of the account (e.g., "cash", "credit").
        account_id : str
            The ID of the account to associate the detail with.

        Returns
        -------
        str
            The UUID of the newly inserted account detail record.

        Raises
        ------
        ValueError
            If the provided `account_class` is not supported for detail insertion.
        """
        try:
            # Look up the appropriate SQL file name based on the account class.
            sql_name = ACCOUNT_DETAIL_INSERTS[account_class]
        except KeyError as exc:
            # Raise an error if an unsupported account class is provided.
            raise ValueError(
                f"Unsupported account_class `{account_class}` for detail insert."
            ) from exc
        # Generate a new UUID for the account detail record.
        detail_id = str(uuid4())
        # Load the specific SQL query for inserting account details.
        sql = _sql(sql_name)
        # Execute the insert query with the detail ID and account ID.
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
        """
        Updates an existing account's details in the database.

        Parameters
        ----------
        account_id : str
            The ID of the account to update.
        name : str
            New name for the account.
        account_type : str
            New type for the account.
        account_class : str
            New class for the account.
        account_role : str
            New role for the account.
        current_balance_minor : int
            New current balance in minor units.
        currency : str
            New currency for the account.
        opened_on : date | None
            New opened date for the account.
        is_active : bool
            New active status for the account.
        """
        # Load the SQL query for updating an account.
        sql = _sql("update_account.sql")
        # Execute the update query with the provided parameters.
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
        """
        Deactivates an account by setting its `is_active` status to false.

        Parameters
        ----------
        account_id : str
            The ID of the account to deactivate.
        """
        # Execute the SQL query to deactivate the specified account.
        self._conn.execute(_sql("deactivate_account.sql"), [account_id])

    # Category queries ----------------------------------------------------
    def get_active_category(self, category_id: str) -> CategoryRecord | None:
        """
        Retrieves an active budgeting category by its ID.

        Parameters
        ----------
        category_id : str
            The ID of the category to retrieve.

        Returns
        -------
        CategoryRecord | None
            A CategoryRecord if an active category with the given ID is found, otherwise None.
        """
        # Execute SQL to select an active category and fetch a single row.
        row = self._fetchone_namespace(
            _sql("select_active_category.sql"), [category_id]
        )
        if row is None:
            return None
        # Convert the fetched row into a CategoryRecord.
        return CategoryRecord.from_row(row)

    def get_category_optional(self, category_id: str) -> CategoryRecord | None:
        """
        Retrieves a category by its ID, returning None if inactive or not found.

        This method is useful when a category might exist but should only be considered
        if it's active.

        Parameters
        ----------
        category_id : str
            The ID of the category to retrieve.

        Returns
        -------
        CategoryRecord | None
            An active CategoryRecord if found, otherwise None.
        """
        # Execute SQL to select a category and fetch a single row.
        row = self._fetchone_namespace(
            _sql("select_active_category.sql"), [category_id]
        )
        if row is None:
            return None
        # Return None if the category is found but is not active.
        if not bool(row.is_active):
            return None
        # Convert the fetched row into a CategoryRecord.
        return CategoryRecord.from_row(row)

    def get_category_month_state(
        self, category_id: str, month_start: date
    ) -> CategoryMonthStateRecord | None:
        """
        Retrieves the monthly state of a specific budgeting category.

        Parameters
        ----------
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the month for which to retrieve the state.

        Returns
        -------
        CategoryMonthStateRecord | None
            A CategoryMonthStateRecord if found for the given category and month, otherwise None.
        """
        # Load the SQL query for selecting category monthly state.
        sql = _sql("select_category_month_state.sql")
        # Execute the query with month_start and category_id parameters.
        row = self._fetchone_namespace(sql, [month_start, category_id])
        if row is None:
            return None
        # Convert the fetched row into a CategoryMonthStateRecord.
        return CategoryMonthStateRecord.from_row(row)

    def get_budget_category_detail(
        self, category_id: str, month_start: date
    ) -> BudgetCategoryDetailRecord | None:
        """
        Retrieves detailed information for a budgeting category for a specific month.

        This includes current month's allocations and activity, as well as
        the previous month's summary.

        Parameters
        ----------
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the current month for which to retrieve details.

        Returns
        -------
        BudgetClassCategoryDetailRecord | None
            A BudgetClassCategoryDetailRecord if found, otherwise None.
        """
        # Load the SQL query for selecting budget category details.
        sql = _sql("select_budget_category_detail.sql")
        # Calculate the start of the previous month for historical data.
        previous_month = _previous_month_start(month_start)
        # Execute the query with current and previous month parameters.
        row = self._fetchone_namespace(sql, [month_start, previous_month, category_id])
        if row is None:
            return None
        # Convert the fetched row into a BudgetCategoryDetailRecord.
        return BudgetCategoryDetailRecord.from_row(row)

    def list_budget_categories(
        self, month: date, previous_month: date
    ) -> list[BudgetCategoryDetailRecord]:
        """
        Lists all budgeting categories with their details for the specified months.

        Parameters
        ----------
        month : date
            The start date of the current month.
        previous_month : date
            The start date of the previous month.

        Returns
        -------
        list[BudgetCategoryDetailRecord]
            A list of BudgetCategoryDetailRecord instances.
        """
        # Load the SQL query for selecting all budget categories with admin details.
        sql = _sql("select_budget_categories_admin.sql")
        # Prepare parameters for the query.
        params = [month, previous_month]
        # Execute the query and fetch all rows.
        rows = self._fetchall_namespaces(sql, params)
        # Convert each fetched row into a BudgetCategoryDetailRecord.
        return [BudgetCategoryDetailRecord.from_row(row) for row in rows]

    def list_reference_categories(self) -> list[ReferenceCategoryRecord]:
        """
        Lists simplified category records suitable for reference or selection.

        Returns
        -------
        list[ReferenceCategoryRecord]
            A list of ReferenceCategoryRecord instances.
        """
        # Load the SQL query for selecting reference categories.
        sql = _sql("select_reference_categories.sql")
        # Execute the query and fetch all rows.
        rows = self._fetchall_namespaces(sql)
        # Convert each fetched row into a ReferenceCategoryRecord.
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
        """
        Inserts a new budgeting category into the database.

        Parameters
        ----------
        category_id : str
            Unique identifier for the new category.
        group_id : str | None
            Optional group ID the category belongs to.
        name : str
            Name of the category.
        is_active : bool
            Whether the category is active.
        goal_type : str | None
            Type of goal for the category.
        goal_amount_minor : int | None
            Target amount for the goal in minor units.
        goal_target_date : date | None
            Target date for the goal.
        goal_frequency : str | None
            Frequency of the goal.
        """
        # Load the SQL query for inserting a new budget category.
        sql = _sql("insert_budget_category.sql")
        # Execute the insert query with the provided parameters.
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
        """
        Updates an existing budgeting category's details in the database.

        Parameters
        ----------
        category_id : str
            The ID of the category to update.
        name : str
            New name for the category.
        group_id : str | None
            New optional group ID the category belongs to.
        is_active : bool
            New active status for the category.
        goal_type : str | None
            New type of goal for the category.
        goal_amount_minor : int | None
            New target amount for the goal in minor units.
        goal_target_date : date | None
            New target date for the goal.
        goal_frequency : str | None
            New frequency of the goal.
        """
        # Load the SQL query for updating a budget category.
        sql = _sql("update_budget_category.sql")
        # Execute the update query with the provided parameters.
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
        """
        Deactivates a budgeting category by setting its `is_active` status to false.

        Parameters
        ----------
        category_id : str
            The ID of the category to deactivate.
        """
        # Execute the SQL query to deactivate the specified budget category.
        self._conn.execute(_sql("deactivate_budget_category.sql"), [category_id])

    # Category groups -----------------------------------------------------
    def list_budget_category_groups(self) -> list[BudgetCategoryGroupRecord]:
        """
        Lists all budgeting category groups.

        Returns
        -------
        list[BudgetCategoryGroupRecord]
            A list of BudgetCategoryGroupRecord instances.
        """
        # Load the SQL query for selecting all budget category groups.
        sql = _sql("select_budget_category_groups.sql")
        # Execute the query and fetch all rows.
        rows = self._fetchall_namespaces(sql)
        # Convert each fetched row into a BudgetCategoryGroupRecord.
        return [BudgetCategoryGroupRecord.from_row(row) for row in rows]

    def insert_budget_category_group(
        self,
        group_id: str,
        name: str,
        sort_order: int,
    ) -> BudgetCategoryGroupRecord | None:
        """
        Inserts a new budgeting category group.

        Parameters
        ----------
        group_id : str
            Unique identifier for the new group.
        name : str
            Name of the category group.
        sort_order : int
            Sorting order for the category group.

        Returns
        -------
        BudgetCategoryGroupRecord | None
            The newly created BudgetCategoryGroupRecord, or None if insertion fails.
        """
        # Load the SQL query for inserting a new budget category group.
        sql = _sql("insert_budget_category_group.sql")
        # Execute the insert query and fetch the single resulting row.
        row = self._fetchone_namespace(sql, [group_id, name, sort_order])
        if row is None:
            return None
        # Convert the fetched row into a BudgetCategoryGroupRecord.
        return BudgetCategoryGroupRecord.from_row(row)

    def update_budget_category_group(
        self,
        group_id: str,
        name: str,
        sort_order: int,
    ) -> BudgetCategoryGroupRecord | None:
        """
        Updates an existing budgeting category group's details.

        Parameters
        ----------
        group_id : str
            The ID of the category group to update.
        name : str
            New name for the category group.
        sort_order : int
            New sorting order for the category group.

        Returns
        -------
        BudgetCategoryGroupRecord | None
            The updated BudgetCategoryGroupRecord, or None if the update fails or group not found.
        """
        # Load the SQL query for updating a budget category group.
        sql = _sql("update_budget_category_group.sql")
        # Execute the update query and fetch the single resulting row.
        row = self._fetchone_namespace(sql, [name, sort_order, group_id])
        if row is None:
            return None
        # Convert the fetched row into a BudgetCategoryGroupRecord.
        return BudgetCategoryGroupRecord.from_row(row)

    def deactivate_budget_category_group(self, group_id: str) -> None:
        """
        Deactivates a budgeting category group.

        Parameters
        ----------
        group_id : str
            The ID of the category group to deactivate.
        """
        # Execute the SQL query to deactivate the specified budget category group.
        self._conn.execute(_sql("deactivate_budget_category_group.sql"), [group_id])

    def get_budget_category_group(
        self, group_id: str
    ) -> BudgetCategoryGroupRecord | None:
        """
        Retrieves a budgeting category group by its ID.

        Parameters
        ----------
        group_id : str
            The ID of the category group to retrieve.

        Returns
        -------
        BudgetCategoryGroupRecord | None
            A BudgetCategoryGroupRecord if found, otherwise None.
        """
        # Load the SQL query for selecting a budget category group.
        sql = _sql("select_budget_category_group.sql")
        # Execute the query and fetch a single row.
        row = self._fetchone_namespace(sql, [group_id])
        if row is None:
            return None
        # Convert the fetched row into a BudgetCategoryGroupRecord.
        return BudgetCategoryGroupRecord.from_row(row)

    # Transactions --------------------------------------------------------
    def get_active_transaction(
        self, concept_id: UUID | str
    ) -> TransactionVersionRecord | None:
        """
        Retrieves the active version of a transaction by its concept ID.

        Parameters
        ----------
        concept_id : UUID | str
            The conceptual ID of the transaction to retrieve.

        Returns
        -------
        TransactionVersionRecord | None
            An active TransactionVersionRecord if found, otherwise None.
        """
        # Load the SQL query for selecting an active transaction.
        sql = _sql("select_active_transaction.sql")
        # Execute the query and fetch a single row.
        row = self._fetchone_namespace(sql, [str(concept_id)])
        if row is None:
            return None
        # Convert the fetched row into a TransactionVersionRecord.
        return TransactionVersionRecord.from_row(row)

    def close_active_transaction(
        self, concept_id: UUID | str, recorded_at: datetime
    ) -> None:
        """
        Closes the active version of a transaction.

        This effectively marks the transaction as no longer active, typically
        used when a new version of the transaction is created or it's finalized.

        Parameters
        ----------
        concept_id : UUID | str
            The conceptual ID of the transaction to close.
        recorded_at : datetime
            The timestamp to record when the transaction was closed.
        """
        # Load the SQL query for closing an active transaction.
        sql = _sql("close_active_transaction.sql")
        # Execute the update query with the recorded_at timestamp and concept ID.
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
        """
        Inserts a new transaction version into the database.

        This method records a new state or creation of a transaction.

        Parameters
        ----------
        transaction_version_id : UUID
            Unique identifier for this specific transaction version.
        concept_id : UUID
            The conceptual ID linking different versions of the same transaction.
        account_id : str
            The ID of the account involved.
        category_id : str
            The ID of the category associated.
        transaction_date : date
            The date of the transaction.
        amount_minor : int
            The amount in minor units.
        memo : str | None
            Optional memo for the transaction.
        status : str
            The status of the transaction.
        recorded_at : datetime
            Timestamp when this version was recorded.
        source : str
            The source of the transaction (e.g., "manual", "import").
        """
        # Load the SQL query for inserting a transaction.
        sql = _sql("insert_transaction.sql")
        # Execute the insert query with all provided transaction details.
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
        """
        Updates the current balance of an account.

        Parameters
        ----------
        account_id : str
            The ID of the account to update.
        amount_minor : int
            The new balance amount in minor units.
        """
        # Load the SQL query for updating an account's balance.
        sql = _sql("update_account_balance.sql")
        # Execute the update query with the new amount and account ID.
        self._conn.execute(sql, [amount_minor, account_id])

    def upsert_category_activity(
        self, category_id: str, month_start: date, activity_delta: int
    ) -> None:
        """
        Updates or inserts the activity for a budgeting category for a specific month.

        This method handles both creation of a new monthly state or updating
        an existing one based on transaction activity.

        Parameters
        ----------
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the month.
        activity_delta : int
            The change in activity amount (in minor units).
        """
        # Load the SQL query for upserting category monthly state.
        sql = _sql("upsert_category_monthly_state.sql")
        # Execute the upsert query. The `activity_delta` is used twice for UPSERT logic.
        self._conn.execute(
            sql, [category_id, month_start, activity_delta, activity_delta]
        )

    def adjust_category_allocation(
        self,
        category_id: str,
        month_start: date,
        allocated_delta: int,
        available_delta: int,
    ) -> None:
        """
        Adjusts the allocated and available amounts for a budgeting category in a given month.

        Parameters
        ----------
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the month.
        allocated_delta : int
            The change in the allocated amount (in minor units).
        available_delta : int
            The change in the available amount (in minor units).
        """
        # Load the SQL query for adjusting category allocation.
        sql = _sql("adjust_category_allocation.sql")
        # Execute the update query with the provided deltas.
        self._conn.execute(
            sql, [category_id, month_start, allocated_delta, available_delta]
        )

    def adjust_category_inflow(
        self,
        category_id: str,
        month_start: date,
        inflow_delta: int,
        available_delta: int,
    ) -> None:
        """
        Adjusts the inflow and available amounts for a budgeting category in a given month.

        Parameters
        ----------
        category_id : str
            The ID of the category.
        month_start : date
            The start date of the month.
        inflow_delta : int
            The change in the inflow amount (in minor units).
        available_delta : int
            The change in the available amount (in minor units).
        """
        # Load the SQL query for adjusting category inflow.
        sql = _sql("adjust_category_inflow.sql")
        # Execute the update query with the provided deltas.
        self._conn.execute(
            sql, [category_id, month_start, inflow_delta, available_delta]
        )

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
        """
        Inserts a new budget allocation record into the database.

        Parameters
        ----------
        allocation_id : UUID
            Unique identifier for this allocation.
        allocation_date : date
            The date when the allocation was made.
        month_start : date
            The start date of the month this allocation applies to.
        from_category_id : str | None
            ID of the source category for the allocation (if any).
        to_category_id : str
            ID of the destination category for the allocation.
        amount_minor : int
            The amount allocated in minor units.
        memo : str | None
            Optional memo for the allocation.
        """
        # Load the SQL query for inserting a budget allocation.
        sql = _sql("insert_budget_allocation.sql")
        # Execute the insert query with all provided allocation details.
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
        """
        Lists a specified number of most recent transactions.

        Parameters
        ----------
        limit : int
            The maximum number of recent transactions to retrieve.

        Returns
        -------
        list[TransactionListRecord]
            A list of TransactionListRecord instances representing recent transactions.
        """
        # Load the SQL query for selecting recent transactions.
        sql = _sql("select_recent_transactions.sql")
        # Execute the query with the limit and fetch all rows.
        rows = self._fetchall_namespaces(sql, [limit])
        # Convert each fetched row into a TransactionListRecord.
        return [TransactionListRecord.from_row(row) for row in rows]

    def list_budget_allocations(
        self, month_start: date, limit: int
    ) -> list[BudgetAllocationRecord]:
        """
        Lists budget allocations for a specific month, with an optional limit.

        Parameters
        ----------
        month_start : date
            The start date of the month for which to list allocations.
        limit : int
            The maximum number of allocations to retrieve.

        Returns
        -------
        list[BudgetAllocationRecord]
            A list of BudgetAllocationRecord instances for the specified month.
        """
        # Load the SQL query for selecting budget allocations.
        sql = _sql("select_budget_allocations.sql")
        # Execute the query with month_start and limit, then fetch all rows.
        rows = self._fetchall_namespaces(sql, [month_start, limit])
        # Convert each fetched row into a BudgetAllocationRecord.
        return [BudgetAllocationRecord.from_row(row) for row in rows]

    def ready_to_assign(self, month_start: date) -> int:
        """
        Calculates the "Ready to Assign" amount for a given month.

        This amount represents funds available to be allocated to categories.

        Parameters
        ----------
        month_start : date
            The start date of the month to calculate "Ready to Assign" for.

        Returns
        -------
        int
            The "Ready to Assign" amount in minor units. Returns 0 if not found or on CatalogException.
        """
        # Load the SQL query for selecting the ready-to-assign amount.
        sql = _sql("select_ready_to_assign.sql")
        try:
            # Execute the query and fetch a single row.
            row = self._fetchone_namespace(sql, [month_start])
        except duckdb.CatalogException:
            # Handle cases where the required tables might not exist (e.g., initial setup).
            return 0
        if row is None:
            return 0
        # Extract and return the ready-to-assign amount.
        return int(row.ready_to_assign_minor or 0)

    def month_cash_inflow(self, month_start: date) -> int:
        """
        Calculates the total cash inflow for a given month.

        Parameters
        ----------
        month_start : date
            The start date of the month to calculate cash inflow for.

        Returns
        -------
        int
            The total cash inflow amount in minor units. Returns 0 if not found or on CatalogException.
        """
        # Load the SQL query for summing month cash inflows.
        sql = _sql("sum_month_cash_inflows.sql")
        try:
            # Execute the query and fetch a single row. The month_start is used twice in the SQL for range.
            row = self._fetchone_namespace(sql, [month_start, month_start])
        except duckdb.CatalogException:
            # Handle cases where the required tables might not exist.
            return 0
        if row is None:
            return 0
        # Extract and return the inflow amount.
        return int(row.inflow_minor or 0)

    # Credit payment helpers ---------------------------------------------
    def upsert_credit_payment_group(
        self,
        group_id: str,
        name: str,
        sort_order: int,
    ) -> None:
        """
        Inserts or updates a credit payment group.

        This method is used to manage groups specifically for credit payments,
        allowing for organization and sorting.

        Parameters
        ----------
        group_id : str
            Unique identifier for the credit payment group.
        name : str
            Name of the credit payment group.
        sort_order : int
            Sorting order for the group.
        """
        # Load the SQL query for upserting a credit payment group.
        sql = _sql("upsert_credit_payment_group.sql")
        # Execute the upsert query with the provided details.
        self._conn.execute(sql, [group_id, name, sort_order])

    def upsert_credit_payment_category(
        self,
        category_id: str,
        group_id: str,
        name: str,
    ) -> None:
        """
        Inserts or updates a credit payment category.

        This method manages categories specifically for credit payments,
        associating them with a credit payment group.

        Parameters
        ----------
        category_id : str
            Unique identifier for the credit payment category.
        group_id : str
            The group ID this credit payment category belongs to.
        name : str
            Name of the credit payment category.
        """
        # Load the SQL query for upserting a credit payment category.
        sql = _sql("upsert_credit_payment_category.sql")
        # Execute the upsert query with the provided details.
        self._conn.execute(sql, [category_id, group_id, name])
