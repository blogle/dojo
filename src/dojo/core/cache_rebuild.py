"""Utilities for rebuilding cached tables from authoritative ledger data."""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

import duckdb

from dojo.budgeting.services import derive_payment_category_id
from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection
from dojo.core.sql import load_sql

logger = logging.getLogger(__name__)


@cache
def _sql(name: str) -> str:
    return load_sql(name)


@dataclass
class _MonthAggregates:
    allocated: int = 0
    inflow: int = 0
    activity: int = 0


def rebuild_caches(
    conn: duckdb.DuckDBPyConnection,
    *,
    rebuild_accounts: bool = True,
    rebuild_categories: bool = True,
) -> None:
    """Recompute cache tables inside a single transaction."""

    conn.execute("BEGIN")
    try:
        if rebuild_accounts:
            _rebuild_account_balances(conn)
        if rebuild_categories:
            _rebuild_budget_category_month_state(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        logger.exception("cache rebuild failed; rolled back transaction")
        raise


def _rebuild_account_balances(conn: duckdb.DuckDBPyConnection) -> None:
    logger.info("rebuild accounts.current_balance_minor start")
    conn.execute(_sql("rebuild_accounts_current_balance.sql"))
    logger.info("rebuild accounts.current_balance_minor done")


def _existing_month_pairs(conn: duckdb.DuckDBPyConnection) -> set[tuple[str, date]]:
    rows: Iterable[tuple[str, date]] = conn.execute(
        "SELECT category_id, month_start FROM budget_category_monthly_state"
    ).fetchall()
    return set(rows)


def _load_category_flags(conn: duckdb.DuckDBPyConnection) -> dict[str, bool]:
    rows: Iterable[tuple[str, bool]] = conn.execute(
        "SELECT category_id, COALESCE(is_system, FALSE) AS is_system FROM budget_categories"
    ).fetchall()
    return {category_id: bool(is_system) for category_id, is_system in rows}


def _load_credit_accounts(conn: duckdb.DuckDBPyConnection) -> dict[str, bool]:
    rows: Iterable[tuple[str, str, str]] = conn.execute(
        "SELECT account_id, account_type, account_class FROM accounts"
    ).fetchall()
    return {
        account_id: (account_type == "liability" and account_class == "credit")
        for account_id, account_type, account_class in rows
    }


def _ensure_entry(
    aggregates: defaultdict[tuple[str, date], _MonthAggregates],
    month_index: defaultdict[str, set[date]],
    category_id: str,
    month_start: date,
) -> _MonthAggregates:
    month_index[category_id].add(month_start)
    return aggregates[(category_id, month_start)]


def _rebuild_budget_category_month_state(conn: duckdb.DuckDBPyConnection) -> None:
    logger.info("rebuild budget_category_monthly_state start")
    existing_pairs = _existing_month_pairs(conn)
    category_flags = _load_category_flags(conn)
    credit_accounts = _load_credit_accounts(conn)

    aggregates: defaultdict[tuple[str, date], _MonthAggregates] = defaultdict(_MonthAggregates)
    month_index: defaultdict[str, set[date]] = defaultdict(set)

    for category_id, month_start in existing_pairs:
        _ensure_entry(aggregates, month_index, category_id, month_start)

    # Check for is_active column existence to support running during migrations
    # where the column might not exist yet (e.g. before 0011_ensure_scd2_columns.sql)
    has_is_active = (
        conn.execute(
            "SELECT count(*) FROM pragma_table_info('budget_allocations') WHERE name = 'is_active'"
        ).fetchone()[0]
        > 0
    )

    sql = """
        SELECT month_start, from_category_id, to_category_id, amount_minor
        FROM budget_allocations
    """
    if has_is_active:
        sql += " WHERE COALESCE(is_active, TRUE) = TRUE"

    allocation_rows = conn.execute(sql).fetchall()
    for month_start, from_category_id, to_category_id, amount_minor in allocation_rows:
        amount = int(amount_minor)
        if to_category_id:
            entry = _ensure_entry(aggregates, month_index, to_category_id, month_start)
            entry.allocated += amount
        if from_category_id and from_category_id != "available_to_budget":
            entry = _ensure_entry(aggregates, month_index, from_category_id, month_start)
            entry.allocated -= amount

    transaction_rows = conn.execute(_sql("select_active_transactions_with_category_flags.sql")).fetchall()
    for account_id, category_id, transaction_date, amount_minor, is_system in transaction_rows:
        month_start = transaction_date.replace(day=1)
        amount = int(amount_minor)
        category_is_system = bool(is_system)
        if not category_is_system:
            entry = _ensure_entry(aggregates, month_index, category_id, month_start)
            entry.activity += -amount
        if not category_is_system and credit_accounts.get(account_id, False) and amount != 0:
            payment_category_id = derive_payment_category_id(account_id)
            if payment_category_id not in category_flags:
                logger.debug(
                    "skip credit reserve inflow for missing payment category",
                    extra={"payment_category_id": payment_category_id},
                )
                continue
            reserve_entry = _ensure_entry(aggregates, month_index, payment_category_id, month_start)
            delta = abs(amount)
            sign = 1 if amount < 0 else -1
            reserve_entry.inflow += sign * delta

    conn.execute("DELETE FROM budget_category_monthly_state")

    insert_rows: list[dict[str, int | str | date]] = []
    for category_id, months in month_index.items():
        running_available = 0
        for month_start in sorted(months):
            entry = aggregates[(category_id, month_start)]
            running_available += entry.allocated + entry.inflow - entry.activity
            insert_rows.append(
                {
                    "category_id": category_id,
                    "month_start": month_start,
                    "allocated_minor": entry.allocated,
                    "inflow_minor": entry.inflow,
                    "activity_minor": entry.activity,
                    "available_minor": running_available,
                }
            )

    if insert_rows:
        conn.executemany(
            _sql("insert_budget_category_monthly_state.sql"),
            insert_rows,
        )
    logger.info("rebuild budget_category_monthly_state done rows=%d", len(insert_rows))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild cache tables from the ledger")
    parser.add_argument("--database", "-d", help="Path to the DuckDB database file")
    parser.add_argument("--skip-accounts", action="store_true", help="Skip account balance rebuild")
    parser.add_argument(
        "--skip-budget",
        action="store_true",
        help="Skip budget category monthly state rebuild",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    args = _parse_args()
    settings: Settings = get_settings()
    db_path = Path(args.database) if args.database else settings.db_path
    with get_connection(db_path) as conn:
        rebuild_caches(
            conn,
            rebuild_accounts=not args.skip_accounts,
            rebuild_categories=not args.skip_budget,
        )


if __name__ == "__main__":
    main()
