# ExecPlan: Account Detail Pages for All Account Types

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Maintain this document in accordance with `.agent/PLANS.md` (repository root). This plan is intended to be fully self-contained for a new contributor.

## Purpose / Big Picture

Today, the Assets & Liabilities page (`/#/accounts`) shows account cards; clicking a card opens a modal with account details and a reconcile button. After this change, clicking any account card navigates directly to an account detail page.

Each account detail page shows a history chart (matching the existing investment/brokerage chart styling and layout) and account-type-specific information. For account types where it makes sense (cash/checking, credit, loans, accessible assets, tangibles), the page also shows a filtered ledger table for that account and includes safe transaction entry actions that reuse the existing global ledger components (so changes to the main ledger UI propagate here). For credit/loan pages, “Record payment” is a transfer (two-leg) flow, not a single-leg ledger entry.

Every account detail page must have an account-type-appropriate integrity action (ledger statement reconcile, investment holdings verification, or tangible valuation update). This plan adds entry points + deep links for these actions, but does not redesign their underlying workflows; ledger reconciliation workflow details live in `docs/plans/reconciliation-feature.md`.

## Progress

- [ ] (YYYY-MM-DD HH:MMZ) Implement canonical `/accounts/:accountId` route + investments redirect alias.
- [x] (2026-01-09 01:27Z) Add backend endpoints for account details + per-account transactions + per-account balance history (including `status` filtering and balance continuity guardrails).
- [ ] (YYYY-MM-DD HH:MMZ) Add frontend API client methods + query key conventions for the new endpoints.
- [ ] (YYYY-MM-DD HH:MMZ) Remove account detail modal; make account cards navigate to detail pages.
- [ ] (YYYY-MM-DD HH:MMZ) Implement account detail pages for all account classes using shared components + shared `?range=` behavior, with liability-safe “Record payment” actions.
- [ ] (YYYY-MM-DD HH:MMZ) Add account-type integrity actions on every detail page using existing flows, with URL-driven modes (`/reconcile`, `/verify-holdings`, `/valuation`).
- [x] (2026-01-09 01:27Z) Add automated tests for new API endpoints and run the relevant test suite.
- [ ] (YYYY-MM-DD HH:MMZ) Manual verification: charts + filtered ledger + integrity actions.

## Surprises & Discoveries

- Observation: (fill in during implementation)
  Evidence: (fill in during implementation)

## Decision Log

- Decision: Do not show integrity-action buttons on every account card in `/#/accounts`.
  Rationale: It is visually noisy; integrity actions will be accessible from each detail page instead.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Loan detail page will not attempt a principal-vs-interest split in v1.
  Rationale: User workflow is a single monthly “mortgage” transaction; Dojo does not currently store principal/interest breakdown data. Showing estimated splits would violate “Truth in Data”.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Integrity actions vary by account type; this plan adds entry points but does not redesign the underlying workflows.
  Rationale: Ledger statement reconciliation is defined in `docs/plans/reconciliation-feature.md`; investment holdings verification remains investment-specific; tangible valuation updates are modeled via `balance_adjustment`.
  Date/Author: 2026-01-08 / user + Codex

- Decision: `/api/accounts/{account_id}/history` defaults to `status=all` (pending + cleared), and both `/history` and `/transactions` support `status=cleared` for cleared-only views (statement context applies a cutoff date).
  Rationale: Account balances are updated regardless of status (see `src/dojo/budgeting/services.py`), so UX parity requires including pending by default; cleared-only views are still needed for statement context, but “Statement” labeling depends on a statement date (see `docs/plans/reconciliation-feature.md`).
  Date/Author: 2026-01-08 / user + Codex

- Decision: Budgeting account history uses budgeting vocabulary (`as_of_date`, `balance_minor`) rather than investment-shaped fields (`market_date`, `nav_minor`).
  Rationale: Avoid cross-domain drift; the frontend can map/format for chart reuse.
  Date/Author: 2026-01-08 / user + Codex

- Decision: `accounts.current_balance_minor` is ledger-derived (cached) and must stay consistent with ledger history.
  Rationale: Prevent silent disagreement between the headline “current value” and the ledger-derived chart (audit continuity / solvency correctness).
  Date/Author: 2026-01-08 / user + Codex

- Decision: Liability “payments” are recorded as two-leg transfers (funding account required); credit/loan pages split `Record payment` (transfer) from `Add charge/fee` (single-leg).
  Rationale: Prevent the “free net worth” bug class where a liability is reduced without a corresponding asset reduction.
  Date/Author: 2026-01-08 / user + Codex

- Decision: `current_balance_minor` and `balance_minor` fields are signed accounting balances (assets positive, liabilities negative). “Owed” is a presentation transform only.
  Rationale: Enforce one canonical sign convention at API boundaries and keep terminology honest.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Account history points are computed as an absolute balance series (baseline before `start_date` + window sum) and the endpoint enforces a maximum date range.
  Rationale: Correctness at the first point and a guardrail against accidental 10–20 year pulls.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Canonical account detail URL is `/accounts/:accountId` for all account classes; `/investments/:accountId` is a redirect alias.
  Rationale: Avoid divergent “account detail” experiences split across two route hierarchies.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Chart range selection is stored in the URL query (e.g., `?range=1M`) and range toggles use `router.replace`.
  Rationale: Makes pages shareable while avoiding Back-button “time travel” through chart tabs.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Integrity action states are encoded in the URL (`/accounts/:accountId/reconcile`, `/accounts/:accountId/verify-holdings`, `/accounts/:accountId/valuation`) even if the UI remains modal in v1.
  Rationale: Predictable deep links and back/forward behavior for linear workflows.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Every account detail page shares the same page chrome (breadcrumb, persistent header, primary/secondary action slots), including investments.
  Rationale: “Same route” should feel like the same surface; reduces IA drift and user confusion.
  Date/Author: 2026-01-08 / user + Codex

