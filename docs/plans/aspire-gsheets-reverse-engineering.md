# Aspire GSheets Reverse Engineering + Documentation

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Update every section as discoveries occur so a brand-new contributor can finish the work end to end using only this file and the working tree.

## Purpose / Big Picture

Dojo is based on Aspire Budget. Aspire is implemented as a Google Sheet (GSheets), so users can customize the UI by moving things around. A robust Aspire -> Dojo migration (and future feature parity work) requires understanding Aspire’s operational semantics (domains, entities, calculations, and UX) and building tooling that can read a user’s Aspire sheet reliably despite customization.

Success means:

1) We have safe, repeatable tooling to read a user-provided Aspire GSheet via the Google Sheets API, focusing on named ranges and the “backend data” / calculations sheets.

2) We have a set of repo-tracked documents that explain Aspire’s behavior precisely enough that future work can:

- copy Aspire features into Dojo without guessing,
- map Aspire concepts to Dojo’s domains (ledger, budgeting, net worth, investments, etc.), and
- implement a migration that relies on named ranges instead of hard-coded cell offsets.

This plan is intentionally evidence-driven: we do not assume Aspire behavior; we extract it from the sheet structure, formulas, and named ranges.

Related (already checked in): `docs/plans/aspire-migration-domain-spec.md` describes *Dojo’s* desired import semantics. This plan focuses on *Aspire’s* source-of-truth semantics and how to read them.

## Progress

- [x] (2026-01-27T20:40Z) Implement `python -m dojo.aspire.gsheets_export` (metadata + named range exports) with safe default outputs under `artifacts/`.
- [x] (2026-01-27T20:40Z) Add unit tests for A1 conversion, range sizing, redaction, and filename sanitization (`tests/unit/aspire/test_gsheets_utils.py`).
- [x] (2026-01-27T20:40Z) Verify tests pass: `uv run -m pytest -q tests/unit/aspire` (18 passed).
- [x] (2026-01-27T21:27Z) Exported named ranges + formulas from a user-provided Aspire sheet (gitignored): `artifacts/aspire_gsheets/<spreadsheet_id>/20260127T212730Z`.
- [x] (2026-01-27T21:27Z) Hardened exporter for real sheets: added `oauth-user` auth + batched `values:batchGet` to avoid 429 rate limits; skip invalid named ranges (missing sheetId / empty ranges).
- [x] (2026-01-29T23:12Z) Add `--a1-range` exports so we can capture non-named-range formulas (e.g. Dashboard/Calculations tables).
- [x] (2026-01-29T23:12Z) Wrote Aspire documentation set under `docs/aspire/` (domains, entities, named ranges, semantics, customization).
- [x] (2026-01-29T23:12Z) Added Dojo/Aspire concept mapping doc (`docs/aspire/dojo-mapping.md`) and updated migration-spec divergences.

## Surprises & Discoveries

- Observation: OAuth consent screen “Testing” requires adding the user as a Test user, otherwise the browser flow returns a 403 before granting access.
- Observation: Some Aspire named ranges can be malformed or partially specified (e.g. missing `sheetId` like `r_DashboardData`, or zero-width ranges like `trx_Uuids`). The exporter must skip these safely.
- Observation: Exporting each named range via one API call can trigger Sheets API 429 rate limits. Batching multiple `ranges=` per `values:batchGet` request avoids this reliably.
- Observation: Many migration-relevant formulas live outside named ranges (e.g. `Dashboard` and `Calculations`). The exporter needs a way to export arbitrary A1 ranges for evidence.

## Decision Log

- Decision: Use named ranges as the primary “anchor” for extraction and semantics discovery because users can move UI regions around but named ranges can remain stable references.
  Rationale: Migration must survive user customization; hard-coded offsets will fail.
  Date/Author: 2026-01-27 / Codex.

- Decision: Store all extracted sheet data (JSON exports) under `artifacts/` (gitignored) by default.
  Rationale: Prevent accidental commits of private financial data while still enabling local analysis.
  Date/Author: 2026-01-27 / Codex.

