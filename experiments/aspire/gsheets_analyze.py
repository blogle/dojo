from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from dojo.aspire.gsheets_client import AuthMode, GoogleSheetsAuth, GoogleSheetsClient, load_credentials
from dojo.aspire.semantics_report import SemanticsInputs, build_semantics_report
from dojo.aspire_migration.extract import extract_aspire_rows
from dojo.aspire_migration.sheets import parse_spreadsheet_id


logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch an Aspire sheet via named ranges and produce a privacy-safe semantics report "
            "(counts, overlaps, and net worth mark sparsity)."
        )
    )
    parser.add_argument("--spreadsheet", required=True, help="Spreadsheet id or URL")
    parser.add_argument(
        "--auth-mode",
        default="oauth-user",
        choices=("adc", "service-account", "oauth-user"),
        help="Google Sheets auth mode",
    )
    parser.add_argument("--service-account-key", type=Path, default=None)
    parser.add_argument("--oauth-client-secret", type=Path, default=None)
    parser.add_argument("--oauth-token-cache", type=Path, default=None)
    parser.add_argument("--no-open-browser", action="store_true", help="Do not open a browser for oauth-user")
    parser.add_argument(
        "--show-names",
        action="store_true",
        help="Include user-defined labels in output (otherwise redacted).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write the JSON report.",
    )
    parser.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    spreadsheet_id = parse_spreadsheet_id(args.spreadsheet)

    auth_mode: AuthMode = args.auth_mode  # type: ignore[assignment]
    auth = GoogleSheetsAuth(
        mode=auth_mode,
        service_account_key_path=args.service_account_key,
        oauth_client_secret_path=args.oauth_client_secret,
        token_cache_path=args.oauth_token_cache,
        open_browser=not args.no_open_browser,
    )
    credentials = load_credentials(auth)
    client = GoogleSheetsClient(credentials=credentials)

    metadata = client.get_spreadsheet_metadata(spreadsheet_id=spreadsheet_id)
    names: set[str] = set()
    for r in metadata.get("namedRanges") or []:
        if isinstance(r, dict) and isinstance(r.get("name"), str):
            names.add(str(r["name"]))

    extracted = extract_aspire_rows(client, spreadsheet_id=spreadsheet_id, available_named_ranges=names)

    inputs = SemanticsInputs(
        dataset_fingerprint=extracted.dataset.dataset_fingerprint,
        transactions_count=extracted.dataset.transactions_count,
        transactions_date_min=extracted.dataset.transactions_date_min,
        transactions_date_max=extracted.dataset.transactions_date_max,
        allocations_count=extracted.dataset.allocations_count,
        allocations_date_min=extracted.dataset.allocations_date_min,
        allocations_date_max=extracted.dataset.allocations_date_max,
        net_worth_marks_count=extracted.dataset.net_worth_snapshots_count,
        net_worth_date_min=extracted.dataset.net_worth_date_min,
        net_worth_date_max=extracted.dataset.net_worth_date_max,
        trx_accounts={str(r.account_name) for r in extracted.transactions if r.account_name},
        trx_categories={str(r.category_name) for r in extracted.transactions if r.category_name},
        cfg_accounts=set(extracted.cfg_accounts),
        cfg_cards=set(extracted.cfg_cards),
        budget_categories=set(extracted.categories_minus_credit_cards),
        net_worth_assets=set(extracted.net_worth_assets),
        net_worth_debts=set(extracted.net_worth_debts),
        net_worth_categories=set(extracted.net_worth_categories),
        net_worth_marks=[(m.snapshot_date, m.category_name) for m in extracted.net_worth_snapshots],
    )

    report = build_semantics_report(inputs=inputs, show_names=bool(args.show_names))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Print a small stdout summary (no raw values).
    uni = report["universes"]
    overlaps = report["overlaps"]
    marks = report["net_worth_mark_stats"]
    print(
        json.dumps(
            {
                "dataset_fingerprint": report["dataset"]["dataset_fingerprint"],
                "universes": uni,
                "overlaps": {
                    "nw_vs_trx_accounts_exact": overlaps["net_worth_vs_trx_accounts_exact"]["count"],
                    "nw_vs_budget_categories_normalized": overlaps["net_worth_vs_budget_categories_normalized"]["count"],
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


if __name__ == "__main__":
    raise SystemExit(main())
