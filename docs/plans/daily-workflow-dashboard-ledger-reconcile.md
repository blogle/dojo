# Daily Workflow UX: Dashboard → Transactions Entry → Reconcile

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Maintain this plan in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Dojo’s highest-frequency workflow is manual, account-by-account transaction entry followed by reconciliation against bank figures. The goal of this plan is to make that workflow feel fast, obvious, forgiving, and trustworthy.

After this plan lands, a user can:

- Open the app at `/#/` and immediately see net worth trend and “what needs attention” (accounts).
- Click into an account and enter a run of transactions quickly without retyping date/account repeatedly.
- Reconcile using clear, non-ambiguous labels (“Cleared balance” and “Pending total”) and tools that shorten “find the delta” investigations.

This plan is coordinated with the following beads issues:

- `dojo-d5j` (P0) — UX-018: Transactions fast-entry composer + keyboard-first contract
- `dojo-cdu` (P1) — UX-019: Reconciliation delta-finding improvements (cash/credit)
- `dojo-2zp` (P2) — UX-020: Net Worth Dashboard MVP as landing page
- `dojo-ygs` (P3) — UX-021: Reconcile session framework (extensible account types)

And it must remain compatible with (and ideally reuse) existing UX/platform work:

- `dojo-pjb.7` (P0) — UX-008: Standardize confirm/undo + auditability for high-stakes actions
- `dojo-pjb.5` (P2) — UX-006: Make TransactionTable editing explicit + safer delete
- `dojo-pjb.9` (P2) — UX-010: Close accessibility + keyboard interaction gaps
- `dojo-pjb.12` (P2) — UX-013: Explainability for credit payments + transfers-as-spending
- `dojo-pjb.11` (P4) — UX-012: Align terminology (Ready to Assign, groups, envelopes/categories)

## Progress

- [x] (2026-01-11) Created beads issues for this UX direction (`dojo-d5j`, `dojo-cdu`, `dojo-2zp`, `dojo-ygs`).
- [x] (2026-01-11) Recorded UX decisions (signed entry, In/Out columns, cleared/pending terminology) in this ExecPlan.
- [ ] Implement `/#/` Dashboard route and basic page skeleton (`dojo-2zp`).
- [ ] Add backend endpoint for net worth history and wire to frontend (`dojo-2zp`).
- [ ] Implement dashboard chart interactions (hover + drag-to-measure) and interval toggles (`dojo-2zp`).
- [ ] Implement Transactions fast-entry contract (signed amount input, carry-forward defaults, keyboard focus rules) (`dojo-d5j`).
- [ ] Remove per-row action buttons from transaction rows; replace with selection toolbar/inspector (keyboard accessible) (`dojo-d5j`, aligns with `dojo-pjb.5`).
- [ ] Improve reconciliation delta-finding helpers and rename labels to cleared/pending (`dojo-cdu`).
- [ ] Run `scripts/run-tests` with appropriate filters; ensure Cypress user stories remain stable.

## Surprises & Discoveries

- Observation: The SPA uses hash routing (`createWebHashHistory`) and currently redirects `/#/` to `/#/transactions`.
  Evidence: `src/dojo/frontend/vite/src/router.js`.

- Observation: The current transactions input uses an unsigned amount + Inflow/Outflow radio toggle, while the ledger display is already split into Outflow and Inflow columns.
  Evidence: `src/dojo/frontend/vite/src/components/TransactionForm.vue`, `src/dojo/frontend/vite/src/components/TransactionTable.vue`.

- Observation: Reconciliation already models “settled + pending = total” and shows three differences, but the “commit” stores only `statement_balance_minor` (the settled value).
  Evidence: `src/dojo/frontend/vite/src/components/ReconciliationModal.vue` (payload uses `statement_balance_minor: statementSettledMinor`).

## Decision Log

- Decision: The landing page should be a net worth dashboard shown at `/#/`.
  Rationale: The dashboard is the “read-mostly” daily check; it should be the first thing seen on entry, with fast deep links into entry/reconcile work.
  Date/Author: 2026-01-11 / user + agent.

- Decision: Use signed amount entry in the transaction composer, while retaining separate Outflow/Inflow columns in the ledger grid.
  Rationale: Signed entry reduces the extra tab stop and “forgot to toggle flow” errors, while the split columns keep the ledger scannable and familiar.
  Date/Author: 2026-01-11 / user + agent.