- Decision: Liability charts use an “owed” series for geometry/labels and invert the “good direction” for theme coloring.
  Rationale: If the underlying ledger stores liabilities as negative balances, displaying signed deltas (“+$100”) would conflict with user expectations (“I owe $100 less”).
  Date/Author: 2026-01-08 / user + Codex

## Outcomes & Retrospective

(fill in when milestones complete)

## Context and Orientation

### Frontend (SPA)

The SPA is in `src/dojo/frontend/vite/src/` and uses Vue + Vue Router hash history (`src/dojo/frontend/vite/src/router.js`).

Note on docs drift: for actual SPA patterns (Vue + TanStack Query), treat `docs/plans/vue-frontend.md` and existing pages like `TransactionsPage.vue` / `InvestmentAccountPage.vue` as the source of truth; `docs/rules/frontend.md` is stale.

The existing investment account detail page is `src/dojo/frontend/vite/src/pages/InvestmentAccountPage.vue`. It includes:

- an interactive area chart component `src/dojo/frontend/vite/src/components/investments/PortfolioChart.vue`
- a right-side details panel
- a holdings table
- shared styling in `src/dojo/frontend/static/styles/components/investments.css`

The existing Assets & Liabilities page is `src/dojo/frontend/vite/src/pages/AccountsPage.vue`. It currently implements a detail modal (`#account-modal`) and uses `src/dojo/frontend/vite/src/components/ReconciliationModal.vue` as a ledger reconciliation flow.

The shared ledger components that must be reused are:

- `src/dojo/frontend/vite/src/components/TransactionForm.vue`
- `src/dojo/frontend/vite/src/components/TransactionTable.vue`

### Backend (FastAPI)

The app mounts routers at `/api` in `src/dojo/core/app.py`.

- Budgeting APIs live in `src/dojo/budgeting/routers.py`.
- Reconciliation endpoints already exist at:
  - `GET /api/accounts/{account_id}/reconciliations/latest`
  - `GET /api/accounts/{account_id}/reconciliations/worksheet`
  - `POST /api/accounts/{account_id}/reconciliations`
  implemented in `src/dojo/core/reconciliation_router.py` and used by the frontend `ReconciliationModal.vue`.

### Data model (relevant pieces)

- `accounts` is the base table. Money amounts in persistence are integer minor units.
- `transactions` is an SCD2/temporal ledger table keyed by `concept_id` with `valid_from/valid_to/is_active`.
- Account classes include: `cash`, `accessible`, `credit`, `loan`, `tangible`, `investment`.
- Per-class configuration/detail tables exist (SCD2 style) including:
  - `cash_account_details`, `credit_account_details`, `accessible_asset_details`, `loan_account_details`, `tangible_asset_details`, `investment_account_details`.

## Plan of Work

We implement a non-modal navigation model:

1. Remove the “account detail modal” path from `AccountsPage.vue` and replace it with navigation: clicking a card takes you to a detail page.
2. Add a canonical detail route for all accounts (`/accounts/:accountId`) and keep `/investments/:accountId` as a redirect alias.
3. Provide a consistent page chrome (breadcrumb + persistent header + action slots) and layout (chart, ledger table, aside) that reuse the existing investment page’s styling conventions.
4. Build per-account-type content:

   - Cash/checking: balance chart + filtered ledger + basic account stats.
   - Accessible assets: balance chart + filtered ledger + term/APY metadata.
   - Credit: owed chart + filtered ledger + APR metadata.
   - Loan: owed chart + filtered ledger + “net change” summaries (no principal/interest split).
   - Tangible: value chart + filtered ledger + a “set valuation” action that creates a `balance_adjustment` transaction.
   - Investment: reuse existing investment-specific content, but wrap it in the same account detail chrome (breadcrumb/header/actions) and ensure the holdings verification integrity action is discoverable/bookmarkable.

This plan requires new backend read endpoints for (a) per-account details (type-specific aside fields), (b) per-account transactions, and (c) per-account balance history points to power the chart.

## Interfaces and Dependencies

### New backend endpoints (budgeting router)

Add to `src/dojo/budgeting/routers.py`.

1) Per-account details (read-only)

Endpoint:

- `GET /api/accounts/{account_id}`

Response model:

- New Pydantic model `AccountDetailResponse` to be added to `src/dojo/budgeting/schemas.py`.

  Proposed shape:

  - Base account fields: `account_id`, `name`, `account_type`, `account_class`, `account_role`, `current_balance_minor`, `currency`, `institution_name`, `opened_on`, `is_active`.
  - `details`: class-specific object (or `null`) sourced from the appropriate `*_account_details` table, e.g.:

    - cash: `interest_rate_apy`
    - accessible: `interest_rate_apy`, `term_end_date`, `early_withdrawal_penalty`
    - credit: `apr`, `card_type`, `cash_advance_apr`
    - loan: `interest_rate_apy`, `initial_principal_minor`, `mortgage_escrow_details`
    - tangible: `asset_name`, `acquisition_cost_minor`
    - investment: `risk_free_sweep_rate`, `is_self_directed`, `tax_classification` (used for metadata display; portfolio metrics still come from investments APIs)

