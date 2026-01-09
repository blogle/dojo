# ExecPlan: Account Reconciliation Feature

This ExecPlan defines the roadmap for implementing the **Account Reconciliation** feature. It is designed for a developer who is new to the codebase. Follow the milestones sequentially.

## Purpose

To allow users to verify that their Dojo ledger matches their real-world bank statements. This involves a manual "commit" process that checkpoints the ledger and a unified **Reconciliation Worksheet** that presents all transactions requiring review (new, modified, and pending).

## Scope & Entry Points

- This plan covers ledger statement reconciliation for `cash`, `accessible`, `credit`, and `loan` accounts.
- Other account-type integrity actions are out of scope here:
  - Investments: holdings/cash verification (investment workflow).
  - Tangibles: valuation updates via `balance_adjustment`.
- SPA entry point (bookmarkable “room”):
  - `/#/accounts/:accountId/reconcile?statementMonth=YYYY-MM`
  - The route should be treated as the source of truth for “am I reconciling?” (back/forward and refresh behave predictably).

**Primary References:**
-   **Spec & Architecture:** `docs/architecture/reconciliation.md` (The Source of Truth)
-   **Engineering Rules:** `docs/rules/engineering_guide.md` (Section 4)
-   **Test Specs:** `docs/test_specs.md` (Specs 2.8, 2.10, 8.7)

---

## Phases & Milestones

### Milestone 1: Database & Backend Core
**Goal:** The database stores reconciliation history, and the service layer can generate the worksheet and commit new checkpoints.
*   [ ] **1.1 Migration:** Create `account_reconciliations` table.
*   [ ] **1.2 Service - Worksheet:** Implement the query to fetch all relevant transactions (new, modified, pending).
*   [ ] **1.3 Service - Commit:** Implement `create_reconciliation`.
*   [ ] **1.4 Testing:** Unit tests for service logic covering Spec 2.10.

### Milestone 2: API Layer
**Goal:** Frontend can access reconciliation data and trigger actions.
*   [ ] **2.1 Read Endpoints:** `GET /latest`, `GET /worksheet`.
*   [ ] **2.2 Write Endpoint:** `POST /`.
*   [ ] **2.3 Testing:** Integration tests verifying the API contract.

### Milestone 3: Frontend UI (The Wizard)
**Goal:** Users can perform the reconciliation workflow in the browser.
*   [ ] **3.1 API Client:** Update frontend service to call new endpoints.
*   [ ] **3.2 Modal Component:** Create `ReconciliationModal.vue` with 2-step wizard (Setup -> Worksheet).
*   [ ] **3.3 Worksheet Logic:** Implement client-side matching and "Difference" calculation.
*   [ ] **3.4 Entry Point:** Wire a route-driven entry point from account detail pages (`/#/accounts/:accountId/reconcile`).

---

## Implementation Details

### Milestone 1: Database & Backend Core

#### 1.1 SQL Migration
**Task:** Create a new migration file `src/dojo/sql/migrations/00XX_account_reconciliations.sql`.
*   **Requirements:**
    *   Table `account_reconciliations` as defined in `docs/architecture/reconciliation.md`.
    *   Columns: `reconciliation_id` (UUID), `account_id` (Text), `created_at` (Timestamp), `statement_date` (Date), `statement_balance_minor` (BigInt).
    *   FK: `account_id` references `accounts`.
*   **Validation:** Run `scripts/run-migrations-check`.

#### 1.2 Reconciliation Service (Worksheet Logic)
**Task:** Create `src/dojo/core/reconciliation.py`.
*   **Function:** `get_worksheet(account_id: str, last_reconciled_at: datetime) -> List[Transaction]`.
*   **Logic:** Execute the query defined in `docs/rules/engineering_guide.md` (Rule 3).
    *   Select **Active** versions where:
    *   `recorded_at > last_reconciled_at` (New/Modified since last check)
    *   **OR** `status != 'cleared'` (Pending from before).
*   **Output:** List of active transactions to display.

#### 1.3 Reconciliation Service (Commit)
**Task:** Add `create_reconciliation` to `src/dojo/core/reconciliation.py`.
*   **Inputs:** `account_id`, `statement_date`, `statement_balance_minor`.
*   **Logic:**
    *   Validate `account_id` exists.
    *   Insert new row into `account_reconciliations`.
    *   **Crucial:** Ensure `created_at` is generated server-side at the moment of insertion (this is the checkpoint timestamp).

