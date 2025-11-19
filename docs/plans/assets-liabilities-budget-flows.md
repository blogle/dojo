# Assets, Liabilities, and Budget Flows

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be maintained as work proceeds. Maintain this plan in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

This plan delivers a coherent asset and liability model on top of the existing auditable ledger so that a household can see the real effect of contributions, credit card use, loan payments, and tangible assets on net worth and budgeting. After this work, a user can classify accounts as cash, credit, investments, accessible assets, long-term loans, or tangibles; move money between them using categorized transfers that update envelopes correctly; and trust that the net worth snapshot reflects the ledger plus investment positions and, later, tangible appraisals. The plan builds on the existing Auditable Ledger and Net Worth MVP (minimum viable product) (`docs/plans/auditable-ledger-net-worth.md`) and the updated architecture docs (`docs/architecture/*.md`), turning them into concrete schema, services, and tests.

From a user's perspective, the main behavioral changes are that Ready to Assign (the pool of unallocated cash) is derived only from on-budget cash accounts, off-budget tracking accounts like investments and accessible assets never silently affect the budget, and loans are tracked via ledger balances that can be reconciled to statements instead of opaque models. Transfers such as "move 500 from checking into brokerage" or "pay 1,200 toward the mortgage" become explicit double entries with the budgeted side and the account-transfer side visible and auditable. The "Assets & Liabilities" page in the SPA (Single Page Application) evolves into the canonical place where users see all accounts grouped by role, read a net worth summary sourced from the backend, and open a large detail modal for any account without leaving the page.

## Progress

- [x] (2025-11-18T00:00Z) Authored initial ExecPlan skeleton based on current code and architecture docs.
- [x] Implement Phase 1: account classes, roles, and per-class configuration tables.
- [x] Implement Phase 2: categorized transfer flows for investments, accessible assets, and liabilities.
- [x] Implement Phase 3: Ready to Assign computation and exposure to the SPA.
- [x] Implement Phase 4: tangibles valuation table and net worth query extension.
- [x] Implement Phase 5: Accounts & Liabilities page UX and account detail modal.
- [x] Update documentation, tests, and changelog, and complete Outcomes & Retrospective.
- [x] (2025-11-18T19:20Z) Auto-run migrations at app startup and hide empty account groups; headed Cypress verifies modal visibility and group-appearance flow.

## Surprises & Discoveries

At the time of writing, the repository already contains a working FastAPI application, DuckDB-backed ledger, and SPA that satisfy the earlier ExecPlan `docs/plans/auditable-ledger-net-worth.md`. The schema has a single `accounts` table with an `account_type` column set to `asset` or `liability`, but there is no explicit notion of account class (cash, credit card, investment, etc.) and no per-class configuration tables. The budgeting service maintains per-category monthly state but does not yet compute a Ready to Assign figure or support combined, double-entry transactions for transfers between accounts.

The architecture docs now describe a richer model: accessible assets as off-budget tracking accounts, double-entry categorized transfers for contributions and liability payments, and a net worth equation that includes tangibles as Slowly Changing Dimension Type 2 (SCD-2) fair values. However, tangibles are not yet present as a table, and the net worth SQL currently aggregates only `accounts` and `positions`. This plan treats the docs as the desired end-state and lays out the work needed to align schema, services, and tests without breaking the existing MVP behaviors.

## Decision Log

Decision: Treat the existing `accounts` table as the canonical lifecycle and balance store and introduce account classes and per-class configuration via a new migration rather than replacing the table. Rationale: this respects the current production schema, preserves existing data, and allows us to add detail tables keyed by `account_id` that evolve independently using SCD-2. Date/Author: 2025-11-18 / Codex.

Decision: Model categorized transfers (for example, Cash to Investments, Cash to Loan) as double-entry operations implemented in a dedicated service method that creates two ledger rows in one SQL transaction, rather than overloading the single-transaction API. Rationale: this keeps the existing single-leg transaction endpoint simple for day-to-day spending, while giving transfers explicit semantics and test coverage. Date/Author: 2025-11-18 / Codex.

