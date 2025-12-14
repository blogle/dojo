"""Integration tests for month-boundary behavior."""

from __future__ import annotations

from datetime import date

import duckdb
from fastapi.testclient import TestClient

from tests.integration.helpers import (  # type: ignore[import]
    FEBRUARY_2025,
    JANUARY_2025,
    allocate_from_rta,
    category_state,
    create_account,
    create_category,
    fund_ready_to_assign,
    ready_to_assign,
)

JANUARY = JANUARY_2025
FEBRUARY = FEBRUARY_2025
JANUARY_TRANSACTION_DATE = date(2025, 1, 10)


def test_month_flip_carries_available_and_resets_activity(
    api_client: TestClient, pristine_db: duckdb.DuckDBPyConnection
) -> None:
    """Spec 6.1 — the category rollover logic preserves availability while clearing budgeted/activity."""

    cash_account = "month_boundary_cash"
    create_account(
        api_client,
        account_id=cash_account,
        account_type="asset",
        account_class="cash",
        account_role="on_budget",
    )
    create_category(api_client, category_id="rollover_buffer", name="Buffer")

    # January income fills Ready-to-Assign, then the envelope consumes it.
    fund_ready_to_assign(
        api_client,
        account_id=cash_account,
        amount_minor=120_000,
        txn_date=JANUARY_TRANSACTION_DATE,
    )
    allocate_from_rta(
        api_client,
        category_id="rollover_buffer",
        amount_minor=120_000,
        month_start=JANUARY,
    )

    january_state = category_state(api_client, category_id="rollover_buffer", month_start=JANUARY)
    assert january_state["available_minor"] == 120_000
    assert january_state["allocated_minor"] == 120_000
    assert january_state["activity_minor"] == 0

    # Query the next month to trigger rollover.
    february_state = category_state(api_client, category_id="rollover_buffer", month_start=FEBRUARY)
    assert february_state["available_minor"] == 120_000
    assert february_state["allocated_minor"] == 0
    assert february_state["activity_minor"] == 0

    # Ready-to-Assign does not change as part of the flip.
    assert ready_to_assign(api_client, JANUARY) == 0
    assert ready_to_assign(api_client, FEBRUARY) == 0

    row = pristine_db.execute(
        """
        SELECT allocated_minor, activity_minor, available_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        ["rollover_buffer", FEBRUARY],
    ).fetchone()
    assert row == (0, 0, 120_000)