Behavior:

- Returns the current view (`is_active = TRUE`) of the account and its class-specific details.
- `current_balance_minor` is a signed accounting balance: assets are positive, liabilities are negative (UI may render `owed_minor = -current_balance_minor` for liabilities).
- `current_balance_minor` reflects the current ledger view including `pending` + `cleared` (label as “Current (incl pending)”).
- Balance source-of-truth is the ledger: `accounts.current_balance_minor` is treated as a cached derived value that must match the sum of active ledger transactions.
  - Initial balances are represented via an `opening_balance` transaction (existing SPA behavior), not by directly setting `current_balance_minor`.
  - Manual balance changes are represented via `balance_adjustment` transactions (explicitly non-cash), not by mutating `current_balance_minor` via account update.
- This endpoint exists so the account detail page aside can render real data (APR/term/etc) without faking values.

2) Per-account transactions (read-only)

Endpoint:

- `GET /api/accounts/{account_id}/transactions`

Query params:

- `start_date` (optional, YYYY-MM-DD)
- `end_date` (optional, YYYY-MM-DD)
- `limit` (optional, default 500, capped)
- `status` (optional, one of `all` or `cleared`; default `all`)

Response model:

- `list[dojo.budgeting.schemas.TransactionListItem]`

Behavior:

- Returns only active (`is_active = TRUE`) transaction versions for the given account id.
- `status` filtering:
  - `status=all` (default) includes both `status="pending"` and `status="cleared"` rows.
  - `status=cleared` returns only `status="cleared"` rows (used for cleared-only views; statement context additionally applies a statement cutoff date).
- Orders results in a stable, UI-friendly way (recommend: `transaction_date DESC, recorded_at DESC`).
- If `start_date/end_date` are provided, filter by `transaction_date BETWEEN start_date AND end_date`.

3) Per-account balance history (read-only)

Endpoint:

- `GET /api/accounts/{account_id}/history`

Query params:

- `start_date` (required, YYYY-MM-DD)
- `end_date` (required, YYYY-MM-DD)
- `status` (optional, one of `all` or `cleared`; default `all`)

Response model:

- New Pydantic model `AccountHistoryPoint` to be added to `src/dojo/budgeting/schemas.py`:
  - `as_of_date: date` (end-of-day balance as-of this date)
  - `balance_minor: int` (signed ledger balance)

Behavior:

- Returns one point per day in the inclusive date range.
- `status` filtering:
  - `status=all` (default) includes both `status="pending"` and `status="cleared"` transactions to match `accounts.current_balance_minor` (“Current (incl pending)” UX parity).
  - `status=cleared` includes only `status="cleared"` transactions (used for cleared-only views; statement context additionally applies a statement cutoff date).
- `balance_minor` is a signed accounting balance consistent with `current_balance_minor` (assets positive, liabilities negative; UI may render owed as `-balance_minor`).
- Uses only active transaction versions (`is_active = TRUE`).
  - Time-travel note: because this is the “current view” of the ledger, later edits to a transaction will rewrite prior history points; this endpoint is not audit-grade “as-recorded” history.
- The daily balance is an absolute balance series computed from ledger transactions:
  - `baseline_minor = SUM(amount_minor)` for this account where `transaction_date < start_date`, applying the requested `status` filter (active rows only).
  - `balance_minor(as_of_date) = baseline_minor + SUM(daily_flow_minor) OVER (ORDER BY as_of_date)` within `[start_date, end_date]`.
  - `opening_balance` and `balance_adjustment` are system categories (see `src/dojo/sql/migrations/0009_system_categories.sql`) and are treated as ordinary transactions (no special-casing).
- Invariant: when `end_date = today` and `status=all`, the last history point equals `accounts.current_balance_minor`.
- Guardrail: reject ranges longer than `MAX_ACCOUNT_HISTORY_DAYS` (recommend 3650) with a 400 error so the SPA can cap “Max” safely.

Chart compatibility note:

Keep the budgeting API semantically clean. In the frontend, map `{ as_of_date, balance_minor }` into whatever shape the chart component expects (or generalize `PortfolioChart.vue` to accept field names/value accessors). Avoid returning `market_date`/`nav_minor` aliases from this endpoint.

### Frontend routing

Update `src/dojo/frontend/vite/src/router.js`.

Add canonical routes for account detail + modes:

- `path: "/accounts/:accountId"`
- `component: AccountDetailPage` (new)

- `path: "/accounts/:accountId/reconcile"`
- `component: AccountDetailPage` (or a thin wrapper route) that opens ledger statement reconciliation UI (cash/credit/accessible/loan only; other account classes redirect back to `/accounts/:accountId`).
  - Query params (optional):
    - `statementMonth=YYYY-MM` (preselect statement month; reconciliation workflow details live in `docs/plans/reconciliation-feature.md`)

- `path: "/accounts/:accountId/verify-holdings"`
- `component: AccountDetailPage` (or a thin wrapper route) that opens holdings/cash verification UI (investment accounts only; non-investments redirect back to `/accounts/:accountId`).

- `path: "/accounts/:accountId/valuation"`
- `component: AccountDetailPage` (or a thin wrapper route) that opens valuation update UI (tangible accounts only; non-tangibles redirect back to `/accounts/:accountId`).
  - Query params (optional):
    - `asOf=YYYY-MM-DD` (valuation as-of date)