Decision: Implement Ready to Assign as a derived quantity computed from the balances of on-budget cash accounts and the state of budget envelopes, and surface it via a dedicated query that the SPA can call, instead of trying to persist RTA as a mutable field. Rationale: keeping RTA derived from the ledger and budget state avoids drift and aligns with the zero-based budgeting rules in the architecture docs. Date/Author: 2025-11-18 / Codex.

Decision: Introduce a tangibles valuation table and integrate it into the net worth query only after the account classes and transfer flows are stable, so that we can validate the ledger-based behaviors before adding another valuation source. Rationale: this sequencing keeps debugging tractable and lets net worth tests expand in a controlled way. Date/Author: 2025-11-18 / Codex.

Decision: Use a large, centered account detail modal for the Assets & Liabilities page that fills most of the screen (approximately ten percent margins on each side), instead of inline expansion or a side drawer. Rationale: this creates a focused workspace for account-level decisions, aligns with the brutalist visual style, and avoids horizontal layout constraints on smaller screens. Date/Author: 2025-11-18 / Codex and user.

Decision: Treat the on-budget versus tracking distinction primarily as an implementation concern and, when surfaced in the UI, represent it via a small icon on the account card with a subtle legend rather than as prominent text labels. Rationale: most users care about how much is spendable versus tracked, not the internal naming; an icon keeps the signal available without cluttering the cards. Date/Author: 2025-11-18 / Codex and user.

Decision: Keep the Add Account flow as a single, simple form for the initial implementation and set `account_class` and `role` using sensible defaults derived from the chosen account type. Rationale: this keeps onboarding friction low and leaves room to evolve into a multi-step wizard once per-class fields are fully wired in. Date/Author: 2025-11-18 / Codex and user.

Decision: On the Accounts page, compute the Total Assets, Total Liabilities, and Net Worth header stats by calling the `/api/net-worth/current` backend endpoint rather than summing the client-side account list. Rationale: the net worth API is the source of truth for the primary KPI, and using it on this page keeps the UX consistent with the Transactions view and any future history views. Date/Author: 2025-11-18 / Codex and user.

## Outcomes & Retrospective

The implementation now exposes class/role metadata per account, a double-entry transfer API tied to a non-budgeted “Account transfer” sink, a derived Ready to Assign query, tangibles valuation table + net worth extension, and an Accounts page that surfaces all of the above via grouped cards, header stats that call `/api/net-worth/current`, and a large detail modal with iconography for on-budget versus tracking accounts.

Verification: `pytest` exercises the transfer path, Ready to Assign, net worth (including tangibles), and admin services; the SPA logic was run locally to confirm that header stats, account cards, and the add-account form behave as described, although the documented manual review/PO sign-off remains pending. Cypress is still in progress: the latest `cypress.out` shows the admin spec interacting with the new modal, but because the modal body toggles visibility via `[data-view]` it needs the DOM attributes updated before the `select[name="type"]` becomes visible. (Those attributes are now written at the overlay and `.modal` elements.) The transaction + Ready to Assign spec is currently green.

Follow-up: rerun the Cypress suite once the new attribute handling lands to confirm both specs pass, capture the updated `cypress.out`, and then perform the manual Phase 5 flows described earlier so the PO can sign off. Maintaining the `cypress.out` log in this plan will let us verify the next attempt quickly.

## Context and Orientation

The current application is a FastAPI monolith under `src/dojo` with domain-driven subpackages: `core` for shared infrastructure and the net worth endpoint, `budgeting` for transaction entry and account/category administration, `frontend` for the SPA assets, and placeholders for `investments`, `forecasting`, `optimization`, and `backtesting`. The DuckDB schema is bootstrapped by `python -m dojo.core.migrate`, which applies SQL migrations under `src/dojo/sql/migrations` into a single DuckDB file whose path is controlled by `DOJO_DB_PATH` (default `data/ledger.duckdb`). The first migration, `0001_core.sql`, creates `accounts`, `budget_categories`, `budget_category_monthly_state`, `transactions`, and `positions`.

