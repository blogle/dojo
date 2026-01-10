# AGENTS.md — How to Work in This Repo

You are a coding and research agent working on **Dojo**, a self-hosted personal finance app that replaces a household budgeting spreadsheet. Dojo combines envelope budgeting with net-worth tracking, forecasting, and portfolio analytics.

This file onboards you into the codebase. It tells you:

- **WHY** this project exists and what “good” looks like.
- **WHAT** major pieces of the system are and where to look.
- **HOW** you should work in this repo (tools, docs, and non-negotiable rules that are *not* covered by linters).

Anything more specific should be discovered via the linked docs (“progressive disclosure”), not hard-coded here.


## 1. Values & Collaboration

These values apply to *all* tasks in this repo:

- **Truth in Data** — Prefer evidence over hunches. Validate before you speculate.
- **Rigor is Respect** — Clear, reproducible code and experiments are how we respect future maintainers.
- **Skepticism is Strength** — Question assumptions (including your own and the user’s).
- **Simple by Design** — Prefer simple, explicit, data-oriented designs over clever abstractions.
- **Derive, Then Describe** — Do the math / reasoning first, then explain it in plain language.

Communication principles:

- If you’re unsure, say so and propose how to reduce the uncertainty (test, measurement, log).
- Push back on bad ideas or risky shortcuts; explain *why* in technical terms when you can.
- Treat the user as a partner, not a boss to appease. Do not be sycophantic or over-agreeable.
- **Never** silently cut corners on financial math or data integrity.


## 2. How to Work in This Repo (High-Level Workflow)

### 2.1 Environment & Commands

- Always run commands **inside the Nix dev shell**:
  - With `direnv`: `cd dojo` then `direnv allow .` (once); afterwards, just `cd` into the repo.
  - Without `direnv`: `nix develop` from the repo root, then run commands inside that shell.
- Prefer repo scripts over raw tools:
  - **Tests**: `scripts/run-tests` (with `--skip-*` flags as needed; see `scripts/README.md`).
  - **Releases**: `scripts/release --bump {patch|minor|major}` (add `--notes-llm codex|gemini|none` as needed) to bump `pyproject.toml`, roll `CHANGELOG.md`, tag, and push; never hand-edit versions or changelog for a release.
- When you need underlying tools:
  - Python: `python -m ...` (never ad-hoc `sys.path` hacks).
  - Cypress: `npx cypress run --e2e ...`.

If you are ever tempted to invent a new “one-off” command, first check `scripts/README.md` and `.agent/TOOLS.md`.


### 2.2 Planning & Research (Big Levers)

Use these for any non-trivial change:
- **ArchMap (`.agent/ARCH_MAP.md`)
  - Use when the work may change structure or boundaries:
    - new modules/packages, new domain boundaries (“cities”), or new shared infrastructure (“resources”)
    - new cross-domain APIs/contracts/events (“highways”)
    - performance-sensitive paths, data ownership changes, persistence patterns, or observability wiring
  - Expectations:
    - Prefer solutions that stay within one “city” and minimize cross-map travel.
    - Maintain a succinct **Constitution** (amendments-style technical requirements/tradeoffs) in `ARCHITECTURE.md`.
    - No ADR directory: architectural decisions are captured as Constitution amendments in `ARCHITECTURE.md`,
      with optional deeper notes under `docs/architecture/` or `docs/data-model/`.
    - When architecture changes, update `ARCHITECTURE.md` and (if newcomer workflows changed) `README.md`
      in the same change as the code.
- **ExecPlan** (`.agent/PLANS.md` + `docs/plans/*.md`)
  - When writing complex features or significant refactors, use an ExecPlan (as described in .agent/PLANS.md) from design to implementation.
  - For features, refactors, or infra changes.
  - A plan must be self-contained, living, and explain how to see the behavior working.
- **ExecResearch** (`.agent/RESEARCH.md` + `docs/research/*.md`)
  - For open-ended or algorithmic work (portfolio math, forecasting, etc.).
  - Must capture experiments, metrics, and how to reproduce them.

Rule of thumb: if you’d explain a change in more than a few paragraphs in a PR, it probably deserves an ExecPlan or ExecResearch doc.


### 2.3 Validation

Before you call a task “done”:

1. Run the relevant tests via `scripts/run-tests` (skip flags allowed if explicitly requested).
2. For API/SPA changes, manually exercise the flow:
   - Start the app: `uvicorn dojo.core.app:create_app --factory --reload`.
   - Hit the SPA and walk through the affected page (transactions, budgets, allocations, etc.).
3. For data or math changes, add or update tests that encode the **invariants** (see Section 4).


## 3. Progressive Disclosure: Where to Look for Details

Do **not** stuff all rules into this file. When you start a task, decide which of these are relevant and read them as needed:

- **Architecture & Data Model**
  - `ARCHITECTURE.md` — System purpose, critical files, runtime flow, invariants, and quality attributes.
  - `.agent/ARCH_MAP.md` — Architecture “map-making” prompt: boundaries, highways, resources, and the Constitution.
  - `docs/data-model/overview.md` — SQL schema overview and service-level docs.

- **Rules & Domain Invariants** (non-linter)
  - `docs/rules/fin_math.md` — Financial math conventions: simple vs log returns, annualization, volatility, portfolio math.
  - `docs/rules/engineering_guide.md` — DuckDB access, temporal tables, and transactional rules.
  - `docs/rules/frontend.md` — SPA structure, store usage, DOM + API patterns.
  - `docs/rules/cypress.md` — Cypress E2E best practices for stability and maintainability.
  - `docs/rules/style_guide.md` — Visual/UX: minimalist earth tones, layout, typography.