Keep `/investments/:accountId` as a backwards-compatible alias:

- `path: "/investments/:accountId"`
- redirect to `/accounts/:accountId`

Canonical URL semantics:

- All in-app navigation (account cards, breadcrumbs, links) points to `/accounts/:accountId`.
- Range is controlled via `?range=` and is preserved when entering/leaving `/reconcile`, `/verify-holdings`, or `/valuation`.
- Integrity-action state is encoded in the route so deep links/back/forward are predictable.

### Frontend API client

Update `src/dojo/frontend/vite/src/services/api.js` to add:

- `api.accounts.get(accountId)` (single-account detail payload; includes class-specific fields for the aside)
- `api.accounts.getTransactions(accountId, { start_date, end_date, limit, status })`
- `api.accounts.getHistory(accountId, start_date, end_date, status)`

### Ledger reuse (avoid semantic drift)

Do not add table-side filtering tied to `lockedAccountId`.

- Account detail pages should call the per-account endpoint (`GET /api/accounts/{account_id}/transactions`) so `TransactionTable.vue` receives already-filtered rows.
- Keep `lockedAccountId` semantics focused on transaction entry/editing (prefill + lock the account selector), not “filter”.
  - If table-side filtering is ever needed later, introduce an explicit prop like `accountIdFilter` instead of overloading `lockedAccountId`.

### Frontend query + range conventions (avoid drift)

Query keys (TanStack Query):

- Use hierarchical keys so existing invalidations keep account pages fresh.
- Recommended key scheme:

  - Account detail: `queryKey: ["accounts", accountId]`
  - Account transactions: `queryKey: ["accounts", accountId, "transactions", start_date, end_date, limit, status]`
  - Account history: `queryKey: ["accounts", accountId, "history", start_date, end_date, status]`

Because ledger mutations already invalidate `"accounts"` (see `src/dojo/frontend/vite/src/services/api.js`), these keys ensure account detail pages refetch after create/update/delete.

Chart range selection + Back button semantics:

- Store the selected range label in the URL query (`?range=1M`) so the page is shareable and refresh restores the selection.
- Use `router.replace(...)` for range toggles so users don’t “time travel” chart tabs when pressing Back.
- Use `router.push(...)` when entering `/reconcile`, `/verify-holdings`, or `/valuation` so Back predictably exits the mode.
- Introduce a shared composable/utility (e.g. `useChartRange()` + `resolveRangeFromLabel()` in `src/dojo/frontend/vite/src/utils/chartRange.js`) used by both `InvestmentAccountPage.vue` and `AccountDetailPage.vue`.
  - This avoids copy/paste drift in the “1M/YTD/Max” logic.
- Prefer composables for query wiring (e.g., `useAccountHistoryQuery(accountId, range)`), so query keys/options stay consistent across pages.

### UX/IA Addendum (page shell + deep links)

Page shell (consistent across all account classes):

- Persistent top bar (survives scroll):
  - Breadcrumb: `Accounts > {Account Name}`
  - Subtitle: `{Account class} · {Institution}` (institution may be blank)
  - Right side: current value labeled “Current (incl pending)” (Balance/Owed/Value) with an “as of” note if known
    - In ledger statement reconcile mode (`/accounts/:accountId/reconcile`), surface statement-context values per `docs/plans/reconciliation-feature.md` (avoid calling it “Statement” until a statement date is chosen)
- Primary action slot (one): account-type integrity action
  - Ledger accounts (cash/credit/accessible/loan): `Reconcile statement`
  - Investments: `Verify holdings` (holdings/cash)
  - Tangibles: `Update valuation`
- Secondary actions (quieter): `Add transaction` (where applicable), `Export`, `Edit account` (metadata only; balance changes are ledger events)
- Main column order: chart → summary strip (delta over range; cleared vs pending where relevant) → transactions table
- Aside: account metadata (APR/term/etc) + last reconciliation / last valuation stamp

Mode routing (bookmarkable “rooms”, even if UI remains modal in v1):

- Ledger reconcile mode (`/accounts/:accountId/reconcile`) is entered via route navigation and exited by navigating back to `/accounts/:accountId`.
  - Applies to ledger accounts only (cash/credit/accessible/loan).
  - Reconciliation workflow semantics and labeling live in `docs/plans/reconciliation-feature.md`.

- Investment holdings verification mode (`/accounts/:accountId/verify-holdings`) is entered via route navigation and exited by navigating back to `/accounts/:accountId`.
  - Applies to investment accounts only.

- Tangible valuation mode (`/accounts/:accountId/valuation`) is entered via route navigation and exited by navigating back to `/accounts/:accountId`.
  - Applies to tangible accounts only.

Deep link standard (hash router examples):

- Account detail: `/#/accounts/:accountId?range=1M`
- Ledger reconcile mode: `/#/accounts/:accountId/reconcile?range=1M&statementMonth=YYYY-MM`
- Investment holdings verification mode: `/#/accounts/:accountId/verify-holdings?range=1M`
- Tangible valuation mode: `/#/accounts/:accountId/valuation?range=1M&asOf=YYYY-MM-DD`

Suggested user flow:

