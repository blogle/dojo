from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import duckdb

from dojo.aspire.semantics_report import SemanticsInputs, build_semantics_report


logger = logging.getLogger(__name__)


def _loads_json_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    text = str(raw)
    if not text.strip():
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[str] = []
    for item in parsed:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _pick_session_id(conn: duckdb.DuckDBPyConnection, preferred: str | None) -> str:
    if preferred:
        row = conn.execute(
            "SELECT 1 FROM aspire_migration_sessions WHERE migration_session_id = $id",
            {"id": preferred},
        ).fetchone()
        if row is None:
            raise SystemExit(f"Unknown migration session id: {preferred}")
        return preferred

    row = conn.execute(
        """
        SELECT migration_session_id
        FROM aspire_migration_sessions
        WHERE extraction_status = 'completed'
        ORDER BY extracted_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None or row[0] is None:
        raise SystemExit("No completed Aspire extraction session found in this database")
    return str(row[0])


def build_inputs_from_staging(
    *,
    conn: duckdb.DuckDBPyConnection,
    migration_session_id: str,
) -> SemanticsInputs:
    session = conn.execute(
        """
        SELECT
            dataset_fingerprint,
            cfg_accounts_json,
            cfg_cards_json,
            categories_minus_credit_cards_json,
            net_worth_assets_json,
            net_worth_debts_json,
            net_worth_categories_json
        FROM aspire_migration_sessions
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone()
    if session is None:
        raise SystemExit(f"Missing migration session: {migration_session_id}")

    (
        dataset_fingerprint,
        cfg_accounts_json,
        cfg_cards_json,
        categories_minus_credit_cards_json,
        net_worth_assets_json,
        net_worth_debts_json,
        net_worth_categories_json,
    ) = session

    cfg_accounts = set(_loads_json_list(cfg_accounts_json))
    cfg_cards = set(_loads_json_list(cfg_cards_json))
    budget_categories = set(_loads_json_list(categories_minus_credit_cards_json))
    net_worth_assets = set(_loads_json_list(net_worth_assets_json))
    net_worth_debts = set(_loads_json_list(net_worth_debts_json))
    net_worth_categories = set(_loads_json_list(net_worth_categories_json))

    trx_meta = conn.execute(
        """
        SELECT
            COUNT(*) AS n,
            MIN(transaction_date) AS dmin,
            MAX(transaction_date) AS dmax
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone() or (0, None, None)
    trx_count, trx_min, trx_max = trx_meta

    alloc_meta = conn.execute(
        """
        SELECT
            COUNT(*) AS n,
            MIN(allocation_date) AS dmin,
            MAX(allocation_date) AS dmax
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone() or (0, None, None)
    alloc_count, alloc_min, alloc_max = alloc_meta

    nw_meta = conn.execute(
        """
        SELECT
            COUNT(*) AS n,
            MIN(snapshot_date) AS dmin,
            MAX(snapshot_date) AS dmax
        FROM aspire_staging_net_worth_snapshots
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone() or (0, None, None)
    nw_count, nw_min, nw_max = nw_meta

    trx_accounts = {
        str(r[0])
        for r in conn.execute(
            """
            SELECT DISTINCT account_name
            FROM aspire_staging_transactions
            WHERE migration_session_id = $id AND account_name IS NOT NULL AND TRIM(account_name) != ''
            """,
            {"id": migration_session_id},
        ).fetchall()
    }
    trx_categories = {
        str(r[0])
        for r in conn.execute(
            """
            SELECT DISTINCT category_name
            FROM aspire_staging_transactions
            WHERE migration_session_id = $id AND category_name IS NOT NULL AND TRIM(category_name) != ''
            """,
            {"id": migration_session_id},
        ).fetchall()
    }

    nw_marks = [
        (row[0], str(row[1]) if row[1] is not None and str(row[1]).strip() else None)
        for row in conn.execute(
            """
            SELECT snapshot_date, category_name
            FROM aspire_staging_net_worth_snapshots
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id},
        ).fetchall()
    ]

    return SemanticsInputs(
        dataset_fingerprint=str(dataset_fingerprint) if dataset_fingerprint is not None else None,
        transactions_count=int(trx_count or 0),
        transactions_date_min=trx_min.isoformat() if trx_min else None,
        transactions_date_max=trx_max.isoformat() if trx_max else None,
        allocations_count=int(alloc_count or 0),
        allocations_date_min=alloc_min.isoformat() if alloc_min else None,
        allocations_date_max=alloc_max.isoformat() if alloc_max else None,
        net_worth_marks_count=int(nw_count or 0),
        net_worth_date_min=nw_min.isoformat() if nw_min else None,
        net_worth_date_max=nw_max.isoformat() if nw_max else None,
        trx_accounts=trx_accounts,
        trx_categories=trx_categories,
        cfg_accounts=cfg_accounts,
        cfg_cards=cfg_cards,
        budget_categories=budget_categories,
        net_worth_assets=net_worth_assets,
        net_worth_debts=net_worth_debts,
        net_worth_categories=net_worth_categories,
        net_worth_marks=nw_marks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze Aspire staging tables in a Dojo DuckDB and emit a privacy-safe semantics report. "
            "This does not require Google OAuth."
        )
    )
    parser.add_argument("--database", type=Path, required=True, help="Path to DuckDB (e.g. data/ledger.duckdb)")
    parser.add_argument("--session", default=None, help="Migration session id (defaults to latest completed)")
    parser.add_argument(
        "--show-names",
        action="store_true",
        help="Include user-defined labels in output (otherwise redacted).",
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional path to write full JSON report")
    parser.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    conn = duckdb.connect(str(args.database), read_only=True)
    try:
        session_id = _pick_session_id(conn, args.session)
        inputs = build_inputs_from_staging(conn=conn, migration_session_id=session_id)
        report = build_semantics_report(inputs=inputs, show_names=bool(args.show_names))

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        overlaps = report["overlaps"]
        marks = report["net_worth_mark_stats"]
        print(
            json.dumps(
                {
                    "migration_session_id": session_id,
                    "dataset_fingerprint": report["dataset"]["dataset_fingerprint"],
                    "universes": report["universes"],
                    "overlaps": {
                        "nw_vs_trx_accounts_exact": overlaps["net_worth_vs_trx_accounts_exact"]["count"],
                        "nw_vs_budget_categories_normalized": overlaps["net_worth_vs_budget_categories_normalized"][
                            "count"
                        ],
                    },
                    "net_worth_marks": {
                        "marks_total": marks["marks_total"],
                        "categories_with_any_marks": marks["categories_with_any_marks"],
                        "distinct_months_total": marks["distinct_months_total"],
                        "buckets_with_multiple_marks": marks["buckets_with_multiple_marks"],
                        "marks_on_month_end": marks["marks_on_month_end"],
                        "marks_within_last_2_days_of_month": marks["marks_within_last_2_days_of_month"],
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
