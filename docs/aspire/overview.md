# Aspire Budget (GSheets) — Reverse Engineering Notes

This documentation set exists to support:

- implementing Aspire-aligned behavior in Dojo, and
- implementing a robust Aspire -> Dojo migration that survives user customization.

Aspire is implemented as a Google Sheet. In a spreadsheet, users can move visible UI elements around, so cell coordinates are not a stable interface. The stable interface is the spreadsheet’s **named ranges** (named, bounded regions of cells), plus the formulas that reference them.

## Evidence-driven workflow

We avoid guessing Aspire behavior. Instead we extract evidence from an Aspire sheet via the Google Sheets API and document what we see.

Tooling:

- Exporter: `python -m dojo.aspire.gsheets_export`
  - Exports sheet metadata + named ranges.
  - Optionally exports formulas / values for each named range.
  - Writes all raw exports under `artifacts/aspire_gsheets/...` (gitignored).

## How to reproduce an export locally

From the repo root:

- Metadata only:

  uv run --extra gsheets -m dojo.aspire.gsheets_export \
    --spreadsheet-id <ID>

- Include formulas for named ranges:

  uv run --extra gsheets -m dojo.aspire.gsheets_export \
    --spreadsheet-id <ID> \
    --include-named-range-formulas

- Include formulas for specific A1 ranges (useful for key tables not covered by named ranges):

  uv run --extra gsheets -m dojo.aspire.gsheets_export \
    --spreadsheet-id <ID> \
    --include-a1-range-formulas \
    --a1-range "'Dashboard'!H6:R91" \
    --a1-range "'Calculations'!A1:Z220"

  Notes:

  - Quote sheet titles with spaces: `"'Category Allocation'!B7:E7"`.
  - Exports are written under `artifacts/` (gitignored).

- Include values for named ranges (redacted by default unless you remove the flag):

  uv run --extra gsheets -m dojo.aspire.gsheets_export \
    --spreadsheet-id <ID> \
    --include-named-range-values \
    --redact-values

## Authentication

The exporter supports multiple auth modes:

- `--auth service-account`: non-interactive; share the sheet with the service account email and pass `--service-account-key /path/to/key.json`.
- `--auth oauth-user`: interactive OAuth; opens a browser window for a user to grant access. Requires `--oauth-client-secret /path/to/client_secret.json` (downloaded from Google Cloud). The refresh token is cached outside the repo by default at `~/.config/dojo/gsheets/token.json` (override via `--oauth-token-cache`).

## Troubleshooting

- OAuth 403 (e.g. “Access blocked: Authorization Error”): configure the OAuth consent screen in the same Google Cloud project as the client secret JSON. If the app is in “Testing”, add your Google account email as a test user, then retry.

## What goes in this docs set

These docs aim to describe Aspire as a set of domains and contracts:

- what the source-of-truth tables are (user-editable inputs)
- what the derived tables are (pure calculations)
- the semantic rules (month boundaries, rollovers, goals, emergency fund, credit cards)
- the reporting semantics (net worth, spending, trends)
- the migration-relevant invariants (what must be extracted and how to anchor to named ranges)

Entry points:

- Configuration knobs: `docs/aspire/configuration.md`
- Net worth semantics (snapshot-driven): `docs/aspire/net-worth.md`
- Budget semantics: `docs/aspire/budgeting-semantics.md`
- Reports overview: `docs/aspire/reports.md`

## Sheet map (typical Aspire 2.0 layout)

The exact layout can vary, but a representative Aspire sheet includes:

- `Dashboard`: the primary user view of category balances and month budgeting.
- `Transactions`: the canonical transaction ledger input table.
- `Category Allocation`: the canonical allocation / envelope-move log.
- `Configuration`: accounts, categories, goals, and other configuration inputs.
- `BackendData`: derived lists and constants used for dropdowns and reporting.
- `Calculations`: core formulas that compute balances and reports.
- Reports: `Balances`, `Account Reports`, `Category Reports`, `Net Worth Reports`, `Spending Reports`, `Trend Reports`.

Users may also add their own sheets (e.g., loan trackers); migration tooling should ignore unknown sheets unless they are referenced via named ranges.

See also the Dojo-side mapping spec: `docs/plans/aspire-migration-domain-spec.md`.