```mermaid
flowchart TD
  A[Accounts list /#/accounts] -->|Click account card| B[Account detail /#/accounts/:id?range=1M]
  B -->|Change range (replace URL)| B
  B -->|Primary CTA: Reconcile statement| C[/#/accounts/:id/reconcile?range=1M&statementMonth=YYYY-MM]
  C -->|Complete| B
  C -->|Cancel/Back| B
  B -->|Primary CTA: Verify holdings (investment)| E[/#/accounts/:id/verify-holdings?range=1M]
  E -->|Done/Back| B
  B -->|Primary CTA: Update valuation (tangible)| D[/#/accounts/:id/valuation?range=1M&asOf=YYYY-MM-DD]
  D -->|Save valuation| B
```

Ledger table hygiene requirements (global ledger and account ledgers must match):

- Amounts are right-aligned and outflow/inflow semantics are consistent.
- Pending vs cleared status is visibly scannable.
- Clicking a transaction row behaves the same everywhere.
- Table header remains visible while scrolling long ledgers (sticky header or equivalent).
- Liability semantics are consistent across header value, chart tooltip, delta label, and table styling.

## Milestones

### Milestone 1: Backend read APIs for account detail pages

At the end of this milestone, the backend can return (a) per-account details (including class-specific fields for the aside), (b) the ledger transactions for a single account, and (c) a daily balance time series for a single account suitable for charting.

Work:

- Add SQL files under `src/dojo/sql/budgeting/`:

  - `select_account_detail_with_details.sql`:
    - selects base account fields
    - joins the active row from the appropriate `*_account_details` table to supply class-specific fields for the aside

  - `select_account_transactions.sql`:
    - filters by `account_id`
    - filters by optional date range
    - filters by optional `status` (`all|cleared`)
    - returns the columns needed for `TransactionListItem` (matching `select_recent_transactions.sql` shape)

  - `select_account_balance_history.sql`:
    - uses `GENERATE_SERIES(start_date, end_date, INTERVAL 1 DAY)` to create daily rows
    - computes an absolute daily balance series using `baseline_minor` + cumulative sum of daily net flows

  Implementation guidance for `select_account_balance_history.sql`:

  - Use an absolute-balance approach with a baseline term (correctness) and daily flows (performance):

    1. `baseline`: compute `baseline_minor = SUM(amount_minor)` where `transaction_date < start_date` for this account, applying the same `status` filter as the request (active rows only).
    2. `flows_by_day`: sum `amount_minor` for each `transaction_date` in `[start_date, end_date]` for this account, applying the same `status` filter as the request (active rows only).
    3. Left join the daily series to `flows_by_day` and compute `balance_minor = baseline_minor + SUM(flow_minor) OVER (ORDER BY as_of_date)`.

  This produces a correct absolute balance series without doing “sum all tx up to date” for every day.

  - If this query becomes hard to reason about, an alternative is the “as-of join” pattern used in `src/dojo/sql/investments/portfolio_history.sql`, but it’s potentially slower and should be justified with realistic row counts.

- Add DAO helpers in `src/dojo/budgeting/dao.py` to execute these SQL files.

- Add router endpoints in `src/dojo/budgeting/routers.py`:

  - `GET /accounts/{account_id}`
  - `GET /accounts/{account_id}/transactions`
  - `GET /accounts/{account_id}/history`

- Enforce balance continuity:

  - `accounts.current_balance_minor` must remain ledger-derived; do not allow arbitrary overrides via account update.
  - Reject non-zero `current_balance_minor` in `POST/PUT /api/accounts` payloads; require balance changes to be expressed as ledger events.
  - Any non-zero starting balance must be represented by an `opening_balance` ledger event.
  - Any later manual correction must be represented by a `balance_adjustment` ledger event (explicitly non-cash).

- Add Pydantic model(s) in `src/dojo/budgeting/schemas.py`:

  - `AccountDetailResponse` (and per-class detail models)
  - `AccountHistoryPoint`

- Add integration tests (recommend new file):

  - `tests/integration/account_details/test_account_details_api.py`

  Test cases (invariants):

  - account detail endpoint returns base fields + class-specific `details` (APR/term/etc) for representative accounts
  - account balances are signed at the API boundary (assets positive, liabilities negative)
  - transactions endpoint returns only one account’s transactions
  - transactions endpoint supports `status=all|cleared` and filters correctly
  - history endpoint returns one point per day
  - history endpoint supports `status=all|cleared` and filters correctly
  - history is an absolute series (includes baseline before `start_date`, e.g. `opening_balance`)
  - for a range ending “today” with `status=all`, the last history point equals `accounts.current_balance_minor` (balance continuity)
  - liability accounts return negative balances in `balance_minor` (UI displays owed via transform)
  - tangible `balance_adjustment` changes the tangible value but does not change `ready_to_assign`
  - a transfer-driven “payment” reduces the liability and reduces the funding asset (net worth unchanged)

Proof:

- Run (from repo root, inside nix dev shell):

  - `scripts/run-tests --filter integration:account_details`

  If filters aren’t supported, run the smallest available subset or `scripts/run-tests --skip-e2e`.

### Milestone 2: Frontend navigation change (remove modal; route to pages)

At the end of this milestone, `/#/accounts` has no account detail modal; clicking a card navigates to the correct detail page.

Work:

- Update `src/dojo/frontend/vite/src/pages/AccountsPage.vue`:

  - Remove the `modalView === 'detail'` path and the click handler that opens it.
  - Keep the “Add account” wizard modal behavior unchanged.
  - Change card click behavior:

    - Navigate to `/accounts/:accountId` for all account cards (canonical detail URL).

  - Remove the in-modal reconcile button (since the modal no longer exists).