- **Language / Style (mostly enforced by lint/CI)**
  - `docs/rules/python.md` — Architecture and Python practices. Use mainly for design decisions, not minor style.
  - `docs/rules/sql.md` — SQL and DuckDB patterns (migrations vs seeds vs fixtures, pushdown, temporal modeling).

When in doubt, first read **fin_math** + **engineering_guide** before touching anything that changes money, returns, or the ledger.


## 4. Non-Negotiable Invariants (Not Covered by Linters)

These rules matter to correctness and can’t be fully enforced by lint tooling. They are **hard requirements**:

### 4.1 Ledger & Money Types

- Store ledger amounts as **integers in minor units** (e.g., cents) or `Decimal` with fixed quantization.
- Never store balances as floats in persistence or domain models.
- Only round at I/O boundaries (UI, CSV export, etc.); analytics may use float64 internally.

See: `docs/rules/fin_math.md` (“Ledgers & Money Types”).


### 4.2 Returns & Portfolio Math

- **Cross-section (within a period)**: use **simple returns** and start-of-period weights.
- **Time aggregation (across periods)**: use **log returns** (`log1p` / `expm1`).
- Annualization: use mean **log** returns and `exp(mean_log * K) - 1` for CAGR; volatility via `std * sqrt(K)` with `ddof=1`.
- Always be explicit about which return type a function consumes or returns (`s_rt`, `log_rt`).

If you’re writing or changing anything that computes performance, risk, or portfolio allocation, read `docs/rules/fin_math.md` *before* coding.


### 4.3 DuckDB & Temporal Tables

From `docs/rules/engineering_guide.md`:

- **Single-writer mindset**: no long-lived global DuckDB connections. Use per-request connections via FastAPI dependencies; close them when done.
- **Writes are always transactional**:
  - Multi-step operations must be enclosed in `BEGIN … COMMIT`.
- **Temporal tables (SCD2 style)**:
  - Never `UPDATE` or `DELETE` business rows in place.
  - To “edit”: close the current version (`is_active = FALSE`), then `INSERT` a new row version in one transaction.
  - To “delete”: mark inactive and propagate corrections to dependent state.
- **Current vs historical queries**:
  - Current state: filter `is_active = TRUE`.
  - Historical reconstruction: use `recorded_at` + grouping logic; do not reinvent this ad hoc—reuse existing helpers or centralize the pattern.

These patterns are essential to avoid corrupting the ledger or breaking time-travel semantics.


### 4.4 Seeds, Fixtures, and E2E Database State

- Migrations live in `sql/migrations/` and are idempotent.
- Dev/demo seeds live in `sql/seeds/` and **never** run against production.
- Test fixtures go in `tests/fixtures/`; they should be small and deterministic.
- Cypress E2E:
  - Every test must reset and reseed the DB in `beforeEach`.
  - Use the provided `cy.resetDatabase()` / `cy.seedDatabase(...)` commands.

See `docs/rules/sql.md` and `cypress/e2e/README.md` for details when working on tests or data flows.


### 4.5 Changelog & Docs

For user-visible changes:

- Update `CHANGELOG.md` under `[Unreleased]` with a one-line summary.
- If behavior or architecture changes, update:
  - `ARCHITECTURE.md` for system-level changes.
  - Any relevant plan in `docs/plans/`.
- Do **not** let `ARCHITECTURE.md` or plans drift from reality.
- If the change alters boundaries, contracts, shared resources, or system tradeoffs,
  apply the Cartographer prompt (`.agent/ARCH_MAP.md`) and update the Constitution section
  in `ARCHITECTURE.md` (amendments-style, succinct).


## 5. Task Deferral & TODOs

- `TODO.md` is for **off-scope** or **deferred** work (bugs, chores, refactors, feature ideas) discovered while working on something else.
- You **may not** defer parts of the current task to `TODO.md` without explicit approval from the human.
- Each TODO entry must record:
  - Trigger, why deferred, proposed next step, and acceptance criteria.

If in doubt: finish the current task correctly before deferring anything.


## 6. Commit Etiquette (For Humans & Agents That Draft Messages)

When drafting commit messages for humans:

- Use 2–5 sentences that cover:
  - *Why* the change was made.
  - The observed impact (tests, perf, UX).
  - Evaluation results (even if just “all tests passed”).
  - Confirmation that you adhered to `AGENTS.md` and relevant rules docs.

Example shape (don’t obsess over exact wording):

- “Replaced sample covariance with Ledoit–Wolf shrinkage. Reduced portfolio variance by ~5% in backtests with no expected-return loss. Updated tests and documentation to reflect the new optimizer. Verified adherence to financial math and engineering rules.”


## 7. Quick Start for a New Agent Session

When you’re dropped into a fresh session:

1. Skim this `AGENTS.md` section-by-section.
2. For the task at hand, decide which of these to open:
   - Data / math heavy → `docs/rules/fin_math.md` & `docs/rules/engineering_guide.md`.
   - Backend behavior → `ARCHITECTURE.md` + `docs/rules/sql.md`.
   - Frontend/UI → `docs/rules/frontend.md` + `docs/rules/style_guide.md`.
   - Planning / research → `.agent/PLANS.md` or `.agent/RESEARCH.md`.
3. Use `scripts/README.md` and `.agent/TOOLS.md` to decide how to run tests or linters.
4. Only then start editing code or plans.

Keep this file small in your mental model: it’s a **map and value system**, not a dumping ground for every rule. Use the linked docs for specifics.
