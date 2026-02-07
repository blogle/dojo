"""Aspire dataset extraction.

This module converts a set of Aspire named ranges into normalized rows and a
privacy-safe summary (counts + date ranges + fingerprint).

Important: Do not log extracted values.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from dojo.aspire.gsheets_client import GoogleSheetsClient


class AspireExtractionError(RuntimeError):
    pass


_GOOGLE_SHEETS_EPOCH = date(1899, 12, 30)


def _serial_to_date(value: Any) -> date:
    """Convert a Google Sheets serial number to a date."""

    # Most commonly, value is a float or int.
    if isinstance(value, (int, float)):
        days = int(value)
        return _GOOGLE_SHEETS_EPOCH + timedelta(days=days)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise AspireExtractionError("Empty date")

        # If it looks like a number, treat it as a serial.
        try:
            as_float = float(raw)
        except ValueError:
            as_float = None
        if as_float is not None:
            days = int(as_float)
            return _GOOGLE_SHEETS_EPOCH + timedelta(days=days)

        # Fall back to ISO-ish formats.
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue

    raise AspireExtractionError("Unrecognized date value")


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    return str(value).strip() or None


def _money_to_minor(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str) and not value.strip():
        return 0

    try:
        dec = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise AspireExtractionError("Invalid money amount") from exc

    return int(dec.scaleb(2))


def _column(values: list[list[Any]] | None) -> list[Any]:
    if not values:
        return []
    out: list[Any] = []
    for row in values:
        if not row:
            out.append(None)
        else:
            out.append(row[0])
    return out


def _date_range(dates: list[date]) -> tuple[str | None, str | None]:
    if not dates:
        return (None, None)
    return (min(dates).isoformat(), max(dates).isoformat())


@dataclass(frozen=True)
class ExtractedAspireDataset:
    dataset_fingerprint: str

    transactions_count: int
    transactions_date_min: str | None
    transactions_date_max: str | None

    allocations_count: int
    allocations_date_min: str | None
    allocations_date_max: str | None

    net_worth_snapshots_count: int
    net_worth_date_min: str | None
    net_worth_date_max: str | None


@dataclass(frozen=True)
class AspireStagingTransactionRow:
    row_index: int
    transaction_date: date | None
    outflow_minor: int
    inflow_minor: int
    amount_minor: int
    category_name: str | None
    account_name: str | None
    memo: str | None
    status: str | None


@dataclass(frozen=True)
class AspireStagingAllocationRow:
    row_index: int
    allocation_date: date | None
    amount_minor: int
    from_category_name: str | None
    to_category_name: str | None


@dataclass(frozen=True)
class AspireStagingNetWorthSnapshotRow:
    row_index: int
    snapshot_date: date | None
    amount_minor: int
    category_name: str | None
    note: str | None
    breakpoint: str | None


@dataclass(frozen=True)
class ExtractedAspireRows:
    dataset: ExtractedAspireDataset
    transactions: list[AspireStagingTransactionRow]
    allocations: list[AspireStagingAllocationRow]
    net_worth_snapshots: list[AspireStagingNetWorthSnapshotRow]

    # Configuration lists (names only). Useful for defaults like "retired" detection.
    cfg_accounts: list[str]
    cfg_cards: list[str]
    hidden_accounts: list[str]
    hidden_categories: list[str]

    # BackendData-derived lists for mapping and defaults.
    categories_minus_credit_cards: list[str]
    net_worth_assets: list[str]
    net_worth_debts: list[str]
    net_worth_categories: list[str]

    # Budget metadata (in minor units) keyed by category name.
    user_def_amounts_minor: dict[str, int]
    user_def_goals_minor: dict[str, int]

    # Aspire special labels (string values).
    special_labels: dict[str, str]


_REQUIRED_RANGES = [
    "trx_Dates",
    "trx_Outflows",
    "trx_Inflows",
    "trx_Categories",
    "trx_Accounts",
    "trx_Memos",
    "trx_Statuses",
    "cts_Dates",
    "cts_Amounts",
    "cts_FromCategories",
    "cts_ToCategories",
]

_OPTIONAL_RANGES = [
    "ntw_Dates",
    "ntw_Amounts",
    "ntw_Categories",
    "ntw_Notes",
    "ntw_Breakpoints",
    # Configuration
    "cfg_Accounts",
    "cfg_Cards",
    # BackendData derived lists
    "CategoriesMinusCreditCards",
    "UserDefCategories",
    "UserDefAmounts",
    "UserDefGoals",
    "NetWorthAssets",
    "NetWorthDebts",
    "NetWorthCategories",
    "HiddenAccounts",
    "HiddenCategories",
    # Special labels
    "v_AtoB",
    "v_AccountTransfer",
    "v_BalanceAdjustment",
    "v_StartingBalance",
    "v_Today",
]


def required_named_ranges() -> list[str]:
    return list(_REQUIRED_RANGES)


def extract_aspire_rows(
    client: GoogleSheetsClient,
    *,
    spreadsheet_id: str,
    available_named_ranges: set[str],
) -> ExtractedAspireRows:
    missing = [name for name in _REQUIRED_RANGES if name not in available_named_ranges]
    if missing:
        raise AspireExtractionError("Missing required Aspire named ranges")

    ranges = [name for name in _REQUIRED_RANGES if name in available_named_ranges]
    ranges += [name for name in _OPTIONAL_RANGES if name in available_named_ranges]

    payload = client.batch_get_values(
        spreadsheet_id=spreadsheet_id,
        ranges=ranges,
        value_render_option="UNFORMATTED_VALUE",
    )

    value_ranges = payload.get("valueRanges", []) or []
    if len(value_ranges) < len(ranges):
        raise AspireExtractionError("Missing value ranges in batch response")

    by_name: dict[str, list[Any]] = {}
    for idx, name in enumerate(ranges):
        vr = value_ranges[idx]
        by_name[name] = _column(vr.get("values"))

    def _names_from_range(range_name: str) -> list[str]:
        raw = by_name.get(range_name)
        if not raw:
            return []
        out: list[str] = []
        for cell in raw:
            name = _to_str(cell)
            if name is not None:
                out.append(name)
        return out

    cfg_accounts = _names_from_range("cfg_Accounts")
    cfg_cards = _names_from_range("cfg_Cards")
    hidden_accounts = _names_from_range("HiddenAccounts")
    hidden_categories = _names_from_range("HiddenCategories")

    categories_minus_credit_cards = _names_from_range("CategoriesMinusCreditCards")
    net_worth_assets = _names_from_range("NetWorthAssets")
    net_worth_debts = _names_from_range("NetWorthDebts")
    net_worth_categories = _names_from_range("NetWorthCategories")

    # User-defined budget metadata lists are aligned by index.
    user_def_amounts_minor: dict[str, int] = {}
    user_def_goals_minor: dict[str, int] = {}
    user_def_categories_raw = by_name.get("UserDefCategories") or []
    user_def_amounts_raw = by_name.get("UserDefAmounts") or []
    user_def_goals_raw = by_name.get("UserDefGoals") or []
    meta_n = max(len(user_def_categories_raw), len(user_def_amounts_raw), len(user_def_goals_raw))
    for i in range(meta_n):
        name_cell = user_def_categories_raw[i] if i < len(user_def_categories_raw) else None
        cat_name = _to_str(name_cell)
        if cat_name is None:
            continue

        amount_cell = user_def_amounts_raw[i] if i < len(user_def_amounts_raw) else None
        goal_cell = user_def_goals_raw[i] if i < len(user_def_goals_raw) else None

        # Treat invalid budgeting metadata as 0; goals are optional and should not
        # block extraction of the financial ledger.
        try:
            amount_minor = _money_to_minor(amount_cell)
        except AspireExtractionError:
            amount_minor = 0
        try:
            goal_minor = _money_to_minor(goal_cell)
        except AspireExtractionError:
            goal_minor = 0

        if amount_minor:
            user_def_amounts_minor[cat_name] = amount_minor
        if goal_minor:
            user_def_goals_minor[cat_name] = goal_minor

    def _scalar_str(range_name: str) -> str | None:
        raw = by_name.get(range_name)
        if not raw:
            return None
        for cell in raw:
            value = _to_str(cell)
            if value is not None:
                return value
        return None

    special_labels: dict[str, str] = {}
    for key in ("v_AtoB", "v_AccountTransfer", "v_StartingBalance", "v_BalanceAdjustment"):
        value = _scalar_str(key)
        if value is not None:
            special_labels[key] = value

    # v_Today is a date serial in Sheets; store it as ISO for downstream parity tools.
    today_raw = by_name.get("v_Today") or []
    for cell in today_raw:
        if cell in (None, ""):
            continue
        try:
            special_labels["v_Today"] = _serial_to_date(cell).isoformat()
        except AspireExtractionError:
            # Best effort; this should not block ledger extraction.
            pass
        break

    # Transactions
    dates_raw = by_name.get("trx_Dates", [])
    outflows_raw = by_name.get("trx_Outflows", [])
    inflows_raw = by_name.get("trx_Inflows", [])
    categories_raw = by_name.get("trx_Categories", [])
    accounts_raw = by_name.get("trx_Accounts", [])
    memos_raw = by_name.get("trx_Memos", [])
    statuses_raw = by_name.get("trx_Statuses", [])

    n = max(
        len(dates_raw),
        len(outflows_raw),
        len(inflows_raw),
        len(categories_raw),
        len(accounts_raw),
        len(memos_raw),
        len(statuses_raw),
    )

    transactions_for_hash: list[dict[str, Any]] = []
    transactions_rows: list[AspireStagingTransactionRow] = []
    transaction_dates: list[date] = []
    transaction_count = 0

    for i in range(n):
        date_cell = dates_raw[i] if i < len(dates_raw) else None
        outflow_cell = outflows_raw[i] if i < len(outflows_raw) else None
        inflow_cell = inflows_raw[i] if i < len(inflows_raw) else None
        category_cell = categories_raw[i] if i < len(categories_raw) else None
        account_cell = accounts_raw[i] if i < len(accounts_raw) else None
        memo_cell = memos_raw[i] if i < len(memos_raw) else None
        status_cell = statuses_raw[i] if i < len(statuses_raw) else None

        # Skip fully empty rows.
        if not any(
            v not in (None, "")
            for v in (
                date_cell,
                outflow_cell,
                inflow_cell,
                category_cell,
                account_cell,
                memo_cell,
                status_cell,
            )
        ):
            continue

        trx_date: date | None = None
        if date_cell not in (None, ""):
            trx_date = _serial_to_date(date_cell)
            transaction_dates.append(trx_date)

        out_minor = _money_to_minor(outflow_cell)
        in_minor = _money_to_minor(inflow_cell)
        if out_minor and in_minor:
            raise AspireExtractionError("Ambiguous transaction row (both inflow and outflow)")

        amount_minor = in_minor - out_minor

        transaction_count += 1

        category_name = _to_str(category_cell)
        account_name = _to_str(account_cell)
        memo = _to_str(memo_cell)
        status_text = _to_str(status_cell)

        transactions_for_hash.append(
            {
                "row": i,
                "date": trx_date.isoformat() if trx_date else None,
                "amount_minor": amount_minor,
                "category": category_name,
                "account": account_name,
                "memo": memo,
                "status": status_text,
            }
        )

        transactions_rows.append(
            AspireStagingTransactionRow(
                row_index=i,
                transaction_date=trx_date,
                outflow_minor=out_minor,
                inflow_minor=in_minor,
                amount_minor=amount_minor,
                category_name=category_name,
                account_name=account_name,
                memo=memo,
                status=status_text,
            )
        )

    trx_min, trx_max = _date_range(transaction_dates)

    # Allocations
    cts_dates_raw = by_name.get("cts_Dates", [])
    cts_amounts_raw = by_name.get("cts_Amounts", [])
    cts_from_raw = by_name.get("cts_FromCategories", [])
    cts_to_raw = by_name.get("cts_ToCategories", [])

    m = max(len(cts_dates_raw), len(cts_amounts_raw), len(cts_from_raw), len(cts_to_raw))
    allocations_for_hash: list[dict[str, Any]] = []
    allocations_rows: list[AspireStagingAllocationRow] = []
    allocation_dates: list[date] = []
    allocation_count = 0

    for i in range(m):
        date_cell = cts_dates_raw[i] if i < len(cts_dates_raw) else None
        amount_cell = cts_amounts_raw[i] if i < len(cts_amounts_raw) else None
        from_cell = cts_from_raw[i] if i < len(cts_from_raw) else None
        to_cell = cts_to_raw[i] if i < len(cts_to_raw) else None

        if not any(v not in (None, "") for v in (date_cell, amount_cell, from_cell, to_cell)):
            continue

        alloc_date: date | None = None
        if date_cell not in (None, ""):
            alloc_date = _serial_to_date(date_cell)
            allocation_dates.append(alloc_date)

        amount_minor = _money_to_minor(amount_cell)

        allocation_count += 1

        from_category_name = _to_str(from_cell)
        to_category_name = _to_str(to_cell)

        allocations_for_hash.append(
            {
                "row": i,
                "date": alloc_date.isoformat() if alloc_date else None,
                "amount_minor": amount_minor,
                "from": from_category_name,
                "to": to_category_name,
            }
        )

        allocations_rows.append(
            AspireStagingAllocationRow(
                row_index=i,
                allocation_date=alloc_date,
                amount_minor=amount_minor,
                from_category_name=from_category_name,
                to_category_name=to_category_name,
            )
        )

    alloc_min, alloc_max = _date_range(allocation_dates)

    # Net worth snapshots (optional)
    ntw_dates_raw = by_name.get("ntw_Dates")
    ntw_amounts_raw = by_name.get("ntw_Amounts")
    ntw_categories_raw = by_name.get("ntw_Categories")
    ntw_notes_raw = by_name.get("ntw_Notes")
    ntw_breakpoints_raw = by_name.get("ntw_Breakpoints")

    net_worth_for_hash: list[dict[str, Any]] = []
    net_worth_rows: list[AspireStagingNetWorthSnapshotRow] = []
    net_worth_dates: list[date] = []
    net_worth_count = 0

    if ntw_dates_raw is not None:
        k = max(
            len(ntw_dates_raw or []),
            len(ntw_amounts_raw or []),
            len(ntw_categories_raw or []),
            len(ntw_notes_raw or []),
            len(ntw_breakpoints_raw or []),
        )

        for i in range(k):
            date_cell = ntw_dates_raw[i] if ntw_dates_raw and i < len(ntw_dates_raw) else None
            amount_cell = ntw_amounts_raw[i] if ntw_amounts_raw and i < len(ntw_amounts_raw) else None
            category_cell = ntw_categories_raw[i] if ntw_categories_raw and i < len(ntw_categories_raw) else None
            note_cell = ntw_notes_raw[i] if ntw_notes_raw and i < len(ntw_notes_raw) else None
            breakpoint_cell = ntw_breakpoints_raw[i] if ntw_breakpoints_raw and i < len(ntw_breakpoints_raw) else None

            if not any(
                v not in (None, "") for v in (date_cell, amount_cell, category_cell, note_cell, breakpoint_cell)
            ):
                continue

            snap_date: date | None = None
            if date_cell not in (None, ""):
                snap_date = _serial_to_date(date_cell)
                net_worth_dates.append(snap_date)

            amount_minor = _money_to_minor(amount_cell)

            net_worth_count += 1

            category_name = _to_str(category_cell)
            note = _to_str(note_cell)
            breakpoint = _to_str(breakpoint_cell)

            net_worth_for_hash.append(
                {
                    "row": i,
                    "date": snap_date.isoformat() if snap_date else None,
                    "amount_minor": amount_minor,
                    "category": category_name,
                    "note": note,
                    "break": breakpoint,
                }
            )

            net_worth_rows.append(
                AspireStagingNetWorthSnapshotRow(
                    row_index=i,
                    snapshot_date=snap_date,
                    amount_minor=amount_minor,
                    category_name=category_name,
                    note=note,
                    breakpoint=breakpoint,
                )
            )

    ntw_min, ntw_max = _date_range(net_worth_dates)

    # Fingerprint: hash of canonical JSON for extracted rows (may include PII, but only in the hash).
    fingerprint_payload = {
        "transactions": transactions_for_hash,
        "allocations": allocations_for_hash,
        "net_worth": net_worth_for_hash,
        # Configuration-derived lists (names only).
        "cfg_accounts": cfg_accounts,
        "cfg_cards": cfg_cards,
        "hidden_accounts": hidden_accounts,
        "hidden_categories": hidden_categories,
        # BackendData-derived lists.
        "categories_minus_credit_cards": categories_minus_credit_cards,
        "net_worth_assets": net_worth_assets,
        "net_worth_debts": net_worth_debts,
        "net_worth_categories": net_worth_categories,
        "user_def_amounts_minor": user_def_amounts_minor,
        "user_def_goals_minor": user_def_goals_minor,
        "special_labels": special_labels,
    }
    blob = json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    dataset_fingerprint = hashlib.sha256(blob).hexdigest()

    dataset = ExtractedAspireDataset(
        dataset_fingerprint=dataset_fingerprint,
        transactions_count=transaction_count,
        transactions_date_min=trx_min,
        transactions_date_max=trx_max,
        allocations_count=allocation_count,
        allocations_date_min=alloc_min,
        allocations_date_max=alloc_max,
        net_worth_snapshots_count=net_worth_count,
        net_worth_date_min=ntw_min,
        net_worth_date_max=ntw_max,
    )

    return ExtractedAspireRows(
        dataset=dataset,
        transactions=transactions_rows,
        allocations=allocations_rows,
        net_worth_snapshots=net_worth_rows,
        cfg_accounts=cfg_accounts,
        cfg_cards=cfg_cards,
        hidden_accounts=hidden_accounts,
        hidden_categories=hidden_categories,
        categories_minus_credit_cards=categories_minus_credit_cards,
        net_worth_assets=net_worth_assets,
        net_worth_debts=net_worth_debts,
        net_worth_categories=net_worth_categories,
        user_def_amounts_minor=user_def_amounts_minor,
        user_def_goals_minor=user_def_goals_minor,
        special_labels=special_labels,
    )


def extract_aspire_dataset(
    client: GoogleSheetsClient,
    *,
    spreadsheet_id: str,
    available_named_ranges: set[str],
) -> ExtractedAspireDataset:
    """Compatibility wrapper that returns only the summary."""

    return extract_aspire_rows(
        client,
        spreadsheet_id=spreadsheet_id,
        available_named_ranges=available_named_ranges,
    ).dataset
