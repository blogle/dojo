# ExecPlan: Envelope Budget E2E MVP

This ExecPlan is a living document and must be maintained in strict accordance with `.agent/PLANS.md`. Every section below is mandatory and must remain self-contained so that a novice engineer can implement the feature using only this file plus the working tree.

## Purpose / Big Picture

Deliver a complete envelope-budgeting slice so a household can stand up the SPA, add accounts, enter transactions, allocate Ready-to-Assign (RTA) into monthly envelopes, and run categorized transfers (cash to credit card or investment) backed by the existing FastAPI + DuckDB services. After completion the UI alone—without cURL or the Python REPL—supports: recording income/outflow, creating budget categories, allocating RTA to a category, and executing a double-entry transfer that shows both ledger legs while net worth and RTA stay consistent with the architecture described in `docs/architecture/budgets_and_transactions.md` and `docs/architecture/overview.md`.

## Progress

- [x] (2025-11-18 09:45Z) Surveyed architecture docs, README, and prior plans to identify required flows and existing backend endpoints.
- [ ] (Pending) Deliver the transaction entry, budgets/envelope management, categorized transfer UI, and Cypress coverage described in this ExecPlan.

## Surprises & Discoveries

- None yet. Update this section with any unexpected API gaps, UX constraints, or performance issues discovered during implementation, including evidence (stack traces, screenshots, or log excerpts).

## Decision Log

- None yet. Record every decision (UI layout trade-offs, schema adjustments, validation strategies) with rationale and timestamp as they occur.

## Outcomes & Retrospective

Pending. Once milestones land, summarize the observed behavior, what remains, and lessons learned relative to the purpose.

## Context and Orientation

The SPA lives in `src/dojo/frontend/static/` with `index.html` defining sections that are conditionally shown based on the hash fragment (e.g., `#/transactions`). `app.js` hydrates DOM nodes, fetches JSON via helper `fetchJSON`, and tracks UI state inside a `state` object. The existing `renderSectionFromHash`, `refreshTransactions`, `updateAccountStats`, and `fetchReadyToAssign` functions already orchestrate navigation and account summaries, so every new UI element must plug into those helpers instead of creating duplicate fetch loops. Formatted currency in the current UI uses helpers `dollarsToMinor` and `minorToDollars`; keep them as the single source of truth for the sign and unit conversions. Styling resides in `styles.css`; keep additions consistent with existing flex/grid utilities and reuse button + modal classes so Cypress selectors remain stable.

The DOM already contains a transactions section with a ledger table but no create/edit controls, an accounts modal used for CRUD, and placeholder sections for other hashes. We will add data attributes such as `data-testid="transaction-form"`, `data-testid="budgets-section"`, and `data-testid="transfer-form"` so Cypress can locate interactive pieces deterministically.

Backend APIs already implement the business logic:

- `POST /api/transactions` accepts `dojo.budgeting.schemas.NewTransactionRequest` with fields `account_id`, `category_id`, `concept`, `memo`, `amount_minor`, `date`. Negative `amount_minor` represents outflows; positive values represent inflows.
- `GET /api/reference-data` returns accounts and budget categories for dropdowns.
- `GET /api/budget-categories` plus `GET /api/budget/ready-to-assign` expose envelope state populated by `upsert_category_monthly_state.sql`.
- `POST /api/budget-categories` creates envelopes (`category_id` slug must match `SLUG_PATTERN` in `src/dojo/budgeting/schemas.py`).
- `POST /api/transfers` accepts `CategorizedTransferRequest` and responds with `CategorizedTransferResponse` containing `concept_id`, both transaction ids, and account deltas.

Cypress end-to-end specs in `cypress/e2e/admin_pages.cy.js` currently assert account management. We will extend them to cover the new flows. Tests run via `pytest` and `npx cypress run --e2e --browser chromium` inside the activated nix environment.

## Plan of Work

### Milestone 1: Transaction entry UI and plumbing

Explain to the executor that the current transactions page only renders a ledger table. Insert an input form above that table in `src/dojo/frontend/static/index.html` with native `<label>` and `<input>` pairs that capture date, account, category, memo, amount, and context toggles. The form should carry `id="transaction-form"` plus `data-testid="transaction-form"` so Cypress has a durable hook. Add a segmented control or pair of radio buttons for "Record expense" vs. "Allocate envelope"; store the choice in a hidden field so the submit handler can set `category_id` and amount signs consistently. Add a `button type="button"` toggle that switches between entering dollars and minor units in the same field, showing helper text that clarifies which unit is currently active.

