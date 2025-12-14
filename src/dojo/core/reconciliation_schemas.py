"""Pydantic schemas for the reconciliation API."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReconciliationCreateRequest(BaseModel):
    """Payload to create a reconciliation checkpoint."""

    statement_date: date = Field(description="Bank statement 'as of' date.")
    statement_balance_minor: int = Field(description="Statement ending balance in minor units.")


class ReconciliationResponse(BaseModel):
    """Serialized reconciliation checkpoint."""

    reconciliation_id: UUID
    account_id: str
    created_at: datetime
    statement_date: date
    statement_balance_minor: int
    previous_reconciliation_id: UUID | None
