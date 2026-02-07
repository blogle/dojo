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

from dojo.aspire_migration.net_worth_parity import Mark, _aspire_signed_amount, _loads_json_list, _month_end, _month_iter
from dojo.aspire_migration.net_worth_parity import _pick_session_id


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonthValues:
    month_end: date
    aspire_total_minor: int
    hybrid_total_minor: int


def _month_start(me: date) -> date:
    return date(me.year, me.month, 1)


def _prev_month_end(me: date) -> date:
    if me.month == 1:
        prev = date(me.year - 1, 12, 1)
    else:
        prev = date(me.year, me.month - 1, 1)
    last = calendar.monthrange(prev.year, prev.month)[1]
    return date(prev.year, prev.month, last)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compute a hybrid net worth series: use Aspire marks for tracking categories, but use ledger-derived "
            "balances for mapped duplicate categories (e.g. Checking/Credit Cards)."
        )
    )
    parser.add_argument("--database", type=str, required=True, help="Path to DuckDB (e.g. data/ledger.duckdb)")
    parser.add_argument("--session", default=None, help="Migration session id (defaults to latest completed)")
    parser.add_argument(
        "--mapping-json",
        type=str,
        required=True,
        help="JSON mapping: { 'Checking': '💰 Checking', 'Reserve Card': '💳 Reserve Card', ... }",
    )
    parser.add_argument(
        "--replacement-date",
        default="mark-date",
        choices=("mark-date", "month-end"),
        help=(
            "When substituting a mapped category with the ledger balance, use the ledger balance as-of the net worth mark date "
            "(Aspire-parity) or as-of the month end boundary."
        ),
    )
    parser.add_argument(
        "--emit-series",
        action="store_true",
        help="Emit the full per-month series (sensitive).",
    )
    parser.add_argument("--out", type=str, default=None, help="Optional path to write full JSON output")
    parser.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    mapping = json.loads(Path(args.mapping_json).read_text(encoding="utf-8"))
    if not isinstance(mapping, dict):
        raise SystemExit("--mapping-json must be a JSON object")
    mapping = {str(k): str(v) for k, v in mapping.items()}

    conn = duckdb.connect(args.database, read_only=True)
    try:
        session_id = _pick_session_id(conn, args.session)

        row = conn.execute(
            """
            SELECT net_worth_assets_json, net_worth_categories_json
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

        if not marks:
            raise SystemExit("No net worth marks found in staging")

        # Aspire bucket semantics: per category, within a month bucket there may be multiple marks, but in your dataset it's 0/1.
        marks_by_category_month: dict[str, dict[date, int]] = defaultdict(lambda: defaultdict(int))
        mark_date_by_category_month: dict[str, dict[date, date]] = defaultdict(dict)
        for m in marks:
            me = _month_end(m.snapshot_date)
            marks_by_category_month[m.category_name][me] += _aspire_signed_amount(
                category=m.category_name,
                amount_minor=m.amount_minor,
                net_worth_assets=net_worth_assets,
            )
            # Keep the latest mark date within the bucket (if multiple entries exist).
            existing = mark_date_by_category_month[m.category_name].get(me)
            if existing is None or m.snapshot_date > existing:
                mark_date_by_category_month[m.category_name][me] = m.snapshot_date

        # Load transactions for mapped accounts.
        needed_accounts = sorted(set(mapping.values()))
        trx_rows = conn.execute(
            """
            SELECT transaction_date, account_name, amount_minor
            FROM aspire_staging_transactions
            WHERE migration_session_id = $id
              AND transaction_date IS NOT NULL
              AND account_name IN (SELECT UNNEST($accounts))
            ORDER BY account_name, transaction_date, row_index
            """,
            {"id": session_id, "accounts": needed_accounts},
        ).fetchall()
        flows_by_account: dict[str, list[tuple[date, int]]] = defaultdict(list)
        for d, a, amt in trx_rows:
            if isinstance(d, date):
                flows_by_account[str(a)].append((d, int(amt or 0)))

        start_me = _month_end(min(m.snapshot_date for m in marks))
        end_me = _month_end(max(m.snapshot_date for m in marks))
        month_ends = _month_iter(start_me, end_me)

        # Running balance pointers per account.
        balances: dict[str, int] = {a: 0 for a in needed_accounts}
        idxs: dict[str, int] = {a: 0 for a in needed_accounts}

        def ledger_balance_asof(acc: str, asof: date) -> int:
            arr = flows_by_account.get(acc) or []
            idx = idxs[acc]
            bal = balances[acc]
            while idx < len(arr) and arr[idx][0] <= asof:
                bal += arr[idx][1]
                idx += 1
            balances[acc] = bal
            idxs[acc] = idx
            return bal

        values: list[MonthValues] = []
        for me in month_ends:
            aspire_total = 0
            hybrid_total = 0
            for cat in configured_categories:
                aspire_value = marks_by_category_month.get(cat, {}).get(me, 0)
                aspire_total += aspire_value

                if cat in mapping:
                    acc = mapping[cat]
                    if args.replacement_date == "month-end":
                        bal = ledger_balance_asof(acc, me)
                    else:
                        mark_date = mark_date_by_category_month.get(cat, {}).get(me)
                        if mark_date is None:
                            # Aspire would contribute 0 for this bucket. Hybrid chooses the same.
                            bal = 0
                        else:
                            bal = ledger_balance_asof(acc, mark_date)
                    hybrid_total += bal
                else:
                    hybrid_total += aspire_value

            values.append(MonthValues(month_end=me, aspire_total_minor=aspire_total, hybrid_total_minor=hybrid_total))

        diffs = [abs(v.hybrid_total_minor - v.aspire_total_minor) for v in values]
        payload: dict[str, Any] = {
            "migration_session_id": session_id,
            "replacement_date": args.replacement_date,
            "window": {"start_month_end": start_me.isoformat(), "end_month_end": end_me.isoformat()},
            "mapped_categories": mapping,
            "summary": {
                "months": len(values),
                "diff_abs_max_minor": max(diffs) if diffs else 0,
                "diff_abs_p50_minor": sorted(diffs)[len(diffs) // 2] if diffs else 0,
            },
        }
        if args.emit_series:
            payload["series"] = [
                {
                    "month_end": v.month_end.isoformat(),
                    "aspire_total_minor": v.aspire_total_minor,
                    "hybrid_total_minor": v.hybrid_total_minor,
                    "diff_minor": v.hybrid_total_minor - v.aspire_total_minor,
                }
                for v in values
            ]

        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        print(json.dumps({"migration_session_id": session_id, **payload["summary"]}, indent=2, sort_keys=True))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
