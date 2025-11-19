"""Pydantic schemas for budgeting APIs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NewTransactionRequest(BaseModel):
    """Incoming transaction payload from the SPA."""

    concept_id: Optional[UUID] = Field(default=None, description="Stable identifier for the logical transaction.")
    transaction_date: date = Field(description="Date the transaction occurred.")
    account_id: str = Field(min_length=1, description="Account to impact.")
    category_id: str = Field(min_length=1, description="Budget category to impact.")
    amount_minor: int = Field(description="Signed minor-unit amount (e.g., cents).")
    memo: Optional[str] = Field(default=None, description="Optional free-form note.")


class CategorizedTransferRequest(BaseModel):
    """Payload describing a double-entry transfer between accounts."""

    source_account_id: str = Field(min_length=1, description="Account ID funds are moving from.")
    destination_account_id: str = Field(min_length=1, description="Account ID funds are moving to.")
    category_id: str = Field(min_length=1, description="Budget category for the budgeted leg.")
    amount_minor: int = Field(gt=0, description="Positive amount in minor units to move.")
    transaction_date: date = Field(description="Date the transfer occurred.")
    memo: Optional[str] = Field(default=None, description="Optional comment for both legs.")
    concept_id: Optional[UUID] = Field(default=None, description="Optional shared concept identifier.")


AccountClass = Literal["cash", "credit", "investment", "accessible", "loan", "tangible"]
AccountRole = Literal["on_budget", "tracking"]


class AccountState(BaseModel):
    """Account balances surfaced to the SPA."""

    account_id: str
    name: str
    account_type: Literal["asset", "liability"]
    account_class: AccountClass
    account_role: AccountRole
    current_balance_minor: int


class CategoryState(BaseModel):
    """Budget category state for the active month."""

    category_id: str
    name: str
    available_minor: int
    activity_minor: int = Field(default=0, description="Month-to-date activity in minor units.")


class TransactionResponse(BaseModel):
    """Response payload after inserting a transaction."""

    transaction_version_id: UUID
    concept_id: UUID
    amount_minor: int
    transaction_date: date
    memo: Optional[str]
    account: AccountState
    category: CategoryState


class ReferenceDataResponse(BaseModel):
    """Reference data shape for dropdowns."""

    accounts: list[AccountState]
    categories: list[CategoryState]


class TransactionListItem(BaseModel):
    """Serialized transaction row for spreadsheet UI."""

    transaction_version_id: UUID
    concept_id: UUID
    transaction_date: date
    account_id: str
    account_name: str
    category_id: str
    category_name: str
    amount_minor: int
    memo: Optional[str]
    recorded_at: datetime


class NetWorthDelta(BaseModel):
    """Placeholder for future response objects that include net worth changes."""

    net_worth_minor: int
    net_worth_decimal: Decimal


class CategorizedTransferLeg(BaseModel):
    """Details for a single leg of a categorized transfer."""

    transaction_version_id: UUID
    account: AccountState


class CategorizedTransferResponse(BaseModel):
    """Response payload that captures the results of a transfer."""

    concept_id: UUID
    budget_leg: CategorizedTransferLeg
    transfer_leg: CategorizedTransferLeg
    category: CategoryState


class ReadyToAssignResponse(BaseModel):
    """Surface Ready to Assign (RTA) for a given month."""

    month_start: date
    ready_to_assign_minor: int
    ready_to_assign_decimal: Decimal


SLUG_PATTERN = r"^[a-z0-9_]+$"


class AccountCommand(BaseModel):
    """Shared fields for account create/update operations with class metadata."""

    name: str = Field(min_length=1, max_length=120)
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
    currency: str = Field(default="USD", min_length=3, max_length=3)
    opened_on: Optional[date] = Field(default=None, description="Optional account open date.")
    is_active: bool = Field(default=True, description="Marks whether the account can be used for new transactions.")


class AccountCreateRequest(AccountCommand):
    """Payload for creating a new account."""

    account_id: str = Field(pattern=SLUG_PATTERN, description="Stable identifier for the account.")


class AccountUpdateRequest(AccountCommand):
    """Payload for editing an existing account."""


class AccountDetail(AccountCommand):
    """Serialized account data for the admin UI."""

    account_id: str
    created_at: datetime
    updated_at: datetime


class BudgetCategoryCommand(BaseModel):
    """Shared fields for budget category mutations."""

    name: str = Field(min_length=1, max_length=120)
    is_active: bool = Field(default=True)


class BudgetCategoryCreateRequest(BudgetCategoryCommand):
    """Payload for creating a budget category."""

    category_id: str = Field(pattern=SLUG_PATTERN, description="Stable identifier for the category.")


class BudgetCategoryUpdateRequest(BudgetCategoryCommand):
    """Payload for editing a budget category."""


class BudgetCategoryDetail(BudgetCategoryCommand):
    """Serialized budget category data for the admin UI."""

    category_id: str
    created_at: datetime
    updated_at: datetime
