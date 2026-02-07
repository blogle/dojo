from __future__ import annotations

import argparse
import calendar
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb


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


def _month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _month_iter(start_month: date, end_month: date) -> list[date]:
    # Both inputs are interpreted as month end boundaries.
    start = date(start_month.year, start_month.month, 1)
    end = date(end_month.year, end_month.month, 1)
    out: list[date] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(_month_end(date(y, m, 1)))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return out


@dataclass(frozen=True)
class Mark:
    snapshot_date: date
    category_name: str
    amount_minor: int


def _aspire_signed_amount(
    *,
    category: str,
    amount_minor: int,
    net_worth_assets: set[str],
) -> int:
    # Aspire semantics: treat amounts as magnitude; sign is + if category is in NetWorthAssets else -.
    return amount_minor if category in net_worth_assets else -amount_minor


def compute_month_bucket_series(
    *,
    marks: list[Mark],
    configured_categories: list[str],
    net_worth_assets: set[str],
    start_month_end: date,
    end_month_end: date,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    marks_by_category_month: dict[str, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    for m in marks:
        month_end = _month_end(m.snapshot_date)
        signed = _aspire_signed_amount(category=m.category_name, amount_minor=m.amount_minor, net_worth_assets=net_worth_assets)
        marks_by_category_month[m.category_name][month_end] += signed

    month_ends = _month_iter(start_month_end, end_month_end)
    series: list[dict[str, Any]] = []
    for me in month_ends:
        total = 0
        for cat in configured_categories:
            total += marks_by_category_month.get(cat, {}).get(me, 0)
        series.append({"month_end": me.isoformat(), "net_worth_minor": total})

    meta = {
        "months": len(month_ends),
        "configured_categories": len(configured_categories),
        "marks": len(marks),
    }
    return series, meta


def compute_carry_forward_series(
    *,
    marks: list[Mark],
    configured_categories: list[str],
    net_worth_assets: set[str],
    start_month_end: date,
    end_month_end: date,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # As-of reinterpretation: value at a month end is the most recent mark <= month end.
    marks_sorted = sorted(marks, key=lambda m: (m.category_name, m.snapshot_date))

    marks_by_category: dict[str, list[Mark]] = defaultdict(list)
    for m in marks_sorted:
        marks_by_category[m.category_name].append(m)

    month_ends = _month_iter(start_month_end, end_month_end)
    series: list[dict[str, Any]] = []
    # Per-category pointer scan.
    pointers: dict[str, int] = {cat: 0 for cat in configured_categories}
    last_value: dict[str, int] = {cat: 0 for cat in configured_categories}

    for me in month_ends:
        total = 0
        for cat in configured_categories:
            arr = marks_by_category.get(cat) or []
            idx = pointers.get(cat, 0)
            while idx < len(arr) and arr[idx].snapshot_date <= me:
                last_value[cat] = _aspire_signed_amount(
                    category=arr[idx].category_name,
                    amount_minor=arr[idx].amount_minor,
                    net_worth_assets=net_worth_assets,
                )
                idx += 1
            pointers[cat] = idx
            total += last_value[cat]
        series.append({"month_end": me.isoformat(), "net_worth_minor": total})

    meta = {
        "months": len(month_ends),
        "configured_categories": len(configured_categories),
        "marks": len(marks),
    }
    return series, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compute Aspire-parity net worth history from extracted ntw_* marks. "
            "Outputs both Aspire month-bucket semantics and an optional carry-forward as-of reinterpretation."
        )
    )
    parser.add_argument("--database", type=Path, required=True, help="Path to DuckDB (e.g. data/ledger.duckdb)")
    parser.add_argument("--session", default=None, help="Migration session id (defaults to latest completed)")
    parser.add_argument(
        "--mode",
        default="bucket",
        choices=("bucket", "carry-forward"),
        help="Net worth aggregation semantics",
    )
    parser.add_argument(
        "--include-non-configured",
        action="store_true",
        help="Include marks for categories not present in NetWorthCategories (not Aspire-parity, but useful for forensics).",
    )
    parser.add_argument(
        "--emit-series",
        action="store_true",
        help="Include the per-month time series in output (can be sensitive).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write full JSON output.",
    )
    parser.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    conn = duckdb.connect(str(args.database), read_only=True)
    try:
        session_id = _pick_session_id(conn, args.session)

        row = conn.execute(
            """
            SELECT
                net_worth_assets_json,
                net_worth_categories_json
            FROM aspire_migration_sessions
            WHERE migration_session_id = $id
            """,
            {"id": session_id},
        ).fetchone()
        if row is None:
            raise SystemExit(f"Missing migration session: {session_id}")
        assets_json, categories_json = row

        net_worth_assets = set(_loads_json_list(assets_json))
        configured_categories = _loads_json_list(categories_json)

        mark_rows = conn.execute(
            """
            SELECT snapshot_date, category_name, amount_minor
            FROM aspire_staging_net_worth_snapshots
            WHERE migration_session_id = $id
              AND snapshot_date IS NOT NULL
              AND category_name IS NOT NULL
              AND TRIM(category_name) != ''
            """,
            {"id": session_id},
        ).fetchall()

        marks: list[Mark] = []
        for d, cat, amt in mark_rows:
            if not isinstance(d, date):
                continue
            name = str(cat).strip()
            if not name:
                continue
            marks.append(Mark(snapshot_date=d, category_name=name, amount_minor=int(amt or 0)))

        mark_categories = {m.category_name for m in marks}
        if args.include_non_configured:
            categories = sorted(mark_categories | set(configured_categories))
        else:
            categories = list(configured_categories)

        if not marks:
            payload = {
                "migration_session_id": session_id,
                "mode": args.mode,
                "marks": 0,
                "configured_categories": len(configured_categories),
                "note": "No net worth marks present.",
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        start = _month_end(min(m.snapshot_date for m in marks))
        end = _month_end(max(m.snapshot_date for m in marks))

        if args.mode == "bucket":
            series, meta = compute_month_bucket_series(
                marks=marks,
                configured_categories=categories,
                net_worth_assets=net_worth_assets,
                start_month_end=start,
                end_month_end=end,
            )
        else:
            series, meta = compute_carry_forward_series(
                marks=marks,
                configured_categories=categories,
                net_worth_assets=net_worth_assets,
                start_month_end=start,
                end_month_end=end,
            )

        payload: dict[str, Any] = {
            "migration_session_id": session_id,
            "mode": args.mode,
            "window": {"start_month_end": start.isoformat(), "end_month_end": end.isoformat()},
            "meta": meta,
            "mismatches": {
                "marks_not_in_configured_categories": sorted(mark_categories - set(configured_categories)),
                "configured_categories_missing_marks": sorted(set(configured_categories) - mark_categories),
            },
        }
        if args.emit_series:
            payload["series"] = series

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # Print a small summary by default.
        print(
            json.dumps(
                {
                    "migration_session_id": session_id,
                    "mode": args.mode,
                    "start_month_end": start.isoformat(),
                    "end_month_end": end.isoformat(),
                    "months": meta["months"],
                    "configured_categories": meta["configured_categories"],
                    "marks": meta["marks"],
                    "marks_not_in_config_count": len(mark_categories - set(configured_categories)),
                    "config_missing_marks_count": len(set(configured_categories) - mark_categories),
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