Proof:

- Start the app locally:

  - `uvicorn dojo.core.app:create_app --factory --reload`

- Navigate in browser to the SPA and confirm:

  - Clicking an account card opens a new page route (no modal).
  - “Add account” still works (wizard modal unchanged).

### Milestone 3: Implement account detail pages (shared shell + type modules)

At the end of this milestone, every account class has a working `/accounts/:accountId` detail view.

- Non-investment accounts: chart + filtered ledger + aside details, reusing the same ledger components as the global ledger.
- Investment accounts: reuse the existing investment detail implementation, but align range/query conventions so the URL, chart interaction, and caching strategy are consistent.

Work:

- Add new page `src/dojo/frontend/vite/src/pages/AccountDetailPage.vue`:

  - Route param: `accountId`.
  - URL query param: `range` (e.g., `?range=1M`, default `1M`). Use shared range resolution logic so all detail pages behave consistently.
  - Fetch required data:

    - reference data (`api.reference.load`) for accounts + categories (dropdowns + names)
    - account detail (`api.accounts.get(accountId)`) for aside fields and current balance
    - latest reconciliation (`api.reconciliations.getLatest(accountId)`) for ledger accounts (for “last reconciled” reassurance + default statement month)
    - account transactions (`api.accounts.getTransactions(accountId, ...)`) (already filtered; default `status=all`; use `status=cleared` only for cleared-only/statement context)
    - account history (`api.accounts.getHistory(accountId, start_date, end_date, status)`) (date range derived from `?range=`; default `status=all`; use `status=cleared` only for cleared-only/statement context)

  - Implement consistent page chrome (all classes, including investments):

    - persistent header with breadcrumb, account name, class + institution subtitle, and current value
    - primary action slot + secondary actions slot
    - main column with chart + ledger table
    - aside column with details

  - Breadcrumb includes an “Accounts” link (replaces a standalone “Back” button).

- Refactor investment detail page code to share range/query conventions:

  - Update `src/dojo/frontend/vite/src/pages/InvestmentAccountPage.vue` (or extract an `InvestmentAccountDetail.vue` component) so range is driven from `?range=` via the shared range composable.
  - Map investment history points into the normalized chart `series` contract and enable percent change labeling for investments.

- Chart component strategy:

  - Refactor `src/dojo/frontend/vite/src/components/investments/PortfolioChart.vue` into a generic time-series chart with an explicit contract:

    - Geometry uses a normalized `series: Array<{ date: string, value_minor: number }>`.
    - Tooltip + summary labels use the same normalized `value_minor` series (no hidden signed series in the chart component).
    - Theme coloring is controlled by an explicit flag (e.g., `increaseIsGood`).
    - Percent change label is optional (show for investments; hide for balance/owed charts).

  - Normalization rules in the page layer:

    - Asset accounts (cash, accessible, tangible): `value_minor = balance_minor`.
    - Liability accounts (credit, loan): `value_minor = -balance_minor` (display “owed” as positive).
      - Delta label is “owed change” (so paying down debt yields a negative delta).
      - Set `increaseIsGood = false` so *decreasing owed* uses the “up/success” styling.

  - Keep styling aligned with `src/dojo/frontend/static/styles/components/investments.css`.

- Filtered ledger:

  - For asset-like accounts (`cash`, `accessible`, `tangible`), render `TransactionForm.vue` with the account locked so users can add/edit transactions quickly.

  - For liability accounts (`credit`, `loan`), avoid the single-leg “payment” footgun:

    - Provide a `Record payment` action that uses the existing transfer flow (`POST /api/transfers`) so payments are always two-leg (asset down + liability down; net worth unchanged).
    - Provide a separate `Add charge/fee` action (single-leg) for liability increases.
    - Any liability reduction that is not a transfer must be explicitly labeled (e.g., refund/credit or `balance_adjustment` non-cash adjustment).

  - Render `TransactionTable.vue` with transactions from the per-account endpoint (already filtered). Pass `lockedAccountId`/`lockedAccountName` so inline edits cannot switch accounts.


Per-type content requirements (minimum viable v1):

- Cash (`cash`):

  - User jobs:
    - “What changed recently?”
    - “Can I add/edit transactions quickly?”
  - Chart: ledger balance over time.
  - Aside: role, institution (if available), current balance, last reconciled (if available).
  - Ledger: full transaction list filtered to the account.

- Accessible assets (`accessible`):

  - User jobs:
    - “What’s the current balance?”
    - “When does it mature / what are the terms?”
  - Chart: ledger balance over time.
  - Aside: term end date, early withdrawal penalty, interest rate (from account details endpoint), last reconciled (if available).
  - Ledger: transactions filtered to the account.

- Credit (`credit`):

  - User jobs:
    - “How much do I owe right now?”
    - “What’s pending vs cleared?”
    - “Reconcile my statement.”
    - “Record a payment without breaking net worth.”
  - Chart: owed over time (display owed as positive).
  - Summary strip: cleared vs pending totals for the selected range (derived from transaction `status`).
  - Actions:
    - `Record payment` uses the transfer flow (two-leg; funding account required; net worth unchanged).
    - `Add charge/fee` is a single-leg outflow on the credit account.
  - Aside: APR, card type/network, cash advance APR (from account details endpoint), last reconciled (if available).
  - Ledger: transactions filtered to the account (status is visible/scannable; UI labels “pending” vs “cleared”).