- Decision: Batch named range formula/value exports via `values:batchGet` with multiple `ranges=` per request.
  Rationale: Avoid Google Sheets API 429 rate limiting while keeping exports readable (one file per named range).
  Date/Author: 2026-01-27 / Codex.

- Decision: Support exporting targeted A1 ranges (opt-in) alongside named ranges.
  Rationale: Some critical formulas live outside named ranges (Dashboard/Calculations), but we still want API-driven, reproducible evidence capture.
  Date/Author: 2026-01-29 / Codex.

## Outcomes & Retrospective

To be filled in as milestones complete.

## Context and Orientation

Aspire is a budgeting system implemented in a spreadsheet. Key properties relevant to migration and reverse engineering:

- Users can reorder/move visible UI sections; cell coordinates are not reliable.
- Named ranges are the stable “API surface” of a spreadsheet.
  - A named range has a name (string) and a grid range (sheet + row/column bounds).
  - Formulas can reference named ranges; those references survive many layout changes.
- Aspire typically has hidden “backend data” and “calculation” tabs where:
  - user config is normalized into tabular forms,
  - the ledger/budget state is computed, and
  - dashboard values are derived.

In Dojo, we will treat Aspire as a source system that emits typed records (accounts, categories, transactions, allocations, net worth snapshots, etc.). The first step is building tooling to *read* Aspire as-is.

## Plan of Work

### Milestone 1 — Implement safe GSheets extraction tooling

Create a small Python CLI that:

- Authenticates to the Google Sheets API using either:
  - Application Default Credentials (ADC), or
  - a service account JSON key.
- Fetches spreadsheet metadata (sheet list and named ranges).
- Optionally exports formulas/values for named ranges (bounded by a max-cell guard).
- Writes outputs under `artifacts/aspire_gsheets/<spreadsheet_id>/<timestamp>/...`.
- Never writes credentials, tokens, or raw exports into git-tracked paths.

At the end of Milestone 1, a contributor can run one command and get a structured export on disk.

### Milestone 2 — Extract evidence from the user’s Aspire sheet

Using the tooling from Milestone 1:

- Export metadata and named ranges.
- Export formulas for named ranges.
- Export values only when necessary, and with optional redaction enabled.

Capture key evidence snippets in this ExecPlan’s `Artifacts and Notes` section (small, sanitized excerpts only).

### Milestone 3 — Reverse engineer Aspire domains + semantics

From the exports:

- Build a named range catalog and group ranges into conceptual domains:
  - accounts
  - categories / envelopes / groups
  - transactions / ledger
  - allocations / budgeting events
  - credit card handling
  - goals / targets
  - net worth / tracking balances
  - monthly rollovers / overspending semantics
- Identify the canonical “tables” (range shapes + header rows) that represent source-of-truth input.
- Identify derived tables (pure formulas) and their dependency graph.

### Milestone 4 — Produce comprehensive Aspire documentation

Create `docs/aspire/` with documents that are useful for both:

- feature parity work (“how does Aspire behave?”), and
- migration work (“how do we read Aspire inputs robustly?”).

Required docs (initial target set; adjust as discoveries occur):

- `docs/aspire/overview.md` — quick orientation: tabs, data flow, primary user workflows.
- `docs/aspire/named-ranges.md` — catalog of named ranges + what they mean.
- `docs/aspire/domains-and-entities.md` — canonical entity types and their fields.
- `docs/aspire/budgeting-semantics.md` — month boundaries, rollovers, overspending rules.
- `docs/aspire/ledger-and-transactions.md` — transaction entry, transfers, splits (if present).
- `docs/aspire/credit-cards.md` — how Aspire reserves/handles credit payments.
- `docs/aspire/net-worth.md` — snapshot semantics and relationship to accounts/ledger.
- `docs/aspire/customization-and-offsets.md` — what users can move, what breaks, why named ranges matter.
- `docs/aspire/dojo-mapping.md` — mapping + divergences vs Dojo (linking to `docs/plans/aspire-migration-domain-spec.md`).

