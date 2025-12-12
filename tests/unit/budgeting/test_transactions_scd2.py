"""Unit tests for Domain 2 SCD-2 ledger specifications."""

from __future__ import annotations

from datetime import date, datetime
from importlib import resources
from pathlib import Path
import threading
from typing import Callable

import duckdb
import pytest

from dojo.budgeting.schemas import NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _category_available(conn: duckdb.DuckDBPyConnection, category_id: str, month: date) -> int:
    row = conn.execute(
        """
        SELECT available_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        [category_id, month],
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _category_activity(conn: duckdb.DuckDBPyConnection, category_id: str, month: date) -> int:
    row = conn.execute(
        """
        SELECT activity_minor
        FROM budget_category_monthly_state
        WHERE category_id = ? AND month_start = ?
        """,
        [category_id, month],
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _account_balance(conn: duckdb.DuckDBPyConnection, account_id: str) -> int:
    row = conn.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = ?",
        [account_id],
    ).fetchone()
    assert row is not None
    return int(row[0])


def _prepare_disk_database(tmp_path: Path) -> Path:
    db_path = tmp_path / "ledger.duckdb"
    conn = duckdb.connect(database=str(db_path))
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    apply_base_budgeting_fixture(conn)
    conn.close()
    return db_path


def _run_in_thread(fn: Callable[[], None]) -> threading.Thread:
    thread = threading.Thread(target=fn)
    thread.start()
    return thread


def test_correction_flow_preserves_history_and_balances(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """Spec 2.1: Editing a transaction preserves prior versions and net deltas."""
    service = TransactionEntryService()
    txn_date = date(2025, 1, 10)
    month = _month_start(txn_date)

    created = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=txn_date,
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-5_000,
            memo="initial grocery spend",
        ),
    )

    ready_before = service.ready_to_assign(in_memory_db, month)
    updated = service.create(
        in_memory_db,
        NewTransactionRequest(
            concept_id=created.concept_id,
            transaction_date=txn_date,
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-6_000,
            memo="correction",
        ),
    )
    ready_after = service.ready_to_assign(in_memory_db, month)

    rows = in_memory_db.execute(
        "SELECT is_active, amount_minor FROM transactions WHERE concept_id = ?",
        [str(created.concept_id)],
    ).fetchall()
    assert len(rows) == 2
    assert sum(1 for row in rows if row[0]) == 1
    assert _account_balance(in_memory_db, "house_checking") == 500_000 - 6_000
    assert _category_available(in_memory_db, "groceries", month) == -6_000
    assert ready_before == ready_after
    assert updated.account.current_balance_minor == 500_000 - 6_000


def test_void_transaction_restores_account_and_category_state(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """Spec 2.2: Voiding a transaction reverses balances without deleting history."""
    service = TransactionEntryService()
    txn_date = date(2025, 1, 11)
    month = _month_start(txn_date)

    created = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=txn_date,
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-10_000,
            memo="purchase to void",
        ),
    )

    service.delete_transaction(in_memory_db, created.concept_id)

    counts = in_memory_db.execute(
        """
        SELECT SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
        FROM transactions
        WHERE concept_id = ?
        """,
        [str(created.concept_id)],
    ).fetchone()
    assert counts is not None and counts[0] == 0
    assert _account_balance(in_memory_db, "house_checking") == 500_000
    assert _category_available(in_memory_db, "groceries", month) == 0


def test_concurrent_edits_result_in_single_active_version(tmp_path: Path) -> None:
    """Spec 2.3: Concurrent edits keep one active version and deterministic balances."""
    db_path = _prepare_disk_database(tmp_path)
    conn = duckdb.connect(database=str(db_path))
    service = TransactionEntryService()
    txn_date = date(2025, 1, 12)
    initial = service.create(
        conn,
        NewTransactionRequest(
            transaction_date=txn_date,
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-5_000,
            memo="baseline",
        ),
    )
    concept_id = initial.concept_id
    conn.close()

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def make_edit(amount_minor: int) -> None:
        worker_conn: duckdb.DuckDBPyConnection | None = None
        try:
            worker_conn = duckdb.connect(database=str(db_path))
            worker_service = TransactionEntryService()
            barrier.wait()
            worker_service.create(
                worker_conn,
                NewTransactionRequest(
                    concept_id=concept_id,
                    transaction_date=txn_date,
                    account_id="house_checking",
                    category_id="groceries",
                    amount_minor=amount_minor,
                    memo=f"edit {amount_minor}",
                ),
            )
        except Exception as exc:  # pragma: no cover - surfaced via assertion
            errors.append(exc)
        finally:
            if worker_conn is not None:
                worker_conn.close()

    threads = [_run_in_thread(lambda amt=amount: make_edit(amt)) for amount in (-7_000, -9_000)]
    for thread in threads:
        thread.join()

    assert len(errors) <= 1, f"expected at most a single conflict, saw {errors!r}"
    if errors:
        assert "Conflict on update" in str(errors[0])

    with duckdb.connect(database=str(db_path)) as verify_conn:
        totals_row = verify_conn.execute(
            """
            SELECT COUNT(*) AS version_count,
                   SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
            FROM transactions
            WHERE concept_id = ?
            """,
            [str(concept_id)],
        ).fetchone()
        assert totals_row is not None
        version_count, active_rows = totals_row
        assert version_count >= 2
        assert active_rows == 1
        latest_row = verify_conn.execute(
            "SELECT amount_minor FROM transactions WHERE concept_id = ? AND is_active = TRUE",
            [str(concept_id)],
        ).fetchone()
        assert latest_row is not None
        latest_amount = int(latest_row[0])
        assert latest_amount in (-7_000, -9_000)
        assert _account_balance(verify_conn, "house_checking") == 500_000 + latest_amount


def test_backdated_insertion_records_historical_activity(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """Spec 2.6: Backdated inserts capture historical activity with later recorded_at."""
    service = TransactionEntryService()
    current_date = date(2025, 5, 5)
    older_date = date(2025, 3, 10)
    older_month = _month_start(older_date)

    # Prime the ledger with a current-month transaction to mimic live usage.
    first_response = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=current_date,
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-2_000,
            memo="recent spend",
        ),
    )

    first_row = in_memory_db.execute(
        "SELECT recorded_at FROM transactions WHERE transaction_version_id = ?",
        [str(first_response.transaction_version_id)],
    ).fetchone()
    assert first_row is not None
    first_recorded_at = first_row[0]

    before_activity = _category_activity(in_memory_db, "groceries", older_month)

    response = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=older_date,
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-1_500,
            memo="backdated receipt",
        ),
    )

    after_activity = _category_activity(in_memory_db, "groceries", older_month)
    assert after_activity == before_activity + 1_500

    timestamps = in_memory_db.execute(
        """
        SELECT transaction_date, recorded_at FROM transactions WHERE transaction_version_id = ?
        """,
        [str(response.transaction_version_id)],
    ).fetchone()
    assert timestamps is not None
    recorded_at = timestamps[1]
    recorded_on = timestamps[0]
    assert recorded_on == older_date
    assert recorded_at > first_recorded_at


def test_reconciliation_adjustment_behaves_like_rta_inflow(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """Spec 2.8: Adjustment transactions move balances and feed Ready to Assign."""
    service = TransactionEntryService()
    txn_date = date(2025, 1, 20)
    month = _month_start(txn_date)
    baseline_balance = _account_balance(in_memory_db, "house_checking")
    baseline_rta = service.ready_to_assign(in_memory_db, month)

    delta = 500
    service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=txn_date,
            account_id="house_checking",
            category_id="available_to_budget",
            amount_minor=delta,
            memo="reconciliation adjustment",
        ),
    )

    assert _account_balance(in_memory_db, "house_checking") == baseline_balance + delta
    assert service.ready_to_assign(in_memory_db, month) == baseline_rta + delta
