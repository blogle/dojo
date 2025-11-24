"""Pydantic schemas for budgeting APIs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Maximum length for names (e.g., account names, category names).
NAME_MAX_LENGTH = 120
# Standard length for currency ISO codes (e.g., "USD").
CURRENCY_CODE_LENGTH = 3
# Default currency code used in the application.
DEFAULT_CURRENCY_CODE = "USD"


class NewTransactionRequest(BaseModel):
    """
    Incoming transaction payload from the SPA (Single Page Application).

    This schema defines the structure for requests to create new transactions,
    including details necessary for ledger entry and budgeting impact.

    Attributes
    ----------
    concept_id : Optional[UUID]
        Stable identifier for the logical transaction.
        Used to group multiple related transaction versions.
    transaction_date : date
        Date the transaction occurred.
    account_id : str
        The ID of the account to be impacted by this transaction.
    category_id : str
        The ID of the budget category to be impacted by this transaction.
    amount_minor : int
        Signed minor-unit amount (e.g., cents or pennies) of the transaction.
        Positive for inflow, negative for outflow.
    status : Literal["pending", "cleared"]
        Ledger status used for reconciliation.
        "pending" for transactions not yet finalized, "cleared" for finalized transactions.
    memo : Optional[str]
        Optional free-form note or description for the transaction.
    """

    concept_id: Optional[UUID] = Field(
        default=None, description="Stable identifier for the logical transaction."
    )
    transaction_date: date = Field(description="Date the transaction occurred.")
    account_id: str = Field(min_length=1, description="Account to impact.")
    category_id: str = Field(min_length=1, description="Budget category to impact.")
    amount_minor: int = Field(description="Signed minor-unit amount (e.g., cents).")
    status: Literal["pending", "cleared"] = Field(
        default="pending", description="Ledger status used for reconciliation."
    )
    memo: Optional[str] = Field(default=None, description="Optional free-form note.")


class CategorizedTransferRequest(BaseModel):
    """
    Payload describing a double-entry transfer between accounts, potentially categorized.

    This schema defines the request structure for moving funds, where one leg
    of the transfer might be categorized within the budgeting system.

    Attributes
    ----------
    source_account_id : str
        Account ID from which funds are being moved.
    destination_account_id : str
        Account ID to which funds are being moved.
    category_id : str
        Budget category for the budgeted leg of the transfer.
        This category will reflect the inflow or outflow for budgeting purposes.
    amount_minor : int
        Positive amount in minor units (e.g., cents) to move.
    transaction_date : date
        Date the transfer occurred.
    memo : Optional[str]
        Optional comment or note that applies to both legs of the transfer.
    concept_id : Optional[UUID]
        Optional shared concept identifier, linking this transfer to a broader financial event.
    """

    source_account_id: str = Field(
        min_length=1, description="Account ID funds are moving from."
    )
    destination_account_id: str = Field(
        min_length=1, description="Account ID funds are moving to."
    )
    category_id: str = Field(
        min_length=1, description="Budget category for the budgeted leg."
    )
    amount_minor: int = Field(
        gt=0, description="Positive amount in minor units to move."
    )
    transaction_date: date = Field(description="Date the transfer occurred.")
    memo: Optional[str] = Field(
        default=None, description="Optional comment for both legs."
    )
    concept_id: Optional[UUID] = Field(
        default=None, description="Optional shared concept identifier."
    )


# Defines the literal types for various account classifications.
AccountClass = Literal["cash", "credit", "investment", "accessible", "loan", "tangible"]
# Defines the literal types for the role of an account in budgeting.
AccountRole = Literal["on_budget", "tracking"]


class AccountState(BaseModel):
    """
    Account balances and key attributes surfaced to the SPA (Single Page Application).

    This schema provides a summary of an account's current state, suitable for
    display in user interfaces.

    Attributes
    ----------
    account_id : str
        Unique identifier for the account.
    name : str
        Human-readable name of the account.
    account_type : Literal["asset", "liability"]
        The type of the account (asset or liability).
    account_class : AccountClass
        The class of the account (e.g., 'cash', 'credit').
    account_role : AccountRole
        The role of the account (e.g., 'on_budget', 'tracking').
    current_balance_minor : int
        The current balance of the account in minor units (e.g., cents).
    """

    account_id: str
    name: str
    account_type: Literal["asset", "liability"]
    account_class: AccountClass
    account_role: AccountRole
    current_balance_minor: int


class CategoryState(BaseModel):
    """
    Budget category state for the active month.

    This schema provides a snapshot of a budgeting category's financial status
    for a given month, including available funds and activity.

    Attributes
    ----------
    category_id : str
        Unique identifier for the category.
    name : str
        Human-readable name of the category.
    available_minor : int
        The total available amount in the category for the month, in minor units.
    activity_minor : int
        Month-to-date activity in minor units (inflows/outflows affecting the category).
    """

    category_id: str
    name: str
    available_minor: int
    activity_minor: int = Field(
        default=0, description="Month-to-date activity in minor units."
    )


class TransactionResponse(BaseModel):
    """
    Response payload after inserting a transaction.

    This schema provides confirmation and details of a newly created or updated
    transaction, including its impact on related account and category states.

    Attributes
    ----------
    transaction_version_id : UUID
        Unique identifier for the specific version of the transaction.
    concept_id : UUID
        The conceptual ID of the transaction.
    amount_minor : int
        The amount of the transaction in minor units.
    transaction_date : date
        The date on which the transaction occurred.
    status : Literal["pending", "cleared"]
        The current status of the transaction.
    memo : Optional[str]
        Optional memo for the transaction.
    account : AccountState
        The state of the account after the transaction.
    category : CategoryState
        The state of the category after the transaction.
    """

    transaction_version_id: UUID
    concept_id: UUID
    amount_minor: int
    transaction_date: date
    status: Literal["pending", "cleared"]
    memo: Optional[str]
    account: AccountState
    category: CategoryState


class ReferenceDataResponse(BaseModel):
    """
    Reference data shape for dropdowns and initial application loading.

    This schema aggregates essential lists of accounts and categories in their
    simplified state for efficient frontend rendering.

    Attributes
    ----------
    accounts : list[AccountState]
        A list of simplified account states.
    categories : list[CategoryState]
        A list of simplified category states.
    """

    accounts: list[AccountState]
    categories: list[CategoryState]


class TransactionListItem(BaseModel):
    """
    Serialized transaction row for spreadsheet UI.

    This schema provides a detailed view of a transaction, enriched with
    account and category names for easy display in transaction lists.

    Attributes
    ----------
    transaction_version_id : UUID
        Unique identifier for the specific version of the transaction.
    concept_id : UUID
        The conceptual ID of the transaction.
    transaction_date : date
        The date on which the transaction occurred.
    account_id : str
        The ID of the account involved.
    account_name : str
        The name of the account involved.
    category_id : str
        The ID of the category associated.
    category_name : str
        The name of the category associated.
    amount_minor : int
        The amount of the transaction in minor units.
    status : Literal["pending", "cleared"]
        The current status of the transaction.
    memo : Optional[str]
        Optional memo for the transaction.
    recorded_at : datetime
        Timestamp when this transaction version was recorded.
    """

    transaction_version_id: UUID
    concept_id: UUID
    transaction_date: date
    account_id: str
    account_name: str
    category_id: str
    category_name: str
    amount_minor: int
    status: Literal["pending", "cleared"]
    memo: Optional[str]
    recorded_at: datetime


class NetWorthDelta(BaseModel):
    """
    Placeholder for future response objects that include net worth changes.

    This schema is intended to represent changes in net worth, providing both
    minor unit integer values and a decimal representation.

    Attributes
    ----------
    net_worth_minor : int
        Net worth in minor units.
    net_worth_decimal : Decimal
        Net worth expressed in whole units (Decimal).
    """

    net_worth_minor: int
    net_worth_decimal: Decimal


class CategorizedTransferLeg(BaseModel):
    """
    Details for a single leg of a categorized transfer.

    Attributes
    ----------
    transaction_version_id : UUID
        Unique identifier for the transaction version representing this leg.
    account : AccountState
        The state of the account involved in this leg.
    """

    transaction_version_id: UUID
    account: AccountState


class CategorizedTransferResponse(BaseModel):
    """
    Response payload that captures the results of a categorized transfer.

    This schema provides details about the conceptual transaction, its individual
    legs, and the impact on the involved category.

    Attributes
    ----------
    concept_id : UUID
        The conceptual ID of the transfer.
    budget_leg : CategorizedTransferLeg
        Details of the leg related to the budgeting category.
    transfer_leg : CategorizedTransferLeg
        Details of the leg representing the direct fund transfer between accounts.
    category : CategoryState
        The state of the budgeting category after the transfer.
    """

    concept_id: UUID
    budget_leg: CategorizedTransferLeg
    transfer_leg: CategorizedTransferLeg
    category: CategoryState


class ReadyToAssignResponse(BaseModel):
    """
    Surface Ready to Assign (RTA) for a given month.

    This schema provides the total amount of funds available to be allocated
    to budgeting categories for a specific month.

    Attributes
    ----------
    month_start : date
        The start date of the month (YYYY-MM-01) for which RTA is calculated.
    ready_to_assign_minor : int
        The "Ready to Assign" amount in minor units.
    ready_to_assign_decimal : Decimal
        The "Ready to Assign" amount expressed in whole units (Decimal).
    """

    month_start: date
    ready_to_assign_minor: int
    ready_to_assign_decimal: Decimal


class BudgetAllocationRequest(BaseModel):
    """
    Move Ready-to-Assign funds or reassign funds between envelopes.

    This schema defines the request structure for allocating or reallocating
    funds within the budgeting system.

    Attributes
    ----------
    category_id : str | None
        Deprecated alias for `to_category_id`.
        The destination category receiving funds.
    to_category_id : str | None
        The ID of the destination category receiving funds.
    from_category_id : str | None
        Optional ID of the source category providing funds.
        If None, funds are assumed to come from "Ready to Assign".
    amount_minor : int
        Positive amount in minor units to allocate or reallocate.
    allocation_date : date | None
        Date the allocation is recorded (defaults to today if None).
    memo : Optional[str]
        Optional note for the allocation ledger entry.
    month_start : date | None
        Optional month override (YYYY-MM-01) for the allocation.
        Defaults to the current month if None.
    """

    category_id: str | None = Field(
        default=None, description="Deprecated alias for `to_category_id`."
    )
    to_category_id: str | None = Field(
        default=None, description="Destination category receiving funds."
    )
    from_category_id: str | None = Field(
        default=None, description="Optional source category providing funds."
    )
    amount_minor: int = Field(gt=0)
    allocation_date: date | None = Field(
        default=None, description="Date the allocation is recorded (defaults to today)."
    )
    memo: Optional[str] = Field(
        default=None, description="Optional note for the allocation ledger."
    )
    month_start: date | None = Field(
        default=None, description="Optional month override (YYYY-MM-01)."
    )


# Regular expression pattern for valid slug-like identifiers (lowercase letters, numbers, underscores).
SLUG_PATTERN = r"^[a-z0-9_]+$"


class BudgetAllocationEntry(BaseModel):
    """
    Single ledger entry describing a budget allocation.

    This schema represents an individual record of funds being allocated
    to or from a budgeting category.

    Attributes
    ----------
    allocation_id : UUID
        Unique identifier for the allocation event.
    allocation_date : date
        The date on which the allocation was recorded.
    amount_minor : int
        The amount of funds allocated in minor units.
    from_category_id : Optional[str]
        The ID of the category from which funds were moved (if applicable).
    from_category_name : Optional[str]
        The name of the category from which funds were moved (if applicable).
    to_category_id : str
        The ID of the category to which funds were moved.
    to_category_name : str
        The name of the category to which funds were moved.
    memo : Optional[str]
        Optional note associated with the allocation.
    created_at : datetime
        Timestamp when this allocation entry was created in the system.
    """

    allocation_id: UUID
    allocation_date: date
    amount_minor: int
    from_category_id: Optional[str]
    from_category_name: Optional[str]
    to_category_id: str
    to_category_name: str
    memo: Optional[str]
    created_at: datetime


class BudgetAllocationsResponse(BaseModel):
    """
    Allocation ledger plus month summary information.

    This schema provides a comprehensive view of all budget allocations
    for a specific month, alongside summary figures like total inflow
    and "Ready to Assign" amounts.

    Attributes
    ----------
    month_start : date
        The start date of the month (YYYY-MM-01) for which allocations are reported.
    inflow_minor : int
        Total cash inflow for the month in minor units.
    inflow_decimal : Decimal
        Total cash inflow for the month expressed in whole units (Decimal).
    ready_to_assign_minor : int
        The "Ready to Assign" amount for the month in minor units.
    ready_to_assign_decimal : Decimal
        The "Ready to Assign" amount for the month expressed in whole units (Decimal).
    allocations : list[BudgetAllocationEntry]
        A list of individual budget allocation entries for the month.
    """

    month_start: date
    inflow_minor: int
    inflow_decimal: Decimal
    ready_to_assign_minor: int
    ready_to_assign_decimal: Decimal
    allocations: list[BudgetAllocationEntry]


class AccountCommand(BaseModel):
    """
    Shared fields for account create/update operations with class metadata.

    This base schema defines the common attributes required when creating or
    modifying a financial account, ensuring consistency across different
    account-related requests.

    Attributes
    ----------
    name : str
        Human-readable name of the account.
    account_type : Literal["asset", "liability"]
        The type of the account (asset or liability).
    account_class : AccountClass
        Logical class of the account used for grouping and reporting.
        Defaults to "cash".
    account_role : AccountRole
        Indicates whether the account contributes to the budget or is tracking-only.
        Defaults to "on_budget".
    current_balance_minor : int
        Current balance of the account in minor units (e.g., cents).
    currency : str
        The currency code (e.g., "USD") of the account.
    opened_on : Optional[date]
        Optional date when the account was opened.
    is_active : bool
        Marks whether the account can be used for new transactions.
        Defaults to True.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    account_type: Literal["asset", "liability"]
    account_class: AccountClass = Field(
        default="cash",
        description="Logical class of the account used for grouping and reporting.",
    )
    account_role: AccountRole = Field(
        default="on_budget",
        description="Indicates whether the account contributes to the budget or is tracking-only.",
    )
    current_balance_minor: int = Field(description="Current balance in minor units.")
    currency: str = Field(
        default=DEFAULT_CURRENCY_CODE,
        min_length=CURRENCY_CODE_LENGTH,
        max_length=CURRENCY_CODE_LENGTH,
    )
    opened_on: Optional[date] = Field(
        default=None, description="Optional account open date."
    )
    is_active: bool = Field(
        default=True,
        description="Marks whether the account can be used for new transactions.",
    )