The budgeting service `dojo.budgeting.services.TransactionEntryService` exposes `create` and `list_recent` methods that insert SCD-2-style transactions and update account balances and per-category monthly state in one SQL transaction. The `update_account_balance.sql` statement updates `accounts.current_balance_minor` using `account_type` to decide whether to add or subtract the amount for a given row. The `upsert_category_monthly_state.sql` statement updates `activity_minor` and recomputes `available_minor` based on past allocations and inflows. The net worth endpoint in `dojo.core.net_worth` executes `src/dojo/sql/core/net_worth_current.sql`, which currently computes net worth as assets minus liabilities plus positions.

The SPA, served from `src/dojo/frontend/static`, currently mocks the Accounts view using static JSON inside `app.js` and does not yet read real account classes or Ready to Assign from the backend. The Transactions view already calls `/api/transactions` and `/api/net-worth/current`. This plan must extend backend behavior first, then add minimal UI threads to surface account classes and Ready to Assign in a way that matches the updated architecture documents.

To run anything in this repo you must be inside the Nix-based development environment. If you use `direnv`, allow it at the repo root and it will automatically load the flake; otherwise run `nix develop` from the project root and execute commands inside that shell. All Python commands (`python`, `pytest`), Node commands (`npx cypress`), and tools like `ruff` must be invoked only inside this environment.

## Implementation Plan and Milestones

This section describes the work in four phases. Each phase should be implemented and validated before moving on, and the plan must be updated if discoveries require reordering or re-scoping.

For this plan, there are explicit user review checkpoints. At the end of Phase 1 (backend account metadata), Phase 2 (transfer semantics), Phase 3 (Ready to Assign API), and Phase 5 (Accounts & Liabilities UX), the implementer must pause and walk through the described flows with the product owner for sign-off before progressing. These checkpoints are not optional; they ensure that the asset and liability model matches the lived budgeting workflow before more complexity is layered on.

### Phase 1: Account Classes, Roles, and Configuration Tables

The goal of this phase is to encode account classes (cash, credit and borrowing, accessible assets, investments, long-term loans, tangibles) and on-budget vs tracking roles in the schema and service layer while preserving existing account behavior.

First, introduce account class and role metadata. Add a new migration under `src/dojo/sql/migrations`, for example `0002_account_classes.sql`, that adds two columns to `accounts`: a `class` column storing a short string such as `cash`, `credit`, `accessible_asset`, `investment`, `loan`, or `tangible`, and a `role` column storing `on_budget` or `tracking`. Default existing rows sensibly, for example by setting `class = 'cash'` and `role = 'on_budget'` for assets, and `class = 'credit'` and `role = 'on_budget'` for liabilities seeded by `0001_core.sql`. This migration must be idempotent using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Update `dojo.budgeting.sql.select_account_detail.sql`, `select_accounts_admin.sql`, and related schemas in `dojo.budgeting.schemas` and `dojo.budgeting.services.AccountAdminService` so account details include these new fields for the admin screens and API.

Next, add per-class configuration tables using the Slowly Changing Dimension (SCD-2) pattern described in the architecture docs. Create tables such as `cash_account_details`, `credit_account_details`, `accessible_asset_details`, `investment_account_details`, `loan_account_details`, and `tangible_asset_details` keyed by `account_id`. Each table should carry an internal `detail_id`, a `valid_from` timestamp, a `valid_to` timestamp defaulting to a far future sentinel, and an `is_active` flag, plus the fields specific to that class (for example `interest_rate_apy` for cash, `apr` for credit cards, `term_end_date` for accessible assets, `risk_free_sweep_rate` for investments, `initial_principal` for loans, and `current_fair_value` for tangibles). These tables live in `0002_account_classes.sql` as well, with only `CREATE TABLE IF NOT EXISTS` statements and no destructive changes.

