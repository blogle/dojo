from __future__ import annotations

import argparse
import calendar
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

import duckdb


logger = logging.getLogger(__name__)


_LEADING_SYMBOLS_RE = re.compile(r"^[^a-zA-Z0-9]+")
_NON_ALNUM_SPACE_RE = re.compile(r"[^a-zA-Z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def _normalize_label(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = _LEADING_SYMBOLS_RE.sub("", s)
    s = _NON_ALNUM_SPACE_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


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


@dataclass(frozen=True)
class Mark:
    snapshot_date: date
    category_name: str
    amount_minor: int


def _aspire_signed_amount(*, category: str, amount_minor: int, net_worth_assets: set[str]) -> int:
    return amount_minor if category in net_worth_assets else -amount_minor


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return float(min(values))
    if p >= 1:
        return float(max(values))
    xs = sorted(values)
    idx = int(round((len(xs) - 1) * p))
    return float(xs[idx])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Aspire net worth marks to ledger-derived balances for candidate duplicate accounts. "
            "This helps map net worth categories (e.g. 'Checking') to transaction accounts (e.g. '💰 Checking')."
        )
    )
    parser.add_argument("--database", type=Path, required=True, help="Path to DuckDB (e.g. data/ledger.duckdb)")
    parser.add_argument("--session", default=None, help="Migration session id (defaults to latest completed)")
    parser.add_argument(
        "--mapping-json",
        type=Path,
        default=None,
        help=(
            "Optional explicit mapping JSON: {\"Checking\": \"💰 Checking\", ...}. "
            "If omitted, uses normalized-name heuristics when unambiguous."
        ),
    )
    parser.add_argument(
        "--emit-samples",
        action="store_true",
        help="Emit a few (date, mark, ledger, diff) samples per mapped pair (sensitive).",
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional path to write full JSON output")
    parser.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    explicit_mapping: dict[str, str] = {}
    if args.mapping_json:
        explicit_mapping = json.loads(args.mapping_json.read_text(encoding="utf-8"))
        if not isinstance(explicit_mapping, dict):
            raise SystemExit("--mapping-json must be a JSON object")
        explicit_mapping = {str(k): str(v) for k, v in explicit_mapping.items()}

    conn = duckdb.connect(str(args.database), read_only=True)
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
        net_worth_categories = _loads_json_list(categories_json)

        trx_accounts = [
            str(r[0])
            for r in conn.execute(
                """
                SELECT DISTINCT account_name
                FROM aspire_staging_transactions
                WHERE migration_session_id = $id
                  AND account_name IS NOT NULL
                  AND TRIM(account_name) != ''
                ORDER BY account_name
                """,
                {"id": session_id},
            ).fetchall()
        ]

        # Build normalized index.
        trx_by_norm: dict[str, list[str]] = defaultdict(list)
        for a in trx_accounts:
            trx_by_norm[_normalize_label(a)].append(a)

        nw_by_norm: dict[str, list[str]] = defaultdict(list)
        for c in net_worth_categories:
            nw_by_norm[_normalize_label(c)].append(c)

        # Candidate mappings.
        mappings: dict[str, str] = {}
        for nw in net_worth_categories:
            if nw in explicit_mapping:
                mappings[nw] = explicit_mapping[nw]
                continue
            norm = _normalize_label(nw)
            candidates = trx_by_norm.get(norm) or []
            if len(candidates) == 1:
                mappings[nw] = candidates[0]

        # Only keep those that actually overlap.
        mappings = {k: v for k, v in mappings.items() if _normalize_label(k) in trx_by_norm}

        # Load all marks for mapped net worth categories.
        if not mappings:
            payload = {
                "migration_session_id": session_id,
                "note": "No duplicate candidates found (or mapping ambiguous).",
                "trx_accounts": len(trx_accounts),
                "net_worth_categories": len(net_worth_categories),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        marks_by_category: dict[str, list[Mark]] = defaultdict(list)
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
        for d, cat, amt in mark_rows:
            if not isinstance(d, date):
                continue
            c = str(cat).strip()
            if c in mappings:
                marks_by_category[c].append(Mark(snapshot_date=d, category_name=c, amount_minor=int(amt or 0)))

        # Preload transactions for any mapped trx account to compute as-of balances.
        needed_trx_accounts = sorted(set(mappings.values()))
        trx_rows = conn.execute(
            """
            SELECT transaction_date, account_name, amount_minor
            FROM aspire_staging_transactions
            WHERE migration_session_id = $id
              AND transaction_date IS NOT NULL
              AND account_name IN (SELECT UNNEST($accounts))
            ORDER BY account_name, transaction_date, row_index
            """,
            {"id": session_id, "accounts": needed_trx_accounts},
        ).fetchall()

        trx_by_account: dict[str, list[tuple[date, int]]] = defaultdict(list)
        for d, a, amt in trx_rows:
            if isinstance(d, date):
                trx_by_account[str(a)].append((d, int(amt or 0)))

        # Compute drift stats.
        results: list[dict[str, Any]] = []
        for nw_cat, trx_acc in sorted(mappings.items()):
            marks = sorted(marks_by_category.get(nw_cat) or [], key=lambda m: m.snapshot_date)
            flows = sorted(trx_by_account.get(trx_acc) or [], key=lambda t: t[0])

            ledger_start = flows[0][0] if flows else None

            # Pointer scan for as-of balances.
            balance = 0
            idx = 0
            diffs: list[int] = []
            abs_diffs: list[float] = []
            samples: list[dict[str, Any]] = []
            skipped_pre_ledger = 0
            for m in marks:
                if ledger_start is not None and m.snapshot_date < ledger_start:
                    skipped_pre_ledger += 1
                    continue
                while idx < len(flows) and flows[idx][0] <= m.snapshot_date:
                    balance += flows[idx][1]
                    idx += 1

                signed_mark = _aspire_signed_amount(
                    category=m.category_name,
                    amount_minor=m.amount_minor,
                    net_worth_assets=net_worth_assets,
                )
                diff = signed_mark - balance
                diffs.append(diff)
                abs_diffs.append(abs(diff))

                if args.emit_samples and len(samples) < 5:
                    samples.append(
                        {
                            "date": m.snapshot_date.isoformat(),
                            "mark_minor": signed_mark,
                            "ledger_balance_minor": balance,
                            "diff_minor": diff,
                            "month_end": _month_end(m.snapshot_date).isoformat(),
                        }
                    )

            results.append(
                {
                    "net_worth_category": nw_cat,
                    "transaction_account": trx_acc,
                    "marks": len(marks),
                    "marks_used": len(diffs),
                    "marks_skipped_pre_ledger": skipped_pre_ledger,
                    "ledger_start_date": ledger_start.isoformat() if ledger_start else None,
                    "diff_abs_mean_minor": int(round(mean(abs_diffs))) if abs_diffs else 0,
                    "diff_abs_p50_minor": int(_percentile(abs_diffs, 0.50)) if abs_diffs else 0,
                    "diff_abs_p90_minor": int(_percentile(abs_diffs, 0.90)) if abs_diffs else 0,
                    "diff_abs_max_minor": int(max(abs_diffs)) if abs_diffs else 0,
                    "samples": samples,
                }
            )

        payload = {
            "migration_session_id": session_id,
            "mappings": mappings,
            "results": results,
            "notes": {
                "interpretation": (
                    "diff = signed_mark - ledger_balance(as-of mark date). "
                    "Large diffs can mean the mark was recorded mid-month, the ledger is missing a starting balance, "
                    "or the net worth category is not truly the same real-world account."
                )
            },
        }

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # Print a concise summary.
        print(
            json.dumps(
                {
                    "migration_session_id": session_id,
                    "mapped_pairs": len(mappings),
                    "pairs": [
                        {
                            "net_worth_category": r["net_worth_category"],
                            "transaction_account": r["transaction_account"],
                            "marks": r["marks"],
                            "marks_used": r["marks_used"],
                            "ledger_start_date": r["ledger_start_date"],
                            "diff_abs_p50_minor": r["diff_abs_p50_minor"],
                            "diff_abs_p90_minor": r["diff_abs_p90_minor"],
                            "diff_abs_max_minor": r["diff_abs_max_minor"],
                        }
                        for r in results
                    ],
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