class AccountCreateRequest(AccountCommand):
    """
    Payload for creating a new account.

    Extends `AccountCommand` by adding the `account_id` field, which is required
    when initially creating an account.

    Attributes
    ----------
    account_id : str
        Stable identifier for the account. Must match `SLUG_PATTERN`.
    """

    account_id: str = Field(
        pattern=SLUG_PATTERN, description="Stable identifier for the account."
    )


class AccountUpdateRequest(AccountCommand):
    """
    Payload for editing an existing account.

    Inherits all fields from `AccountCommand`, providing the mutable attributes
    for updating an account.
    """


class AccountDetail(AccountCommand):
    """
    Serialized account data for the admin UI.

    Extends `AccountCommand` with read-only audit fields such as `account_id`,
    `created_at`, and `updated_at`, providing a full view of an account's state
    for administrative purposes.

    Attributes
    ----------
    account_id : str
        Unique identifier for the account.
    created_at : datetime
        Timestamp when the account record was created.
    updated_at : datetime
        Timestamp when the account record was last updated.
    """

    account_id: str
    created_at: datetime
    updated_at: datetime


class BudgetCategoryCommand(BaseModel):
    """
    Shared fields for budget category mutations.

    This base schema defines the common attributes for creating or updating
    budgeting categories, including goal-related fields.

    Attributes
    ----------
    name : str
        Human-readable name of the category.
    group_id : Optional[str]
        Optional parent category group ID.
    is_active : bool
        Indicates if the category is currently active. Defaults to True.
    goal_type : Optional[Literal["target_date", "recurring"]]
        The type of budgeting goal for this category, if any.
    goal_amount_minor : Optional[int]
        The target amount for the goal in minor units, if a goal is set.
    goal_target_date : Optional[date]
        The target date for the goal, if applicable.
    goal_frequency : Optional[Literal["monthly", "quarterly", "yearly"]]
        The frequency of the goal, if applicable.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    group_id: Optional[str] = Field(
        default=None, description="Parent category group ID."
    )
    is_active: bool = Field(default=True)
    goal_type: Optional[Literal["target_date", "recurring"]] = Field(default=None)
    goal_amount_minor: Optional[int] = Field(default=None)
    goal_target_date: Optional[date] = Field(default=None)
    goal_frequency: Optional[Literal["monthly", "quarterly", "yearly"]] = Field(
        default=None
    )


class BudgetCategoryGroupCommand(BaseModel):
    """
    Shared fields for budget category group mutations.

    This base schema defines the common attributes for creating or updating
    budgeting category groups, used for organizing categories.

    Attributes
    ----------
    name : str
        Human-readable name of the category group.
    sort_order : int
        An integer indicating the display order of the group. Defaults to 0.
    is_active : bool
        Indicates if the category group is currently active. Defaults to True.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class BudgetCategoryGroupCreateRequest(BudgetCategoryGroupCommand):
    """
    Payload for creating a new category group.

    Extends `BudgetCategoryGroupCommand` by adding the `group_id` field,
    which is required when initially creating a category group.

    Attributes
    ----------
    group_id : str
        Stable identifier for the group. Must match `SLUG_PATTERN`.
    """

    group_id: str = Field(
        pattern=SLUG_PATTERN, description="Stable identifier for the group."
    )