#### 1.4 Backend Unit Tests
**Task:** Create `tests/unit/core/test_reconciliation.py`.
*   **Scenarios (Spec 2.10):**
    1.  **Modified Pending:** Edit a pending item -> Appears in worksheet.
    2.  **Correction:** Edit a previously reconciled cleared item -> Appears in worksheet.
    3.  **New Item:** Insert new item -> Appears in worksheet.
    4.  **Old Pending:** Item from 3 months ago still pending -> Appears in worksheet.

### Milestone 2: API Layer

#### 2.1 & 2.2 Routers
**Task:** Create `src/dojo/core/reconciliation_router.py`.
*   `GET /api/accounts/{account_id}/reconciliations/latest`: Returns the most recent checkpoint metadata.
*   `GET /api/accounts/{account_id}/reconciliations/worksheet`: Calls `get_worksheet`.
*   `POST /api/accounts/{account_id}/reconciliations`: Accepts JSON `{ statement_date, statement_balance_minor }`. Calls `create_reconciliation`.

#### 2.3 Integration Tests
**Task:** Create `tests/integration/reconciliation/test_reconciliation_api.py`.
*   **Flow:**
    1.  Create account & transactions (some cleared, some pending).
    2.  Call `POST` to reconcile (commit 1).
    3.  Mutate transactions (edit pending, edit cleared, add new).
    4.  Call `GET /worksheet` and verify it contains all mutated + remaining pending items.

### Milestone 3: Frontend UI

#### 3.1 API Client
**Task:** Update `src/dojo/frontend/vite/src/services/api.js`.
*   Add `reconciliations` object with methods `getLatest`, `getWorksheet`, `create`.

#### 3.2 & 3.3 The Modal (Wizard)
**Task:** Create `src/dojo/frontend/vite/src/components/ReconciliationModal.vue`.

*   **Routing + state persistence:**
    *   Treat reconciliation as a route-driven “room”: open when the route matches `/#/accounts/:accountId/reconcile` (see `docs/plans/account-detail-pages.md`).
    *   MVP guardrail: warn on leaving (Back/close/refresh) if the wizard is dirty (statement inputs, matches, checked items).
    *   Follow-up: persist a draft keyed by `(accountId, statementMonth)` so refresh/navigation does not lose in-progress work.

*   **Terminology (UI + docs):**
    *   Use **"difference"** consistently (avoid "diff").
    *   Only label something **"Statement"** once a `statementDate` (or month) is selected; otherwise label cleared totals as "Cleared (all time)".

*   **State:**
    *   `step`: 'loading' | 'setup' | 'worksheet' | 'success'.
    *   `worksheetItems`: Array.
    *   `form`: `{ statementDate, statementBalance }`.

*   **Step 1 (Setup):**
    *   Input `statementDate` (default: today) and `statementBalance`.
    *   Fetch `api.reconciliations.getLatest` + `api.reconciliations.getWorksheet`.

*   **Step 2 (Worksheet):**
    *   Show the full worksheet set (pending + new/modified since last checkpoint). Do not hide pending items by default.
    *   Computed `clearedBalance` = Sum of all cleared items included in the reconciliation calculation (statement-aware; see `docs/architecture/reconciliation.md`).
    *   Computed `difference` = `statementBalance - clearedBalance`.
    *   **Validation:** "Finish" button disabled unless `difference == 0`.
    *   **Action:** Click "Finish" -> `api.reconciliations.create` -> Close modal and navigate back to `/#/accounts/:accountId`.

#### 3.4 Integration
**Task:** Wire the entry point from account detail pages.

*   In `src/dojo/frontend/vite/src/pages/AccountDetailPage.vue`, add a primary CTA “Reconcile statement” for eligible ledger accounts that navigates to `/#/accounts/:accountId/reconcile` (preserving `?range=`).
*   Ensure the reconcile UI is opened by route match, and closing/cancel navigates back to `/#/accounts/:accountId`.
*   Optional: keep a secondary entry point from `/#/accounts` if it does not add UI noise.

---

## Validation Checklist
Before considering the task done:

1.  [ ] **Backend Tests Pass:** `scripts/run-tests --filter unit:reconciliation --filter integration:reconciliation` shows all green.
2.  [ ] **Query Logic:** Verify that a corrected date on a previously reconciled item causes it to reappear in the worksheet.
3.  [ ] **Math is Correct:** The frontend allows finishing *only* when the difference is exactly 0.00.
4.  [ ] **Linting:** `scripts/lint` passes.
5.  [ ] **Navigation + Labels:** Refresh/back/forward behave in `/#/accounts/:accountId/reconcile`, dirty-state warns on leave, and "Statement" labels only appear once a statement date is selected.