- Loan (`loan`):

  - User jobs:
    - “Did my payment post?”
    - “Is the owed balance trending down?”
  - Chart: owed over time (display owed as positive).
  - Actions:
    - `Record payment` uses the transfer flow (two-leg; funding account required; net worth unchanged).
    - `Add charge/fee` is a single-leg outflow on the loan account (interest/fees/etc).
  - Aside: interest rate, original principal (from account details endpoint), last reconciled (if available).
  - Ledger: transactions filtered to the account.
  - Summary widgets (avoid ambiguous “payment” terminology):

    - Net change over interval: end minus start (interpreted as “owed change”).
    - Owed reductions (inflows): sum of positive `amount_minor` on the loan account over the interval.
    - Owed increases (outflows): sum of absolute negative `amount_minor` on the loan account over the interval.

  Note: Do not attempt principal-vs-interest breakdown in v1.

- Tangible (`tangible`):

  - User jobs:
    - “What is it worth now?”
    - “When did I last update valuation?”
  - Chart: value over time (ledger balance).
  - Aside: asset name, acquisition cost basis (from account details endpoint), current value, last valuation update (most recent `balance_adjustment`).
  - Ledger: transactions filtered to the account including `balance_adjustment` entries.
    - Guardrail: `balance_adjustment` is a system category and must be labeled as a non-cash valuation event; it does not affect budgeting / `ready_to_assign`.


- Investment (`investment`):

  - User jobs:
    - “What’s my NAV / performance?”
    - “What holdings do I own?”
    - “Reconcile holdings/cash.”
  - Chart: NAV over time (percent change enabled).
  - Main content: reuse the existing investment-specific UI (holdings table + cash reconcile).
  - Aside: portfolio summary + investment account metadata (where available).

Proof:

- Manual:

  - Navigate to at least one account of each class from `/#/accounts`.
  - Confirm the persistent header clearly identifies the account (breadcrumb + name + class + institution) and remains visible enough to avoid “where am I?” confusion.
  - Confirm chart loads and updates with time range selection, and the selection is reflected in the URL (`?range=`) so refresh/back/forward preserves it.
  - Change range multiple times and confirm Back does not step through range changes (range toggles use replace).
  - Confirm liabilities display “owed” as a positive chart/value and the delta label matches the owed mental model.
  - Confirm the aside renders class-specific details (APR/term/etc) from `GET /api/accounts/{account_id}`.
  - Confirm ledger table only shows transactions for the current account.
  - Confirm editing a transaction in the detail page behaves identically to the global ledger.

### Milestone 4: Integrity actions on every detail page (minimal, type-aware)

At the end of this milestone, every detail page has a visible, account-type-appropriate integrity action that is functional and bookmarkable (route-driven).

Work:

- For cash/credit/accessible/loan detail pages (ledger statement reconciliation):

  - Primary CTA “Reconcile statement” navigates to `/accounts/:accountId/reconcile` (preserving `?range=`).
  - The UI may still use `src/dojo/frontend/vite/src/components/ReconciliationModal.vue` in v1, but it must be route-driven:

    - entering `/accounts/:accountId/reconcile` opens the reconcile UI
    - closing/canceling navigates back to `/accounts/:accountId` (so Back exits reconcile mode predictably)

  - Reconciliation worksheet semantics (pending + new/modified), statement cutoffs, and draft persistence are defined in `docs/plans/reconciliation-feature.md`.

- For investment detail page (holdings verification):

  - Primary CTA “Verify holdings” navigates to `/accounts/:accountId/verify-holdings`.
  - This focuses the existing holdings/cash verification UI; avoid labeling it “statement reconcile”.

- For tangibles:

  - Primary CTA “Update valuation” navigates to `/accounts/:accountId/valuation`.
  - The valuation UI may be a modal in v1, but it must be route-driven like reconcile.

  This should create a `balance_adjustment` transaction (`category_id="balance_adjustment"` system category) representing the delta needed to reach a user-entered target value as-of a date.

  Keep it explicit in the UI copy that this is a valuation update event (not a bank statement reconcile) and that it is non-cash (does not affect budgeting / `ready_to_assign`).

Document how these integrity actions relate to other plans:

- Ledger statement reconciliation is defined in `docs/plans/reconciliation-feature.md`.
- Investment holdings verification is investment-specific and already implemented separately.
- Tangible valuation updates are modeled as `balance_adjustment` events (non-cash).

Proof:

- Manual verification on each account type:

  - Enter ledger reconcile via `/accounts/:accountId/reconcile` and confirm a working flow opens; Back/close returns to `/accounts/:accountId` predictably.
  - Enter investment holdings verification via `/accounts/:accountId/verify-holdings` and confirm the UI opens; Back/close returns to `/accounts/:accountId`.
  - For tangibles, enter `/accounts/:accountId/valuation` and confirm Back/close returns to `/accounts/:accountId`.
  - Confirm integrity-mode URLs are bookmarkable (refresh preserves the mode).
  - Confirm tangible “Update valuation” produces a visible ledger event and updates the chart.

## Concrete Steps

All commands are run from the repository root, inside the Nix dev shell.

1) Enter dev shell (if not already):

  nix develop

2) Run focused tests while iterating:

  scripts/run-tests --filter integration:account_details

  If filters aren’t supported: scripts/run-tests --skip-e2e