class BudgetCategoryGroupUpdateRequest(BudgetCategoryGroupCommand):
    """
    Payload for editing an existing category group.

    Inherits all fields from `BudgetCategoryGroupCommand`, providing the mutable attributes
    for updating a category group.
    """


class BudgetCategoryGroupDetail(BudgetCategoryGroupCommand):
    """
    Serialized category group data.

    Extends `BudgetCategoryGroupCommand` with read-only audit fields such as `group_id`,
    `created_at`, and `updated_at`, providing a full view of a category group's state.

    Attributes
    ----------
    group_id : str
        Unique identifier for the category group.
    created_at : datetime
        Timestamp when the group record was created.
    updated_at : datetime
        Timestamp when the group record was last updated.
    """

    group_id: str
    created_at: datetime
    updated_at: datetime


class BudgetCategoryCreateRequest(BudgetCategoryCommand):
    """
    Payload for creating a budget category.

    Extends `BudgetCategoryCommand` by adding an optional `category_id` field.
    If not provided, the backend can generate one.

    Attributes
    ----------
    category_id : Optional[str]
        Stable identifier for the category. Must match `SLUG_PATTERN`.
        If None, a new ID will be generated.
    """

    category_id: Optional[str] = Field(
        default=None,
        pattern=SLUG_PATTERN,
        description="Stable identifier for the category.",
    )


