"""Pydantic models for the investments domain."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Money fields are integer minor units (e.g., cents).
# Quantity is float to allow fractional shares (see docs/plans/investment-tracking.md).

SecurityType = Literal["STOCK", "ETF", "MUTUAL_FUND", "CRYPTO", "INDEX"]


class CreatePositionRequest(BaseModel):
    """Incoming position payload for portfolio reconciliation."""

    ticker: str = Field(min_length=1, description="Ticker symbol (will be normalized to uppercase).")
    quantity: float = Field(gt=0, description="Number of shares/units (fractional allowed).")
    avg_cost_minor: int = Field(ge=0, description="Per-share average cost basis in minor units.")


class ReconcilePortfolioRequest(BaseModel):
    """Incoming payload representing the full desired portfolio state."""

    uninvested_cash_minor: int = Field(ge=0, description="Brokerage cash / buying power in minor units.")
    positions: list[CreatePositionRequest] = Field(default_factory=list)


class Security(BaseModel):
    security_id: UUID
    ticker: str
    name: str | None = None
    type: SecurityType = "STOCK"
    currency: str = "USD"


class Position(BaseModel):
    """Raw SCD2 row representation for a position."""

    position_id: UUID
    concept_id: UUID
    account_id: str
    security_id: UUID
    quantity: float
    avg_cost_minor: int
    valid_from: datetime
    valid_to: datetime
    is_active: bool
    recorded_at: datetime


class PositionView(BaseModel):
    """Enriched position view: includes latest price and derived values."""

    security_id: UUID
    ticker: str
    name: str | None = None
    quantity: float
    avg_cost_minor: int
    price_minor: int | None = None
    market_value_minor: int
    gain_minor: int | None = None


class PortfolioState(BaseModel):
    """Current portfolio snapshot for an investment account."""

    account_id: str
    ledger_cash_minor: int
    uninvested_cash_minor: int
    holdings_value_minor: int
    nav_minor: int
    total_return_minor: int
    total_return_pct: float | None = None
    positions: list[PositionView] = Field(default_factory=list)


class PortfolioHistoryPoint(BaseModel):
    """Single daily point used for charting."""

    market_date: date
    nav_minor: int
    cash_flow_minor: int
    return_minor: int
