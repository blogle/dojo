"""Core API schemas."""

from datetime import date as Date
from decimal import Decimal

from pydantic import BaseModel, Field


class NetWorthResponse(BaseModel):
    """
    Serialized net worth snapshot for API responses.

    This schema defines the structure for returning consolidated net worth data
    through the API, including both minor unit integer values and a decimal
    representation for display.

    Attributes
    ----------
    assets_minor : int
        Sum of active asset account balances in minor units (e.g., cents).
    liabilities_minor : int
        Sum of active liability account balances in minor units.
    positions_minor : int
        Sum of active investment position market values in minor units.
    tangibles_minor : int
        Sum of active tangible asset valuations in minor units.
    net_worth_minor : int
        Calculated net worth in minor units (assets - liabilities + positions + tangibles).
    net_worth_decimal : Decimal
        The net worth expressed in whole units as a Decimal, suitable for display.
    """

    assets_minor: int = Field(description="Sum of active asset account balances.")
    liabilities_minor: int = Field(description="Sum of active liability account balances.")
    positions_minor: int = Field(description="Sum of active position market values.")
    tangibles_minor: int = Field(description="Sum of active tangible valuations.")
    net_worth_minor: int = Field(description="Assets - liabilities + positions (minor units).")
    net_worth_decimal: Decimal = Field(description="Net worth expressed in whole units (Decimal).")


class NetWorthHistoryPoint(BaseModel):
    """One point in the net worth time series."""

    date: Date = Field(description="Point date (YYYY-MM-DD).")
    value_minor: int = Field(description="Net worth at date (minor units).")