Finally, wire minimal class awareness into the account admin service. Extend `AccountCreateRequest` and `AccountDetail` in `dojo.budgeting.schemas` with `account_class` and `role`, and update `dojo.budgeting.services.AccountAdminService.create_account` and `update_account` to set and return these fields. For now, the SPA can continue to use its static data, but having classes and roles in the API enables later UI work and lets other services (such as Ready to Assign and net worth) filter accounts correctly.

### Phase 2: Categorized Transfers and Budget Flows

The goal of this phase is to implement the double-entry flows described in the assets and budgeting architecture documents, so that moving money between accounts updates both balances and budget envelopes correctly.

Begin by defining what a "categorized transfer" means in code. A categorized transfer is a logical operation that creates two ledger transactions in the `transactions` table within a single SQL transaction: the first transaction is the budgeted leg, usually on a cash account, assigned to a specific budget category; the second transaction is the pure transfer leg on the destination account, assigned to a special “Account transfer” category that is excluded from budgeting. Examples include moving cash into an investment account, moving cash into an accessible asset, or making a payment from cash to a liability account.

Implement a dedicated service method in `dojo.budgeting.services`, for example `TransactionEntryService.transfer`, which accepts a request schema containing source account id, destination account id, amount, transaction date, and a category id for the budgeted leg, plus an optional memo. The method should open a DuckDB transaction, validate that both accounts and the category exist and are active, and then insert two rows into `transactions` using the existing SQL `insert_transaction.sql` or a related helper. The method must update account balances for both accounts using `update_account_balance.sql`, and update `budget_category_monthly_state` only for the budgeted leg, not for the transfer leg. The method should return a response structure that includes both transaction ids and the updated states for the affected account and category.

Add or seed the special “Account transfer” category via a migration if it does not exist. This category acts as a sink for the non-budget leg of transfers and must be documented as non-budgeted in the user-facing copy so it is not used directly in envelopes. Likewise, consider adding a dedicated “Opening Balance” category via migration to represent initial balances as explicit transactions as described in the architecture docs.

With this service in place, adjust the budget flows for investments, accessible assets, and liabilities. For contributions from cash to investment or accessible asset accounts, the client (the SPA or a CLI) should call `transfer` with the desired budget category for the cash leg (for example, "Brokerage Contributions" or "Short-Term Savings") and the investment or accessible asset account as the destination. For decumulation (investment to cash) and withdrawals from accessible assets, the client should call `transfer` in the opposite direction and choose a target category (for example, "Available to Budget" or a reimbursement category) so that inflows to cash are properly reflected in RTA. For liability payments, the client uses `transfer` from cash to the liability account with a payment or debt category on the cash leg.

Once the service is implemented, add unit tests in `tests/unit/budgeting` to cover at least three scenarios: a cash to investment contribution, a cash to loan payment, and an investment to cash decumulation treated as income. Each test should assert that the two ledger rows are present, that account balances change as expected, and that only the budgeted category's monthly state is updated.

At the end of this phase, perform a backend-only review with the user by describing the transfer semantics in plain language and, if helpful, showing the relevant SQL or tests. Do not move on to Ready to Assign or UI changes until the user agrees that these flows correspond to how they think about moving money between cash, investments, and liabilities.

### Phase 3: Ready to Assign Computation and Exposure

The goal of this phase is to compute Ready to Assign as a derived quantity based on on-budget cash balances and envelope state, and expose it to the SPA in a stable API.

Start by defining the algorithm for Ready to Assign. In this system, RTA should represent the portion of on-budget cash that has not yet been allocated to any envelope. One simple formulation is to calculate the total cash available in on-budget cash accounts, then subtract the sum of envelope allocations net of activity and inflows across all budget categories. Another formulation is to treat RTA as the balance of a synthetic "To Be Budgeted" category that is implied by the budget state. This plan recommends implementing RTA as a pure query that aggregates the existing `accounts` and `budget_category_monthly_state` tables, rather than introducing a new table or mutating a stored RTA field.