- Decision: Do not mix up terms: “Account” is the entity; “Assets & Liabilities” is a page/view.
  Rationale: The same account can be viewed on multiple pages; naming needs to remain stable to avoid confusion.
  Date/Author: 2026-01-11 / user + agent.

- Decision: In reconciliation UI, use “Cleared balance” and “Pending total” as the primary labels (avoid “current”, avoid ambiguous “settled”).
  Rationale: Users reconcile against bank-provided cleared + pending figures; the UI must match that mental model.
  Date/Author: 2026-01-11 / user + agent.

- Decision: Avoid repeating row-level buttons (save/cancel/delete) on every ledger row.
  Rationale: Row chrome creates noise and slows scanning; actions should appear for the selected row(s) in one consistent place and remain keyboard accessible.
  Date/Author: 2026-01-11 / user + agent.

- Decision (tentative; confirm during implementation): Default new manual transactions to `cleared`, and allow fast toggle to `pending` for the last few items.
  Rationale: The entry workflow is oldest→newest; most items are cleared, and pending items are entered last.
  Date/Author: 2026-01-11 / agent (pending confirmation).

## Outcomes & Retrospective

To be filled as milestones land. At a minimum, record:

- What got faster (keystrokes/time) for the daily entry workflow.
- Which reconciliation mismatch hunts became simpler (and why).
- Any UX tradeoffs or regressions discovered and how they were mitigated.

## Context and Orientation

This repository’s SPA is a Vue 3 app built with Vite.

Frontend entry points:

- Router: `src/dojo/frontend/vite/src/router.js` (hash router).
- Shell/nav: `src/dojo/frontend/vite/src/App.vue`.
- Transactions page: `src/dojo/frontend/vite/src/pages/TransactionsPage.vue`.
- Transaction input: `src/dojo/frontend/vite/src/components/TransactionForm.vue`.
- Ledger grid: `src/dojo/frontend/vite/src/components/TransactionTable.vue`.
- Reconcile wizard/modal: `src/dojo/frontend/vite/src/components/ReconciliationModal.vue`.
- Assets & Liabilities page: `src/dojo/frontend/vite/src/pages/AccountsPage.vue`.
- Account detail page (route-driven modals for reconcile/verify holdings/valuation): `src/dojo/frontend/vite/src/pages/AccountDetailPage.vue`.

Backend API context:

- Core router contains `GET /api/net-worth/current` in `src/dojo/core/routers.py`.
- Budgeting router contains account history and transactions endpoints (e.g., `GET /api/accounts/{account_id}/history`) in `src/dojo/budgeting/routers.py`.
- Frontend API client lives at `src/dojo/frontend/vite/src/services/api.js`.

Existing SQL patterns worth reusing:

- Account balance history is implemented via date series + baseline + window sum in `src/dojo/sql/budgeting/select_account_balance_history.sql`.
- Investment portfolio history is implemented via SCD2 position joins + ASOF market prices in `src/dojo/sql/investments/portfolio_history.sql`.

Testing conventions:

- Run automated tests via `scripts/run-tests` (see `scripts/README.md`).
- Cypress user stories are in `cypress/e2e/user-stories/`.

## Plan of Work

### Milestone 1: Make the Dashboard the landing page (route + shell)

At the end of this milestone, visiting `/#/` renders a new Dashboard page (even if the chart uses placeholder data initially). The global nav includes a “Dashboard” entry and the DOJO logo returns you to the dashboard.

This work primarily touches:

- `src/dojo/frontend/vite/src/router.js`
- `src/dojo/frontend/vite/src/App.vue`
- New file: `src/dojo/frontend/vite/src/pages/DashboardPage.vue`

Proof:

- Start the app and navigate to `/#/`.
- Confirm the Dashboard page renders and is reachable from the header.

Related tickets: `dojo-2zp`.

### Milestone 2: Net worth history endpoint (backend) + API client (frontend)

At the end of this milestone, the backend provides `GET /api/net-worth/history?interval={interval}` returning an ordered array of points `{ date: YYYY-MM-DD, value_minor: int }`, and the frontend can fetch it.

Design constraints:

