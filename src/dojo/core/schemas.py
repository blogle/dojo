"""Core API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class NetWorthResponse(BaseModel):
    """Serialized net worth snapshot for API responses."""

    assets_minor: int = Field(description="Sum of active asset account balances.")
    liabilities_minor: int = Field(description="Sum of active liability account balances.")
    positions_minor: int = Field(description="Sum of active position market values.")
    tangibles_minor: int = Field(description="Sum of active tangible valuations.")
    net_worth_minor: int = Field(description="Assets - liabilities + positions (minor units).")
    net_worth_decimal: Decimal = Field(description="Net worth expressed in whole units (Decimal).")