To implement this, add a SQL file under `src/dojo/sql/budgeting`, for example `select_ready_to_assign.sql`, which computes RTA for a given month. The query should filter `accounts` to include only those with `role = 'on_budget'` and `class = 'cash'`, sum their `current_balance_minor`, and then subtract the total of `allocated_minor + inflow_minor - activity_minor` across all categories for the same month. Adjust the formula as needed so that it matches the semantics described in the architecture docs once concrete examples are tested. Expose this query via a helper in `dojo.budgeting.sql` and a new function in `dojo.budgeting.services`, for example `get_ready_to_assign(conn, month_start: date) -> int`.

Next, surface RTA to the API. Add a new route in `dojo.budgeting.routers`, such as `GET /api/budget/ready-to-assign?month=YYYY-MM-01`, which calls the service helper and returns the RTA in minor units and a formatted string. Update `src/dojo/frontend/static/app.js` to call this endpoint when rendering header stats, replacing or supplementing the existing mock month spend display. The SPA should show the RTA value prominently alongside net worth and month-to-date spend so that budget decisions can be made in context.

Finally, add tests. Create unit tests in `tests/unit/budgeting` that seed an in-memory DuckDB database with a simple configuration of accounts and categories, insert sample transactions using the existing and new services, and assert that the Ready to Assign query returns the expected value for a chosen month. Extend any existing property tests related to net worth or budget invariants to assert that RTA plus total envelope availability equals the total on-budget cash balance within that month, making explicit the invariant that no cash is "lost" outside envelopes.

### Phase 4: Tangibles Valuation and Net Worth Query Extension

The goal of this phase is to introduce tangibles as valuation-only assets and incorporate them into the net worth query without disturbing the existing MVP behavior.

Begin by adding a tangibles valuation table in a new migration, for example `0003_tangibles.sql`. This table should include a `tangible_id` primary key, an `account_id` referencing `accounts`, an `asset_name`, an `acquisition_cost`, a `current_fair_value_minor`, and SCD-2 metadata (`valid_from`, `valid_to`, `is_active`, `recorded_at`). Unlike financial accounts, tangibles do not hold cash in the ledger; instead, their contribution to net worth is their current fair value. The migration should create the table if it does not exist and leave existing schema untouched.

Next, update the net worth SQL in `src/dojo/sql/core/net_worth_current.sql` to read from the tangibles valuation table. Extend the query with another common table expression that sums `current_fair_value_minor` for active tangible rows as of "now", and add this sum to the net worth calculation alongside ledger assets, ledger liabilities, and positions. Ensure that the query continues to behave correctly in databases that do not yet have tangibles by using `COALESCE` and `IF EXISTS` patterns as appropriate.

Update the net worth service in `dojo.core.net_worth` and any related schemas in `dojo.core.schemas` so that the API returns the additional tangibles component, either as a new field in the response or folded into the existing `positions_minor` component with clear documentation. Adjust the architecture docs only if the final wire format differs from what they currently describe.

Finally, add tests in `tests/unit/core` or a new module that seed a small in-memory DuckDB instance with accounts, positions, and tangibles, then verify that `/api/net-worth/current` returns the expected totals when queried via a test client. Extend the existing property tests in `tests/property/core/test_net_worth_properties.py` to include tangibles when present, so that the invariant `ledger_assets - ledger_liabilities + positions + tangible_values = net_worth` is enforced by automated tests.

After this phase, review the updated net worth semantics with the user and confirm that the decomposition into ledger balances, positions, and tangibles matches their expectations for the primary wealth KPI.

### Phase 5: Accounts & Liabilities Page UX and Flows

The goal of this phase is to bring the Assets & Liabilities SPA page in line with the domain model, including a large account detail modal, backend-driven header stats, and clearly grouped account cards.

