"""Pydantic schemas for budgeting APIs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
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


class AccountState(BaseModel):
    """Account balances surfaced to the SPA."""

    account_id: str
    name: str
    current_balance_minor: int


class CategoryState(BaseModel):
    """Budget category state for the active month."""

    category_id: str
    name: str
    available_minor: int


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