### Milestone 5 — Validation and reproducibility

- Add unit tests for the extraction utilities.
- Ensure the exporter is deterministic for a fixed sheet state.
- Document exact commands to reproduce the exports locally.

## Concrete Steps

All commands are run from the repo root: `/home/ogle/src/dojo`.

1) Install dependencies (if needed by the implementation) using the repo’s Python toolchain.

2) Run metadata export (default behavior). Pick an auth mode:

    # Interactive OAuth (opens browser; caches token under ~/.config/dojo/gsheets/token.json)
    uv run --extra gsheets -m dojo.aspire.gsheets_export --spreadsheet-id <ID> --auth oauth-user --oauth-client-secret <CLIENT_SECRET_JSON>

    # Service account (share the sheet with the service account email)
    uv run --extra gsheets -m dojo.aspire.gsheets_export --spreadsheet-id <ID> --auth service-account --service-account-key <SERVICE_ACCOUNT_KEY_JSON>

3) Run named range formula export:

    uv run --extra gsheets -m dojo.aspire.gsheets_export --spreadsheet-id <ID> --auth <mode> [auth flags...] --include-named-range-formulas

4) Export specific A1 ranges (optional, but useful for Dashboard/Calculations formulas not covered by named ranges):

    uv run --extra gsheets -m dojo.aspire.gsheets_export --spreadsheet-id <ID> --auth <mode> [auth flags...] \
      --include-a1-range-formulas \
      --a1-range "'Dashboard'!H6:R91" \
      --a1-range "'Calculations'!A1:Z220"

5) Run named range values export (usually keep values redacted):

    uv run --extra gsheets -m dojo.aspire.gsheets_export --spreadsheet-id <ID> --auth <mode> [auth flags...] --include-named-range-values --redact-values

6) Inspect the output directory under `artifacts/aspire_gsheets/...`.

## Validation and Acceptance

Milestone 1 acceptance:

- Running the exporter command succeeds and writes:
  - a metadata file with sheet list + named ranges
  - an index of named ranges with computed A1 notation
  - (if selected) formula/value exports for named ranges

Milestones 3–4 acceptance:

- `docs/aspire/*.md` exists and is detailed enough that a new contributor can:
  - explain Aspire’s budgeting semantics (month boundary, overspending, rollovers),
  - identify the source-of-truth tables in the sheet,
  - understand how named ranges anchor the sheet,
  - map Aspire entities to Dojo entities (and explain divergences),
  - implement a migration extractor that does not depend on fixed cell offsets.

## Idempotence and Recovery

- Exports are written to a timestamped directory under `artifacts/` so repeated runs do not overwrite prior evidence.
- The exporter never modifies the spreadsheet (read-only scopes only).
- Credentials are read from:
  - ADC, or
  - a local service account key path.
  The exporter must never copy or persist credentials into the repo.

If auth fails:

- For ADC: re-run `gcloud auth application-default login` (if using gcloud) and re-run the exporter.
- For service accounts: confirm the sheet is shared with the service account email and the key path is correct.

## Artifacts and Notes

(Keep any pasted artifacts small and sanitized. Never paste raw transaction/category names or balances from a personal sheet into this repo.)

- Placeholder: sheet list + hidden flags.
- Placeholder: named ranges list (names + A1 ranges only).
- Placeholder: key formulas that define budget/ledger semantics.

## Interfaces and Dependencies

We will rely on the Google Sheets API v4.

The exporter CLI should live under:

- `src/dojo/aspire/gsheets_export.py` with module entrypoint `python -m dojo.aspire.gsheets_export`.

It must support:

- Auth mode `adc` (application default credentials).
- Auth mode `service-account` (JSON key file).
- Auth mode `oauth-user` (interactive browser OAuth via a client secrets JSON).

Outputs should be JSON for machine readability.

---

Plan change log: initial version created 2026-01-27 to implement GSheets tooling and Aspire reverse engineering as a prerequisite for a robust migration feature.

Plan change log: 2026-01-27 updated CLI commands to use `uv run --extra gsheets` and the current exporter flags.