- The endpoint must be truthful about what it includes. If the history includes investments and tangibles, compute them consistently; if it cannot yet, the endpoint must either (a) label itself as “cash-only” in the UI, or (b) refuse the request with a clear error until the full computation exists. Do not silently ship misleading net worth charts.

Implementation approach:

- Add a new Pydantic response schema in `src/dojo/core/schemas.py` for history points.
- Add a new DAO/service function in `src/dojo/core/` that generates history points for a requested interval.
- Reuse SQL patterns already present (generate_series, SCD2 joins, ASOF prices) rather than inventing bespoke Python loops.

Frontend:

- Add `api.netWorth.history(interval)` to `src/dojo/frontend/vite/src/services/api.js`.

Proof:

- `curl` the endpoint and verify it returns valid JSON with monotonically increasing dates.

Related tickets: `dojo-2zp`.

### Milestone 3: Dashboard chart interactions (hover + drag-to-measure) and interval toggles

At the end of this milestone, the dashboard matches the interaction spec in `next_up/net_worth_dashboard.md`:

- Interval toggles update the time window.
- Hover shows a tooltip for a point.
- Click-and-drag shows a selected range overlay and computes delta + percent for that selected range.

Proof:

- Manually verify hover + drag interactions feel smooth.
- Add at least one deterministic automated test (backend or frontend unit test) that the interval toggle changes the underlying data request.

Related tickets: `dojo-2zp`.

### Milestone 4: Transactions fast-entry contract (signed entry + carry-forward defaults)

At the end of this milestone, the transactions composer supports fast, repetitive entry:

- The amount input accepts signed values (`-12.34` outflow, `+12.34` inflow).
- The grid still shows separate Outflow/Inflow columns.
- After submit, Date/Account/Status carry forward to the next entry.
- Focus returns to the amount field so the next row can be entered immediately.

Implementation notes:

- Update parsing utilities in `src/dojo/frontend/vite/src/utils/transactions.js` to support signed input directly (while keeping existing flows where needed).
- Ensure liability account restrictions remain sensible (credit payments continue to be recorded via transfers unless/until the design changes).

Proof:

- Enter 5 transactions for the same account/date with only amount/category/memo changes, without re-selecting account/date.

Related tickets: `dojo-d5j`.

### Milestone 5: Remove per-row action chrome; add selection toolbar/inspector (keyboard accessible)

At the end of this milestone:

- Transaction rows do not show per-row Edit/Delete buttons.
- Clicking a row selects it (visible selection state).
- A single toolbar/inspector (outside the grid) exposes actions for the selected row(s) and is keyboard accessible.

This must coordinate with `dojo-pjb.7` (confirm/undo) and `dojo-pjb.5` (explicit edit/delete behavior) rather than fighting them.

Proof:

- Cypress user stories that edit or delete a transaction use toolbar actions (not cell-click/Enter assumptions).

Related tickets: `dojo-d5j`, `dojo-pjb.5`, `dojo-pjb.7`, `dojo-pjb.9`.

### Milestone 6: Reconciliation delta-finder helpers and cleared/pending terminology

At the end of this milestone:

- Reconciliation setup labels read “Cleared balance” and “Pending total”.
- The worksheet shows three differences clearly (cleared, pending, total).
- The worksheet includes helpers to find mismatches quickly (search, status filters, and “amount equals difference”).

Proof:

- In a seeded test scenario where a single transaction is off by $0.01, the UI makes it easy to filter to the culprit.

Related tickets: `dojo-cdu`.

### Milestone 7 (later): Reconcile session framework for non-ledger account types

At the end of this milestone:

- There is a shared reconciliation “shell” UI that hosts different adapters.
- Cash/credit uses the shell.
- Investment positions verification and tangible valuation have renderable stubs in the same shell.

Proof:

- Navigating to the reconcile routes for each type renders a consistent outer UI with type-specific content.

Related tickets: `dojo-ygs`.

## Concrete Steps

Working directory: `/home/ogle/src/dojo`.

1) Run focused frontend unit tests before making large UI changes:

    scripts/run-tests --skip-e2e

2) Implement Milestone 1 (router + dashboard page):