3) Start the app for manual checks:

  uvicorn dojo.core.app:create_app --factory --reload

4) Manual acceptance walkthrough:

- Open `/#/accounts`.
- Click a cash account: verify route to `/#/accounts/:accountId`, persistent header (breadcrumb + subtitle), and chart/table load.
- Change chart range: verify `?range=` updates via replace (Back does not step through tab clicks).
- Enter ledger reconcile mode: verify route `/#/accounts/:accountId/reconcile` opens the reconciliation UI; Back/close returns to detail.
- For a tangible account: enter `/#/accounts/:accountId/valuation` and confirm Back/close returns and saving creates a `balance_adjustment` event.
- On a credit/loan account: verify `Record payment` uses the transfer flow and requires a funding account; verify it reduces owed and reduces the funding asset (net worth unchanged).
- On an investment account: enter `/#/accounts/:accountId/verify-holdings` and confirm the holdings verification UI is reachable; Back returns to the detail page.
- Repeat basic checks for accessible.

## Validation and Acceptance

Acceptance criteria (human-verifiable):

- From `/#/accounts`, clicking an account card navigates to `/#/accounts/:accountId`; no account detail modal appears.
- Every account detail page uses the same page chrome (breadcrumb, title, subtitle, current value, primary/secondary action slots), including investments.
- Chart range selection is shareable via URL query (`?range=`), updates via `router.replace` (no Back-stack spam), and is preserved across refresh/back/forward.
- Integrity action states are bookmarkable URLs (`/#/accounts/:accountId/reconcile`, `/#/accounts/:accountId/verify-holdings`, `/#/accounts/:accountId/valuation`); Back/close exits the mode predictably.
- The header value is explicitly labeled “Current (incl pending)”. Ledger reconcile mode uses reconciliation-feature labeling (avoid “Statement” until a statement date is chosen).
- Each account detail page shows:

  - A chart for that account with the same interaction model as the investment chart (hover tooltip + interval selection).
  - An aside panel with class-specific details (APR/term/etc) sourced from `GET /api/accounts/{account_id}`.
  - A ledger table filtered to that account (by calling the per-account transactions endpoint).

- Clicking a transaction row behaves the same everywhere (global ledger vs account ledger).
- Liability semantics are consistent across header value, chart tooltip, delta label, and table styling (owed displayed as positive; “good direction” consistent).
- Balance continuity: for a range ending “today” with `status=all`, the last history point matches the header “Current (incl pending)” value.
- Asset-like accounts use the same `TransactionForm.vue` component for single-leg ledger entry; credit/loan pages split `Add charge/fee` (single-leg) from `Record payment` (transfer) to prevent “free net worth” liability reductions.
- Each detail page has an account-type integrity action entry point:

  - Ledger accounts: `/accounts/:accountId/reconcile` opens the existing ledger reconciliation wizard (see `docs/plans/reconciliation-feature.md` for worksheet semantics and completion rules).
  - Investments: `/accounts/:accountId/verify-holdings` opens holdings/cash verification UI.
  - Tangibles: `/accounts/:accountId/valuation` creates a `balance_adjustment` event (non-cash; system category), updates the chart, and does not change budgeting / `ready_to_assign`.

Automated validation:

- New integration tests for `/api/accounts/{id}`, `/api/accounts/{id}/transactions`, and `/api/accounts/{id}/history` pass.
- Existing integration tests for reconciliation and investments continue to pass.

## Idempotence and Recovery

- All new SQL files are read-only queries; they are safe to run repeatedly.
- No migrations are required for the core “detail pages” work, so rollback is code-only.
- If performance issues appear in history queries:

  - Reduce the frontend default range for “Max” and/or lower `MAX_ACCOUNT_HISTORY_DAYS`, and log the decision in this plan.

- If a balance cache mismatch is detected (last history point != `accounts.current_balance_minor`):

  - Treat it as data integrity drift and run `scripts/rebuild-caches` (or equivalent) to recompute cached balances from the ledger before trusting charts.

## Artifacts and Notes

Key existing artifacts being reused:

- Investment chart styling and layout:

  - `src/dojo/frontend/vite/src/components/investments/PortfolioChart.vue`
  - `src/dojo/frontend/static/styles/components/investments.css`

- Ledger UI components (must be reused to ensure UI changes propagate):

  - `src/dojo/frontend/vite/src/components/TransactionForm.vue`
  - `src/dojo/frontend/vite/src/components/TransactionTable.vue`

- Existing reconciliation wizard:

  - `src/dojo/frontend/vite/src/components/ReconciliationModal.vue`
  - `src/dojo/core/reconciliation_router.py`
  - `docs/plans/reconciliation-feature.md`

Change note (required for living ExecPlans):

- 2026-01-08: Initial plan drafted from brainstorming session. Clarified that integrity actions belong on detail pages (not account cards) and that loan principal/interest breakdown is out of scope for v1 to preserve ledger truth.
- 2026-01-09: Incorporated expert review feedback: absolute-balance history with baseline, status-filtered history/transactions for cleared-only views, canonical `/accounts/:id` routes with URL-driven modes, explicit sign conventions, ledger-derived balance continuity, and liability-safe payment entry via transfers.
- 2026-01-09: Implemented Milestone 1 backend read APIs (`/api/accounts/{id}`, `/transactions`, `/history`), enforced `current_balance_minor` guardrails on account create/update, and added integration tests for the new endpoints.