In `app.js`, extend the module-level `state` with `state.forms.transaction = { mode: "expense", submitting: false, error: null }`. During `DOMContentLoaded`, fetch `/api/reference-data` once (reuse the logic already used for account stats) and populate `<select>` elements by calling a new helper `renderTransactionFormOptions(reference)`. The submit handler should prevent default submission, read values via `FormData`, convert amount input to integer cents with `dollarsToMinor`, and flip the sign to negative whenever the mode is "expense" or "allocation". Assemble a `NewTransactionRequest` object with `account_id`, `category_id`, `concept`, `memo`, `amount_minor`, and ISO date. Call `fetchJSON("/api/transactions", { method: "POST", body: JSON.stringify(payload) })` and, after success, call `Promise.all([refreshTransactions(), fetchReadyToAssign(), updateAccountStats()])` to keep UI counters in sync.

Show progress feedback by disabling the submit button and adding `aria-busy="true"` while awaiting the response; re-enable it and restore focus afterwards. Display validation errors returned by the API inside a `<p class="form-error" data-testid="transaction-error">` region directly under the form. Keep keyboard navigation friendly by ordering the inputs logically and ensuring the submit button is last in the tab order. If submission succeeds, clear only the memo and amount fields while leaving the date defaulted to today, so rapid entry stays efficient. Document this behavior in a short code comment near the clearing logic so future maintainers know it is intentional.

### Milestone 2: Budgets page with envelope control

Add a dedicated `section` for `#/budgets` in `index.html` that mirrors the SPA hash navigation and carries `data-testid="budgets-section"`. Above the category grid, place a summary bar that displays Ready-to-Assign (RTA), "Activity this month", and "Available this month" metrics; populate these numbers with `minorToDollars` or the raw minor units based on a toggle button (`data-testid="budgets-amount-toggle"`). For each category, render the display name, slug, `available_minor`, and `activity_minor`, plus a contextual menu with "Rename" and "Allocate" actions.

In `app.js`, introduce `state.budgets = { categories: [], readyToAssignMinor: 0, unitDisplay: "dollars" }` and a `loadBudgetsData()` helper that concurrently calls `GET /api/budget-categories` and `/api/budget/ready-to-assign`. Whenever the budgets section becomes visible, call this helper and then `renderBudgetsPage(state.budgets)` to patch DOM nodes in place instead of re-rendering the entire section. When no categories exist, show an empty-state paragraph that references the "Add category" button.

Reuse the accounts modal pattern by cloning the modal markup and renaming ids/classes to `category-modal`. When the "Add category" button is clicked, open the modal, focus the display name input, and auto-fill the slug field by running the existing `slugify` helper as the user types. Submitting the modal fires `POST /api/budget-categories` with `{ name, slug }`. If the backend returns a validation error (for example, slug collision), keep the modal open, surface the error near the slug field, and leave the previous values intact. Successful submissions close the modal, refresh budgets data, and show a brief confirmation toast (reuse the `showToast` helper if present or add one near the transfer milestone).

Support renaming by adding a "Rename" button inside each category card. Clicking it re-opens the same modal pre-populated with the existing name/slug and displays a notice that changing the slug will move historical allocations. The rename submission can call the same `POST /api/budget-categories` endpoint if it supports upserts; otherwise, add a dedicated endpoint call and document its usage here. After renaming, update both the budgets list and any cached reference data so the transactions form picks up the new category immediately.

Create an inline allocation form under the summary bar with `data-testid="allocation-form"`. The form should request a target category, amount, and memo; the memo can default to "Envelope allocation" but should remain editable. When the user submits, post to `/api/transactions` with `category_id` set to the selected envelope, `amount_minor` negative, and `account_id` set to whichever account in `state.accounts` is flagged with `is_ready_to_assign === true` (fall back to a dedicated "RTA" account id defined in settings if the API exposes it differently, and document the id here once confirmed). Upon success, update RTA, the specific category's `available_minor`, and the "Activity" metric. Inline helper text must explain that "Allocations decrease Ready-to-Assign and increase the envelope's available amount" so the UX remains intuitive.