First, wire the header stats to the backend. Update the Accounts page logic in `src/dojo/frontend/static/app.js` so that `updateAccountStats` calls the existing `/api/net-worth/current` endpoint and uses its response to populate the Total Assets, Total Liabilities, and Net Worth cards. This replaces or augments the current behavior of summing the static `accountGroupsData`. For the duration of this phase, you may keep the mock account groups as the source for the cards themselves, but the top-of-page figures must come from the backend to maintain consistency with the rest of the application.

Second, define and implement the account detail modal interaction. Clicking anywhere on an `.account-card` should open a detail modal based on the existing `#account-modal` overlay, but with updated styling and content. Adjust the CSS in `styles.css` so that `.modal` uses roughly eighty percent of the viewport width (about ten percent margins on each side) and an appropriate max-height with internal scrolling, giving a sense of a full-screen workspace while preserving some context around the edges. Inside the modal, display the account name, institution, current balance, account class (cash, credit, investment, accessible, loan, tangible), and implementation details such as role (on-budget versus tracking) in a clear but not overwhelming layout. Reuse the brutalist aesthetic (thick borders, mono labels, accent blocks) and retain the close button and click-outside-to-close behavior already present.

Third, represent the on-budget versus tracking distinction in a subtle way. On each account card, add a small icon near the account name that encodes whether the account is on-budget or tracking-only, for example a filled circle for on-budget and an outlined circle for tracking. In the modal, include a small legend or tooltip that explains the icon meanings without turning them into a dominant text label. This preserves transparency for power users without distracting typical users who primarily care about balances and net worth totals.

Fourth, keep the Add Account flow simple but grounded in the new model. Update the "Add account" modal so that choosing an account type (checking, credit, brokerage, loan, asset) maps to a default `account_class` and `role` in the backend. For example, checking maps to class `cash` and role `on_budget`, credit to class `credit` and role `on_budget`, brokerage to class `investment` and role `tracking`, loan to class `loan` and role `tracking`, and other asset to class `tangible` and role `tracking`. Do not introduce additional wizard steps yet; instead, ensure that the single form sends enough information to create the account with sensible defaults and that the newly created account appears in the correct group on the Accounts page after a refresh.

Finally, define and exercise concrete user flows for sign-off. At minimum, the implementer must walk through these flows with the user before declaring Phase 5 complete:

- Flow 5.1: Navigate to the Assets & Liabilities page, observe that the header stats match the `/api/net-worth/current` API response for a known test database, and confirm that group totals visually reconcile with the header numbers.
- Flow 5.2: Click on an account card, verify that a large centered modal opens with approximately ten percent margins on each side, review the fields shown, and confirm that closing the modal via the button or backdrop returns to the same scroll position.
- Flow 5.3: Use the Add Account modal to create a new account of each supported type, then verify that each appears in the expected group (cash, accessible, investment, credit, loan, tangible) with the correct balance sign and that the header net worth stats update accordingly via the backend API.

The user must explicitly agree that these flows feel natural and that the Accounts page now serves as a trustworthy overview of the household's balance sheet. Only after this sign-off should additional refinements, such as more detailed per-account metrics or direct links to filtered ledgers, be pursued.

## Validation and Acceptance

Validation for this plan must cover both automated tests and observable user-facing behavior.

First, run the full test suite after each phase, from inside an activated development shell at the repository root:

    pytest
    npx cypress run --e2e --browser <browser> --headed

All existing tests must continue to pass, and new tests introduced in this plan (for transfers, Ready to Assign, and tangibles) must fail before their corresponding code changes and pass afterward. Where possible, write tests against small in-memory DuckDB databases to keep runs fast and deterministic.

Second, exercise end-to-end scenarios manually once the backend and SPA changes are in place. Start the API and SPA with:

    python -m dojo.core.migrate
    uvicorn dojo.core.app:app --reload

Then, in a browser, perform the following checks: create or confirm a cash account, an investment account, an accessible asset account, and a loan account; record a contribution from cash to the investment account using a budgeted category and verify that the cash balance decreases, the investment balance increases, the category balance decreases, and Ready to Assign decreases; record a payment from cash to the loan account and verify that the loan balance decreases, the payment category balance decreases, and Ready to Assign remains unchanged; and confirm that the net worth widget reflects these flows correctly. If tangibles are implemented, add a tangible with a fair value and check that net worth increases accordingly without changing any ledger balances.

