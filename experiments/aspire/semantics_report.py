from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable


def _sha8(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def redact_label(value: str) -> str:
    # Keep length as a useful signal but avoid leaking user-defined names.
    return f"label:{_sha8(value)}(len={len(value)})"


_LEADING_SYMBOLS_RE = re.compile(r"^[^a-zA-Z0-9]+")
_NON_ALNUM_SPACE_RE = re.compile(r"[^a-zA-Z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def normalize_label(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = _LEADING_SYMBOLS_RE.sub("", s)
    s = _NON_ALNUM_SPACE_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def safe_labels(labels: Iterable[str], *, show_names: bool) -> list[str]:
    out: list[str] = []
    for name in labels:
        out.append(name if show_names else redact_label(name))
    return out


@dataclass(frozen=True)
class NetWorthMarkStats:
    categories_total: int
    categories_with_any_marks: int
    marks_total: int
    marks_with_missing_date: int
    marks_with_missing_category: int
    distinct_months_total: int
    marks_on_month_end: int
    marks_within_last_2_days_of_month: int
    max_marks_in_one_month_for_any_category: int
    buckets_with_multiple_marks: int


@dataclass(frozen=True)
class SemanticsInputs:
    dataset_fingerprint: str | None
    transactions_count: int
    transactions_date_min: str | None
    transactions_date_max: str | None
    allocations_count: int
    allocations_date_min: str | None
    allocations_date_max: str | None
    net_worth_marks_count: int
    net_worth_date_min: str | None
    net_worth_date_max: str | None

    trx_accounts: set[str]
    trx_categories: set[str]
    cfg_accounts: set[str]
    cfg_cards: set[str]
    budget_categories: set[str]
    net_worth_assets: set[str]
    net_worth_debts: set[str]
    net_worth_categories: set[str]

    # (snapshot_date, category_name)
    net_worth_marks: list[tuple[date | None, str | None]]


def _month_key(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def _is_month_end(d: date) -> bool:
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    return (next_month.toordinal() - d.toordinal()) == 1


def _days_to_month_end(d: date) -> int:
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    return (next_month.toordinal() - 1) - d.toordinal()


def build_semantics_report(*, inputs: SemanticsInputs, show_names: bool) -> dict[str, Any]:
    nw_categories = inputs.net_worth_categories
    nw_mark_categories = set(m[1] for m in inputs.net_worth_marks if m[1] and str(m[1]).strip())

    def _norm_set(values: Iterable[str]) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for v in values:
            out[normalize_label(v)].add(v)
        return out

    norm_trx_accounts = _norm_set(inputs.trx_accounts)
    norm_cfg_accounts = _norm_set(inputs.cfg_accounts)
    norm_cfg_cards = _norm_set(inputs.cfg_cards)
    norm_nw_categories = _norm_set(nw_categories)
    norm_budget_categories = _norm_set(inputs.budget_categories)
    norm_trx_categories = _norm_set(inputs.trx_categories)

    exact_overlap_with_trx_accounts = sorted(nw_categories & inputs.trx_accounts)
    exact_overlap_with_cfg_accounts = sorted(nw_categories & inputs.cfg_accounts)
    exact_overlap_with_cfg_cards = sorted(nw_categories & inputs.cfg_cards)

    def _normalized_overlap(a: dict[str, set[str]], b: dict[str, set[str]]) -> list[tuple[str, int, int]]:
        hits: list[tuple[str, int, int]] = []
        for k in sorted(set(a.keys()) & set(b.keys())):
            if not k:
                continue
            hits.append((k, len(a[k]), len(b[k])))
        return hits

    norm_overlap_trx_accounts = _normalized_overlap(norm_nw_categories, norm_trx_accounts)
    norm_overlap_budget_categories = _normalized_overlap(norm_nw_categories, norm_budget_categories)
    norm_overlap_trx_categories = _normalized_overlap(norm_nw_categories, norm_trx_categories)

    def _overlap_details(
        *,
        left: dict[str, set[str]],
        right: dict[str, set[str]],
        keys: list[tuple[str, int, int]],
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for k, _lc, _rc in keys[:limit]:
            l_vals = sorted(left.get(k, set()))
            r_vals = sorted(right.get(k, set()))
            out.append(
                {
                    "normalized": k if show_names else redact_label(k),
                    "left_variants": safe_labels(l_vals[:10], show_names=show_names),
                    "right_variants": safe_labels(r_vals[:10], show_names=show_names),
                    "left_variant_count": len(l_vals),
                    "right_variant_count": len(r_vals),
                }
            )
        return out

    marks_by_category_month: dict[str, Counter[tuple[int, int]]] = defaultdict(Counter)
    marks_by_category_total: Counter[str] = Counter()
    marks_by_category_month_end_like: Counter[str] = Counter()
    marks_missing_date = 0
    marks_missing_category = 0
    marks_total = 0
    marks_on_month_end = 0
    marks_within_2d = 0
    for snapshot_date, category_name in inputs.net_worth_marks:
        marks_total += 1
        if snapshot_date is None:
            marks_missing_date += 1
            continue
        if not category_name:
            marks_missing_category += 1
            continue

        marks_by_category_total[str(category_name)] += 1

        mk = _month_key(snapshot_date)
        marks_by_category_month[category_name][mk] += 1
        if _is_month_end(snapshot_date):
            marks_on_month_end += 1
        if _days_to_month_end(snapshot_date) <= 2:
            marks_within_2d += 1
            marks_by_category_month_end_like[str(category_name)] += 1

    distinct_months_total = len({mk for c in marks_by_category_month.values() for mk in c.keys()})
    buckets_with_multiple = sum(1 for c in marks_by_category_month.values() for _mk, n in c.items() if n > 1)
    max_marks_in_one_bucket = max((max(c.values()) for c in marks_by_category_month.values() if c), default=0)

    mark_stats = NetWorthMarkStats(
        categories_total=len(nw_categories),
        categories_with_any_marks=len(marks_by_category_month),
        marks_total=marks_total,
        marks_with_missing_date=marks_missing_date,
        marks_with_missing_category=marks_missing_category,
        distinct_months_total=distinct_months_total,
        marks_on_month_end=marks_on_month_end,
        marks_within_last_2_days_of_month=marks_within_2d,
        max_marks_in_one_month_for_any_category=max_marks_in_one_bucket,
        buckets_with_multiple_marks=buckets_with_multiple,
    )

    coverage: list[dict[str, Any]] = []
    for category, ctr in marks_by_category_month.items():
        months_with_marks = len(ctr)
        if not ctr:
            continue
        first = min(ctr.keys())
        last = max(ctr.keys())
        span = (last[0] - first[0]) * 12 + (last[1] - first[1]) + 1
        coverage.append(
            {
                "category": category if show_names else redact_label(category),
                "months_with_marks": months_with_marks,
                "month_span": span,
                "coverage_ratio": (months_with_marks / span) if span > 0 else 0.0,
                "max_marks_in_a_month": max(ctr.values()) if ctr else 0,
            }
        )
    coverage.sort(key=lambda r: (r["coverage_ratio"], -r["month_span"], -r["months_with_marks"]))

    heuristic = {
        "duplicate_of_trx_account_exact": len(exact_overlap_with_trx_accounts),
        "duplicate_of_cfg_account_exact": len(exact_overlap_with_cfg_accounts),
        "duplicate_of_cfg_card_exact": len(exact_overlap_with_cfg_cards),
        "also_budget_category_normalized": len(norm_overlap_budget_categories),
        "appears_in_trx_categories_normalized": len(norm_overlap_trx_categories),
    }

    # Per-category compact view (drives onboarding heuristics and validates assumptions).
    norm_trx_account_keys = set(norm_trx_accounts.keys())
    norm_budget_category_keys = set(norm_budget_categories.keys())
    category_rows: list[dict[str, Any]] = []
    for cat in sorted(nw_categories):
        norm = normalize_label(cat)
        ctr = marks_by_category_month.get(cat) or Counter()
        months_with_marks = len(ctr)
        marks_for_cat = int(marks_by_category_total.get(cat, 0))
        first = min(ctr.keys()) if ctr else None
        last = max(ctr.keys()) if ctr else None
        span = ((last[0] - first[0]) * 12 + (last[1] - first[1]) + 1) if (first and last) else 0

        kind = "asset" if cat in inputs.net_worth_assets else ("debt" if cat in inputs.net_worth_debts else "unknown")
        category_rows.append(
            {
                "category": cat if show_names else redact_label(cat),
                "kind": kind,
                "marks_total": marks_for_cat,
                "marks_month_end_like": int(marks_by_category_month_end_like.get(cat, 0)),
                "months_with_marks": months_with_marks,
                "month_span": span,
                "coverage_ratio": (months_with_marks / span) if span > 0 else 0.0,
                "month_end_like_ratio": (
                    (float(marks_by_category_month_end_like.get(cat, 0)) / float(marks_for_cat))
                    if marks_for_cat > 0
                    else 0.0
                ),
                "normalized": norm if show_names else redact_label(norm),
                "normalized_overlaps": {
                    "trx_account": norm in norm_trx_account_keys,
                    "budget_category": norm in norm_budget_category_keys,
                },
            }
        )

    # Most relevant first: duplicates and sparse categories.
    category_rows.sort(
        key=lambda r: (
            not (r["normalized_overlaps"]["trx_account"] or r["normalized_overlaps"]["budget_category"]),
            r["coverage_ratio"],
            -r["month_span"],
        )
    )

    return {
        "dataset": {
            "dataset_fingerprint": inputs.dataset_fingerprint,
            "transactions": {
                "count": inputs.transactions_count,
                "date_min": inputs.transactions_date_min,
                "date_max": inputs.transactions_date_max,
            },
            "allocations": {
                "count": inputs.allocations_count,
                "date_min": inputs.allocations_date_min,
                "date_max": inputs.allocations_date_max,
            },
            "net_worth_marks": {
                "count": inputs.net_worth_marks_count,
                "date_min": inputs.net_worth_date_min,
                "date_max": inputs.net_worth_date_max,
            },
        },
        "universes": {
            "trx_accounts": len(inputs.trx_accounts),
            "trx_categories": len(inputs.trx_categories),
            "cfg_accounts": len(inputs.cfg_accounts),
            "cfg_cards": len(inputs.cfg_cards),
            "budget_categories": len(inputs.budget_categories),
            "net_worth_assets": len(inputs.net_worth_assets),
            "net_worth_debts": len(inputs.net_worth_debts),
            "net_worth_categories": len(inputs.net_worth_categories),
        },
        "overlaps": {
            "net_worth_vs_trx_accounts_exact": {
                "count": len(exact_overlap_with_trx_accounts),
                "examples": safe_labels(exact_overlap_with_trx_accounts[:20], show_names=show_names),
            },
            "net_worth_vs_cfg_accounts_exact": {
                "count": len(exact_overlap_with_cfg_accounts),
                "examples": safe_labels(exact_overlap_with_cfg_accounts[:20], show_names=show_names),
            },
            "net_worth_vs_cfg_cards_exact": {
                "count": len(exact_overlap_with_cfg_cards),
                "examples": safe_labels(exact_overlap_with_cfg_cards[:20], show_names=show_names),
            },
            "net_worth_vs_trx_accounts_normalized": {
                "count": len(norm_overlap_trx_accounts),
                "normalized_keys": [
                    (k if show_names else redact_label(k)) for (k, _a, _b) in norm_overlap_trx_accounts[:50]
                ],
                "details": _overlap_details(
                    left=norm_nw_categories,
                    right=norm_trx_accounts,
                    keys=norm_overlap_trx_accounts,
                ),
            },
            "net_worth_vs_budget_categories_normalized": {
                "count": len(norm_overlap_budget_categories),
                "normalized_keys": [
                    (k if show_names else redact_label(k)) for (k, _a, _b) in norm_overlap_budget_categories[:50]
                ],
                "details": _overlap_details(
                    left=norm_nw_categories,
                    right=norm_budget_categories,
                    keys=norm_overlap_budget_categories,
                ),
            },
        },
        "net_worth_mark_stats": mark_stats.__dict__,
        "net_worth_category_mismatches": {
            "marks_not_in_config_count": len(nw_mark_categories - nw_categories),
            "marks_not_in_config_examples": safe_labels(
                sorted(nw_mark_categories - nw_categories)[:20],
                show_names=show_names,
            ),
            "config_not_in_marks_count": len(nw_categories - nw_mark_categories),
            "config_not_in_marks_examples": safe_labels(
                sorted(nw_categories - nw_mark_categories)[:20],
                show_names=show_names,
            ),
        },
        "net_worth_category_coverage_sample": {
            "most_sparse": coverage[:25],
            "least_sparse": list(reversed(coverage[-10:])),
        },
        "net_worth_categories_compact": {
            "count": len(category_rows),
            "top": category_rows[:30],
        },
        "heuristic_sizing": heuristic,
    }