### Milestone 3: Categorized transfer flow

Extend the transactions section with a `fieldset` that is hidden by default and becomes visible when a "Transfer" toggle switch is active. Add `data-testid="transfer-form"` to the container and include the following inputs: source account select, destination account select, optional category select (used to categorize the reimbursement), amount (dollars by default with a units toggle), and memo. Populate the selects from the same `state.accounts` and `state.categories` caches used in Milestone 1 so the UI stays consistent.

In `app.js`, introduce `state.forms.transfer = { submitting: false, error: null }` and register event listeners that keep the submit button disabled until the source and destination differ, a category is chosen, and the parsed amount is greater than zero. Add inline validation text next to each select to guide the user when two identical accounts are picked. Assemble the payload `{ source_account_id, destination_account_id, category_id, concept, memo, amount_minor }` where `amount_minor` is always positive. Post it to `/api/transfers` using `fetchJSON` and, upon success, call the same refresh helpers as in Milestone 1 plus `renderBudgetsPage` because categorized transfers mutate envelopes as well.

After a successful response, surface a non-blocking toast that includes `response.concept_id`, `response.source_transaction_id`, and `response.destination_transaction_id`. The toast copy should point users to the ledger table so they can verify both legs immediately. Reset only the amount and memo fields so repeated transfers stay efficient, but always clear the validation messages and hide the error region on success.

Add documentation explaining that this flow is distinct from single-leg transactions because the backend inserts two ledger rows that share a `concept_id`: one moves money between accounts, and one ties the movement to a budget category so RTA and net worth stay balanced. Mention this difference in both the inline code comments near the transfer handler and in the "Artifacts and Notes" section below so future contributors remember the invariants.

### Milestone 4: Cypress coverage and documentation touch-ups

Extend `cypress/e2e/admin_pages.cy.js` with three scenario blocks that mirror the manual acceptance criteria. Use the new `data-testid` attributes (`transaction-form`, `allocation-form`, `transfer-form`, `budgets-section`, summary stat ids) so the tests remain resilient to cosmetic HTML changes. Seed accounts via the existing UI helpers if no checking/credit accounts exist; otherwise, select the first row that matches the expected account type. After submitting the transaction form, assert that the ledger table prepends a new row containing the submitted memo and amount, and that the Ready-to-Assign banner updates within a few seconds (use `cy.contains` with `{ timeout: 10000 }` to accommodate API latency).

For the budgets flow, navigate directly to `#/budgets`, create a fresh category, allocate a known amount, and assert that the category card's availability column increases by exactly that amount while the summary RTA chips decrease by the same value. Add a helper command such as `cy.formatMinor` or reuse existing utilities to avoid flaky currency parsing. For the transfer scenario, flip the transfer toggle, enter distinct source/destination accounts, submit, and verify that two ledger rows referencing the same `concept_id` appear plus that the toast includes both transaction ids.

Document the new forms in `README.md` (or whichever getting-started doc references the SPA) so future testers know where to find the budgeting UI. Inline in `app.js`, add short comments in the handlers describing why the state is split between transaction and transfer forms. Update the ExecPlan `Progress` section whenever one of the Cypress scenarios lands so the living document reflects test coverage.

## Concrete Steps

1. Ensure the nix/direnv environment is active at the repo root:

        direnv allow .
        # or: nix develop

2. While developing the frontend, run the FastAPI server from the repo root so the SPA hits live endpoints:

        uvicorn dojo.core.app:app --reload

3. In a separate terminal, build/test iteratively:

        pytest
        npx cypress run --e2e --browser chromium

4. For manual UI verification, open the SPA at http://127.0.0.1:8000/ in a modern browser and follow the Validation checklist below. Document any failures in Surprises & Discoveries.

## Validation and Acceptance

Success requires demonstrating all three UI flows:

1. **Transaction entry:** With the server running, open http://127.0.0.1:8000/#/transactions, fill the new form (date, checking account, groceries category, memo, amount), submit, and observe the row appear atop the ledger. RTA and net worth stats should refresh immediately.
2. **Budgets page:** Navigate to http://127.0.0.1:8000/#/budgets, click “Add category,” create one, allocate ≤ current RTA to it, and ensure the category’s availability increases by the allocation amount while RTA decreases by the same value. The activity metric should reflect the allocation.
3. **Categorized transfer:** Use the new transfer toggle to move money from checking to a credit account. After submission, both accounts’ balances should update and two transactions should appear in the ledger referencing the same concept id. The UI should display information from `CategorizedTransferResponse` (transaction ids and memo).