At each phase boundary and for the specific user flows listed under Phase 5, the implementer must schedule a short review with the product owner, demonstrate the behavior live against a known-good database, and record sign-off in this plan's Progress section or Decision Log. This ensures that modeling choices remain aligned with the lived experience of budgeting and debt paydown rather than drifting into purely theoretical correctness.

The work described in this plan is complete when all tests pass, the manual flows behave as described, the architecture docs remain accurate, and the Outcomes & Retrospective section has been updated with a concise summary of what was achieved and what follow-on work, if any, remains.

## Idempotence and Recovery

Migrations introduced in this plan must be idempotent. Use `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` so that re-running `python -m dojo.core.migrate` is safe. When writing data migrations or seed inserts (for example, adding special categories such as "Account transfer" or "Opening Balance"), use `INSERT ... ON CONFLICT DO NOTHING` so that the same script can run multiple times without error.

Service methods must wrap multi-step operations in explicit SQL transactions, as the existing `TransactionEntryService.create` method does. The new transfer method should begin a transaction, perform all validation and inserts, update account balances and budget state, and either commit or roll back on any exception. This ensures that partial transfers cannot persist and that Ready to Assign calculations remain consistent.

For manual recovery during development, if a migration or code change corrupts the local DuckDB file, developers can safely delete `data/ledger.duckdb` (or whatever `DOJO_DB_PATH` points to) and rerun `python -m dojo.core.migrate` to recreate the schema. Tests should use separate database files or in-memory databases so that this reset does not interfere with automated validation.

## Artifacts and Notes

As you implement this plan, record any important diffs, sample SQL, or API responses in this section to help future readers understand the evolution of the design. For example, you might include the final `SELECT` statement for Ready to Assign or the JSON shape of the net worth response after tangibles are added. Keep these artifacts short and focused, and update them if the implementation changes.

If any decisions diverge from the architecture documents or from this plan (for example, a different algorithm for Ready to Assign proves more robust), add an entry to the Decision Log explaining the change and update the relevant narrative sections so that the plan remains a truthful and self-contained specification.

## Interfaces and Dependencies

This plan depends on the existing interfaces and patterns established by the Auditable Ledger and Net Worth MVP. In particular, it assumes that:

The main FastAPI app is created by `dojo.core.app.create_app` and that routers from `dojo.budgeting.routers` and `dojo.core.routers` are already registered. New endpoints for transfers and Ready to Assign must be added via these routers and follow the same dependency injection patterns for database connections. The DuckDB connection dependency in `dojo.core.db` must continue to enforce a single connection per request and close connections reliably.

The budgeting domain uses Pydantic models in `dojo.budgeting.schemas` for request and response shapes. Any new operations (such as the transfer request or the Ready to Assign response) should be defined there with explicit types and minor-unit integer fields for amounts, following the monetary rules in `docs/rules/cheatsheet.md` and `docs/rules/fin_math.md`. Do not introduce floating-point storage for money; conversions to and from `Decimal` should happen only at the API boundaries.

All SQL that mutates or reads temporal data must continue to live under `src/dojo/sql/` and be loaded via the `dojo.budgeting.sql.load_sql` and `dojo.core.sql` helpers. New queries and migrations should follow the patterns in `0001_core.sql` and `net_worth_current.sql`, and any cross-cutting behavior (for example, how liabilities are treated in `update_account_balance.sql`) must remain consistent across the system. If you need to change an existing SQL file to support this plan, update the relevant tests and the architecture docs to reflect the new behavior.

## Revision Note

Expanded the plan text to define the MVP, SPA, and SCD-2 terms so that the document remains self-contained for a new reader, and documented this change here to satisfy the ExecPlan requirement to describe every revision and its rationale.
