"""Aspire dataset extraction from Google Sheets named ranges.

This module converts a set of Aspire named ranges into normalized rows and a
privacy-safe summary (counts + date ranges + fingerprint).

Important: never log extracted values.
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
    if isinstance(value, (int, float)):
        return _GOOGLE_SHEETS_EPOCH + timedelta(days=int(value))

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise AspireExtractionError("Empty date")

        try:
            as_float = float(raw)
        except ValueError:
            as_float = None
        if as_float is not None:
            return _GOOGLE_SHEETS_EPOCH + timedelta(days=int(as_float))

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
        out.append(row[0] if row else None)
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

    net_worth_marks_count: int
    net_worth_date_min: str | None
    net_worth_date_max: str | None


@dataclass(frozen=True)
class AspireStagingTransactionRow:
    row_index: int
    transaction_date: date | None
    amount_minor: int
    category_name: str | None
    account_name: str | None
    memo: str | None
    status_raw: str | None


@dataclass(frozen=True)
class AspireStagingAllocationRow:
    row_index: int
    allocation_date: date | None
    amount_minor: int
    from_category_name: str | None
    to_category_name: str | None


@dataclass(frozen=True)
class AspireStagingNetWorthMarkRow:
    row_index: int
    mark_date: date | None
    amount_minor: int
    category_name: str | None
    note: str | None
    breakpoint: str | None


@dataclass(frozen=True)
class ExtractedAspireRows:
    dataset: ExtractedAspireDataset
    transactions: list[AspireStagingTransactionRow]
    allocations: list[AspireStagingAllocationRow]
    net_worth_marks: list[AspireStagingNetWorthMarkRow]

    cfg_accounts: list[str]
    cfg_cards: list[str]
    hidden_accounts: list[str]
    hidden_categories: list[str]

    categories_minus_credit_cards: list[str]
    net_worth_assets: list[str]
    net_worth_debts: list[str]
    net_worth_categories: list[str]

    user_def_amounts_minor: dict[str, int]
    user_def_goals_minor: dict[str, int]

    category_type_symbols: dict[str, str]
    configuration_rows: list["AspireConfigurationRow"]
    dashboard_category_proxy: dict[str, "AspireDashboardCategoryProxy"]

    special_labels: dict[str, str]
    status_symbols: dict[str, str]


@dataclass(frozen=True)
class AspireConfigurationRow:
    row_type_symbol: str | None
    name: str | None
    monthly_target_minor: int
    due_date: date | None
    goal_amount_minor: int


@dataclass(frozen=True)
class AspireDashboardCategoryProxy:
    configured_budget_minor: int
    budgeted_minor: int
    activity_minor: int
    available_minor: int


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
    "r_ConfigurationData",
    # Special labels
    "v_AtoB",
    "v_AccountTransfer",
    "v_BalanceAdjustment",
    "v_StartingBalance",
    # Status symbols
    "v_ApprovedSymbol",
    "v_PendingSymbol",
    "v_BreakSymbol",
    # Category configuration marker symbols
    "v_CategoryGroupSymbol",
    "v_ReportableCategorySymbol",
    "v_NonReportableCategorySymbol",
    "v_DebtAccountSymbol",
]

_OPTIONAL_RANGES = [
    # Net worth marks
    "ntw_Dates",
    "ntw_Amounts",
    "ntw_Categories",
    "ntw_Notes",
    "ntw_Breakpoints",
    # Configuration
    "cfg_Accounts",
    "cfg_Cards",
    "HiddenAccounts",
    "HiddenCategories",
    "NetWorthAssets",
    "NetWorthDebts",
    "NetWorthCategories",
    "CategoriesMinusCreditCards",
    "UserDefCategories",
    "UserDefAmounts",
    "UserDefGoals",
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
    values_by_name: dict[str, list[list[Any]]] = {}
    for idx, name in enumerate(ranges):
        raw_values = (value_ranges[idx] or {}).get("values") or []
        values_by_name[name] = raw_values
        by_name[name] = _column(raw_values)

    # Best-effort Aspire proxy table (Dashboard category rows).
    dashboard_values: list[list[Any]] = []
    try:
        dashboard_payload = client.batch_get_values(
            spreadsheet_id=spreadsheet_id,
            ranges=["'Dashboard'!J6:R140"],
            value_render_option="UNFORMATTED_VALUE",
        )
        dashboard_ranges = dashboard_payload.get("valueRanges", []) or []
        if dashboard_ranges:
            dashboard_values = (dashboard_ranges[0] or {}).get("values") or []
    except Exception:
        dashboard_values = []

    def _names(range_name: str) -> list[str]:
        raw = by_name.get(range_name) or []
        out: list[str] = []
        for cell in raw:
            name = _to_str(cell)
            if name is not None:
                out.append(name)
        return out

    cfg_accounts = _names("cfg_Accounts")
    cfg_cards = _names("cfg_Cards")
    hidden_accounts = _names("HiddenAccounts")
    hidden_categories = _names("HiddenCategories")
    categories_minus_credit_cards = _names("CategoriesMinusCreditCards")
    net_worth_assets = _names("NetWorthAssets")
    net_worth_debts = _names("NetWorthDebts")
    net_worth_categories = _names("NetWorthCategories")

    user_def_amounts_minor: dict[str, int] = {}
    user_def_goals_minor: dict[str, int] = {}
    user_def_categories = by_name.get("UserDefCategories") or []
    user_def_amounts = by_name.get("UserDefAmounts") or []
    user_def_goals = by_name.get("UserDefGoals") or []
    meta_n = max(len(user_def_categories), len(user_def_amounts), len(user_def_goals))
    for i in range(meta_n):
        cat_name = _to_str(user_def_categories[i] if i < len(user_def_categories) else None)
        if cat_name is None:
            continue

        amount_cell = user_def_amounts[i] if i < len(user_def_amounts) else None
        goal_cell = user_def_goals[i] if i < len(user_def_goals) else None
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
        raw = by_name.get(range_name) or []
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

    today_raw = by_name.get("v_Today") or []
    for cell in today_raw:
        if cell in (None, ""):
            continue
        try:
            special_labels["v_Today"] = _serial_to_date(cell).isoformat()
        except AspireExtractionError:
            pass
        break

    status_symbols: dict[str, str] = {}
    for key in ("v_ApprovedSymbol", "v_PendingSymbol", "v_BreakSymbol"):
        value = _scalar_str(key)
        if value is not None:
            status_symbols[key] = value

    category_type_symbols: dict[str, str] = {}
    for key in (
        "v_CategoryGroupSymbol",
        "v_ReportableCategorySymbol",
        "v_NonReportableCategorySymbol",
        "v_DebtAccountSymbol",
    ):
        value = _scalar_str(key)
        if value is not None:
            category_type_symbols[key] = value

    # Budget configuration table (categories + groups + targets/goals).
    configuration_rows: list[AspireConfigurationRow] = []
    config_values = values_by_name.get("r_ConfigurationData") or []
    for raw_row in config_values:
        # Range is C:K => [type, name, .., target(G), due_date(H), .., goal(K)]
        row_type = _to_str(raw_row[0] if len(raw_row) > 0 else None)
        name = _to_str(raw_row[1] if len(raw_row) > 1 else None)
        target_cell = raw_row[4] if len(raw_row) > 4 else None
        due_cell = raw_row[5] if len(raw_row) > 5 else None
        goal_cell = raw_row[8] if len(raw_row) > 8 else None

        try:
            monthly_target_minor = _money_to_minor(target_cell)
        except AspireExtractionError:
            monthly_target_minor = 0
        try:
            goal_amount_minor = _money_to_minor(goal_cell)
        except AspireExtractionError:
            goal_amount_minor = 0

        due_date: date | None = None
        if due_cell not in (None, ""):
            try:
                due_date = _serial_to_date(due_cell)
            except AspireExtractionError:
                due_date = None

        if not any([row_type, name, monthly_target_minor, goal_amount_minor, due_date]):
            continue
        configuration_rows.append(
            AspireConfigurationRow(
                row_type_symbol=row_type,
                name=name,
                monthly_target_minor=monthly_target_minor,
                due_date=due_date,
                goal_amount_minor=goal_amount_minor,
            )
        )

    dashboard_category_proxy: dict[str, AspireDashboardCategoryProxy] = {}
    known_user_categories = {name for name in user_def_categories if _to_str(name)}
    for row in dashboard_values:
        if not row:
            continue
        category_name = _to_str(row[0] if len(row) > 0 else None)
        if not category_name:
            continue
        if known_user_categories and category_name not in known_user_categories:
            continue
        available_cell = row[2] if len(row) > 2 else None
        activity_cell = row[5] if len(row) > 5 else None
        configured_cell = row[6] if len(row) > 6 else None
        budgeted_cell = row[8] if len(row) > 8 else None
        try:
            available_minor = _money_to_minor(available_cell)
        except AspireExtractionError:
            available_minor = 0
        try:
            activity_minor = _money_to_minor(activity_cell)
        except AspireExtractionError:
            activity_minor = 0
        try:
            configured_minor = _money_to_minor(configured_cell)
        except AspireExtractionError:
            configured_minor = 0
        try:
            budgeted_minor = _money_to_minor(budgeted_cell)
        except AspireExtractionError:
            budgeted_minor = 0
        dashboard_category_proxy[category_name] = AspireDashboardCategoryProxy(
            configured_budget_minor=configured_minor,
            budgeted_minor=budgeted_minor,
            activity_minor=activity_minor,
            available_minor=available_minor,
        )

    # Transactions
    dates_raw = by_name.get("trx_Dates") or []
    outflows_raw = by_name.get("trx_Outflows") or []
    inflows_raw = by_name.get("trx_Inflows") or []
    categories_raw = by_name.get("trx_Categories") or []
    accounts_raw = by_name.get("trx_Accounts") or []
    memos_raw = by_name.get("trx_Memos") or []
    statuses_raw = by_name.get("trx_Statuses") or []

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
    transaction_rows: list[AspireStagingTransactionRow] = []
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

        if not any(
            v not in (None, "")
            for v in (date_cell, outflow_cell, inflow_cell, category_cell, account_cell, memo_cell, status_cell)
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
        status_raw = _to_str(status_cell)

        transactions_for_hash.append(
            {
                "row": i,
                "date": trx_date.isoformat() if trx_date else None,
                "amount_minor": amount_minor,
                "category": category_name,
                "account": account_name,
                "memo": memo,
                "status": status_raw,
            }
        )

        transaction_rows.append(
            AspireStagingTransactionRow(
                row_index=i,
                transaction_date=trx_date,
                amount_minor=amount_minor,
                category_name=category_name,
                account_name=account_name,
                memo=memo,
                status_raw=status_raw,
            )
        )

    trx_min, trx_max = _date_range(transaction_dates)

    # Allocations
    cts_dates_raw = by_name.get("cts_Dates") or []
    cts_amounts_raw = by_name.get("cts_Amounts") or []
    cts_from_raw = by_name.get("cts_FromCategories") or []
    cts_to_raw = by_name.get("cts_ToCategories") or []

    m = max(len(cts_dates_raw), len(cts_amounts_raw), len(cts_from_raw), len(cts_to_raw))
    allocations_for_hash: list[dict[str, Any]] = []
    allocation_rows: list[AspireStagingAllocationRow] = []
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

        from_name = _to_str(from_cell)
        to_name = _to_str(to_cell)

        allocations_for_hash.append(
            {
                "row": i,
                "date": alloc_date.isoformat() if alloc_date else None,
                "amount_minor": amount_minor,
                "from": from_name,
                "to": to_name,
            }
        )

        allocation_rows.append(
            AspireStagingAllocationRow(
                row_index=i,
                allocation_date=alloc_date,
                amount_minor=amount_minor,
                from_category_name=from_name,
                to_category_name=to_name,
            )
        )

    alloc_min, alloc_max = _date_range(allocation_dates)

    # Net worth marks (optional)
    ntw_dates_raw = by_name.get("ntw_Dates")
    ntw_amounts_raw = by_name.get("ntw_Amounts")
    ntw_categories_raw = by_name.get("ntw_Categories")
    ntw_notes_raw = by_name.get("ntw_Notes")
    ntw_breakpoints_raw = by_name.get("ntw_Breakpoints")

    marks_for_hash: list[dict[str, Any]] = []
    mark_rows: list[AspireStagingNetWorthMarkRow] = []
    mark_dates: list[date] = []
    mark_count = 0

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
            bp_cell = ntw_breakpoints_raw[i] if ntw_breakpoints_raw and i < len(ntw_breakpoints_raw) else None

            if not any(v not in (None, "") for v in (date_cell, amount_cell, category_cell, note_cell, bp_cell)):
                continue

            mark_date: date | None = None
            if date_cell not in (None, ""):
                mark_date = _serial_to_date(date_cell)
                mark_dates.append(mark_date)

            amount_minor = _money_to_minor(amount_cell)
            mark_count += 1

            category_name = _to_str(category_cell)
            note = _to_str(note_cell)
            bp = _to_str(bp_cell)

            marks_for_hash.append(
                {
                    "row": i,
                    "date": mark_date.isoformat() if mark_date else None,
                    "amount_minor": amount_minor,
                    "category": category_name,
                    "note": note,
                    "break": bp,
                }
            )

            mark_rows.append(
                AspireStagingNetWorthMarkRow(
                    row_index=i,
                    mark_date=mark_date,
                    amount_minor=amount_minor,
                    category_name=category_name,
                    note=note,
                    breakpoint=bp,
                )
            )

    ntw_min, ntw_max = _date_range(mark_dates)

    fingerprint_payload = {
        "transactions": transactions_for_hash,
        "allocations": allocations_for_hash,
        "net_worth": marks_for_hash,
        "cfg_accounts": cfg_accounts,
        "cfg_cards": cfg_cards,
        "hidden_accounts": hidden_accounts,
        "hidden_categories": hidden_categories,
        "categories_minus_credit_cards": categories_minus_credit_cards,
        "net_worth_assets": net_worth_assets,
        "net_worth_debts": net_worth_debts,
        "net_worth_categories": net_worth_categories,
        "user_def_amounts_minor": user_def_amounts_minor,
        "user_def_goals_minor": user_def_goals_minor,
        "category_type_symbols": category_type_symbols,
        "configuration_rows": [
            {
                "row_type_symbol": r.row_type_symbol,
                "name": r.name,
                "monthly_target_minor": r.monthly_target_minor,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "goal_amount_minor": r.goal_amount_minor,
            }
            for r in configuration_rows
        ],
        "dashboard_category_proxy": {
            name: {
                "configured_budget_minor": row.configured_budget_minor,
                "budgeted_minor": row.budgeted_minor,
                "activity_minor": row.activity_minor,
                "available_minor": row.available_minor,
            }
            for name, row in sorted(dashboard_category_proxy.items())
        },
        "special_labels": special_labels,
        "status_symbols": status_symbols,
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
        net_worth_marks_count=mark_count,
        net_worth_date_min=ntw_min,
        net_worth_date_max=ntw_max,
    )

    return ExtractedAspireRows(
        dataset=dataset,
        transactions=transaction_rows,
        allocations=allocation_rows,
        net_worth_marks=mark_rows,
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
        category_type_symbols=category_type_symbols,
        configuration_rows=configuration_rows,
        dashboard_category_proxy=dashboard_category_proxy,
        special_labels=special_labels,
        status_symbols=status_symbols,
    )