Automated validation: `pytest` must pass, and `npx cypress run --e2e --browser chromium` must include assertions covering all new flows. Document the command outputs briefly in Artifacts when first achieved.

## Idempotence and Recovery

All REST calls are already idempotent with respect to retries: attempting to recreate a category slug returns a validation error, and re-posting a transfer with the same payload simply inserts another pair of transactions sharing a new `concept_id`. When the SPA encounters a failed fetch, leave the form data intact and display the backend-provided error text so the user can correct inputs without re-entry. Because DuckDB migrations are SCD-2, re-running `pytest` or the Cypress suite after rollback is safe. Frontend changes are additive and can be reloaded safely by refreshing the browser.

## Artifacts and Notes

Important snippets to reference while implementing:

        const referenceData = await fetchJSON("/api/reference-data");
        state.accounts = referenceData.accounts;
        state.categories = referenceData.categories;
        renderTransactionFormOptions();

        const allocationPayload = {
            account_id: state.accounts.find((acct) => acct.is_ready_to_assign).id,
            category_id: selectedCategoryId,
            concept: "Envelope allocation",
            memo,
            amount_minor: -1 * dollarsToMinor(amountInputValue)
        };
        await fetchJSON("/api/transactions", {
            method: "POST",
            body: JSON.stringify(allocationPayload)
        });

        const transferPayload = {
            source_account_id,
            destination_account_id,
            category_id,
            concept,
            memo,
            amount_minor: dollarsToMinor(amountDollars)
        };
        const response = await fetchJSON("/api/transfers", {
            method: "POST",
            body: JSON.stringify(transferPayload)
        });
        showToast(`Transfer ${response.concept_id} posted (${response.source_transaction_id} & ${response.destination_transaction_id})`);

        // Cypress selector example
        cy.get('[data-testid="transaction-form"]').within(() => {
            cy.get('input[name="amount"]').type("125.67");
            cy.root().submit();
        });

Capture similar snippets for allocations and Cypress commands as the implementation progresses so that future readers see working examples.

## Interfaces and Dependencies

- `src/dojo/frontend/static/index.html`: add transaction form markup, budgets section, allocation controls, and transfer toggle plus toast container. Maintain semantic HTML, reuse `.form-field`, `.modal`, and `.summary-chip` classes, and attach new `data-testid` hooks (`transaction-form`, `allocation-form`, `transfer-form`, `budgets-section`, `budgets-amount-toggle`).
- `src/dojo/frontend/static/app.js`: extend `state`, add fetch/render helpers (`loadReferenceData`, `loadBudgetsData`, `renderBudgetsPage`, `renderTransactionFormOptions`, `submitTransaction`, `submitAllocation`, `submitTransfer`), and add a lightweight `showToast` utility if none exists so transfers can surface response ids. Keep minor-unit math centralized to avoid drift.
- `src/dojo/frontend/static/styles.css`: only augment if necessary for layout; reuse button and modal styles to avoid divergence, but add `.form-error`, `.toast`, and `.summary-chip--warning` modifiers if readability demands it.
- Documentation (`README.md` or `docs/architecture/overview.md` SPA section): describe the new budgeting flows so future contributors know how to exercise them manually.
- REST APIs (`/api/reference-data`, `/api/transactions`, `/api/budget-categories`, `/api/budget/ready-to-assign`, `/api/transfers`): no backend changes expected, but document any discrepancies immediately if schemas differ from the assumptions captured here.
- Cypress spec `cypress/e2e/admin_pages.cy.js`: add deterministic selectors (see above) and helper utilities for unit conversions to script the flows reliably.

## Revision Note

Initial fully fleshed ExecPlan authoring on 2025-11-18 to capture the transaction entry, budgets/envelope, and categorized transfer MVP requirements plus validation strategy before implementation begins. Expanded on 2025-11-18 11:05Z to detail DOM structure, state fields, allocation specifics, transfer toasts, selectors for Cypress, and documentation touchpoints so execution is unambiguous before coding starts.