class BudgetCategoryUpdateRequest(BudgetCategoryCommand):
    """
    Payload for editing a budget category.

    Inherits all fields from `BudgetCategoryCommand`, providing the mutable attributes
    for updating a budgeting category.
    """


class BudgetCategoryDetail(BudgetCategoryCommand):
    """
    Serialized budget category data for the admin UI.

    Extends `BudgetCategoryCommand` with read-only audit fields and current
    monthly state information, providing a comprehensive view of a category's
    status for administrative purposes.

    Attributes
    ----------
    category_id : str
        Unique identifier for the category.
    group_id : Optional[str]
        Parent category group ID.
    created_at : datetime
        Timestamp when the category record was created.
    updated_at : datetime
        Timestamp when the category record was last updated.
    available_minor : int
        Current available funds for the month in minor units. Defaults to 0.
    activity_minor : int
        Month-to-date activity amount in minor units. Defaults to 0.
    allocated_minor : int
        Month-to-date allocations applied to this envelope in minor units. Defaults to 0.
    last_month_allocated_minor : int
        Allocated amount from the previous month. Defaults to 0.
    last_month_activity_minor : int
        Activity amount from the previous month. Defaults to 0.
    last_month_available_minor : int
        Available amount from the previous month. Defaults to 0.
    """

    category_id: str
    group_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    available_minor: int = Field(
        default=0, description="Current available funds for the month in minor units."
    )
    activity_minor: int = Field(
        default=0, description="Month-to-date activity amount in minor units."
    )
    allocated_minor: int = Field(
        default=0,
        description="Month-to-date allocations applied to this envelope in minor units.",
    )
    last_month_allocated_minor: int = Field(
        default=0, description="Allocated amount from the previous month."
    )
    last_month_activity_minor: int = Field(
        default=0, description="Activity amount from the previous month."
    )
    last_month_available_minor: int = Field(
        default=0, description="Available amount from the previous month."
    )