- Edit `src/dojo/frontend/vite/src/router.js` so `path: "/"` renders a new `DashboardPage` instead of redirecting to `/transactions`.
- Add `src/dojo/frontend/vite/src/pages/DashboardPage.vue` with a minimal scaffold and stable selectors.
- Update `src/dojo/frontend/vite/src/App.vue` nav to include “Dashboard”.

3) Implement Milestone 2 (backend + api client):

- Add `GET /api/net-worth/history` to `src/dojo/core/routers.py`.
- Add supporting schema(s) in `src/dojo/core/schemas.py`.
- Add new SQL files under `src/dojo/sql/core/` for net worth history (name explicitly, and keep them small and testable).
- Update `src/dojo/frontend/vite/src/services/api.js` with `api.netWorth.history(interval)`.

4) Implement Milestone 3 (dashboard chart behavior):

- Follow the interaction spec in `next_up/net_worth_dashboard.md`.
- Keep hover/drag work on `requestAnimationFrame` or similarly efficient reactive refs.

5) Implement Milestones 4–5 (transactions fast entry + selection toolbar):

- Update `src/dojo/frontend/vite/src/components/TransactionForm.vue` to accept signed input and to carry forward date/account/status.
- Update `src/dojo/frontend/vite/src/components/TransactionTable.vue` to separate “selection” from “edit mode” and remove per-row actions.
- Update Cypress Page Objects and user stories as required (`cypress/support/pages/TransactionPage.js`, user stories 05/06/14).

6) Implement Milestone 6 (reconcile improvements):

- Update `src/dojo/frontend/vite/src/components/ReconciliationModal.vue` labels and add delta-finder controls with stable selectors.
- Keep commit behavior correct and auditable; coordinate confirm/undo work with `dojo-pjb.7`.

7) Validation:

- Run `scripts/run-tests --skip-e2e` during iteration.
- Before declaring the milestone done, run at least the affected Cypress specs:

    scripts/run-tests --filter e2e:05-manual-transaction-lifecycle
    scripts/run-tests --filter e2e:06-editable-ledger-rows
    scripts/run-tests --filter e2e:14-display-monthly-summary-cards

## Validation and Acceptance

Acceptance is user-observable behavior:

- Dashboard:
  - Navigating to `/#/` renders the dashboard.
  - Interval buttons update the chart range.
  - Hover shows a tooltip; drag-to-measure shows start/end values and delta.

- Transactions:
  - A user can enter multiple transactions for the same account/date by repeatedly typing `amount → category → memo` and pressing Enter, without reselecting account/date.
  - Signed amount entry correctly maps to Outflow/Inflow columns.
  - No per-row action buttons appear in the ledger rows; actions are accessible via selection toolbar/inspector.

- Reconciliation:
  - Setup labels use “Cleared balance” and “Pending total”.
  - Differences are shown for cleared/pending/total.
  - Delta-finder helpers allow narrowing to likely culprit transactions.

- Tests:
  - `scripts/run-tests --skip-e2e` passes.
  - Targeted Cypress specs for transactions pass.

## Idempotence and Recovery

- Routes and UI state should survive refresh/back/forward without ending up in broken intermediary states.
- Where a workflow is multi-step (reconcile), closing/cancel must not corrupt state; it should either discard draft inputs safely or persist a draft explicitly.
- Data integrity remains source-of-truth in the ledger; UI changes must not introduce “hidden deletes” or non-auditable balance changes.

## Artifacts and Notes

As work proceeds, capture short evidence snippets in this plan:

- A sample JSON response from `/api/net-worth/history` for a small interval.
- A short test transcript proving the new endpoint is covered.
- Before/after notes on transaction-entry keystrokes (even informal counts are useful).

## Interfaces and Dependencies

Frontend interfaces to preserve:

- `TransactionForm.vue` emits `submit(payload, resolve, reject)` and the caller is responsible for performing the mutation.
- `TransactionTable.vue` emits `update(payload, resolve, reject)` and `delete(tx, resolve, reject)`.

New/updated backend interface:

- `GET /api/net-worth/history?interval={interval}` returning a list of points:

    [{"date": "YYYY-MM-DD", "value_minor": 123456}, ...]

New/updated frontend API client:

- `api.netWorth.history(interval)` in `src/dojo/frontend/vite/src/services/api.js`.

When revising this plan, ensure changes are reflected in `Progress` and recorded in `Decision Log` with rationale.
