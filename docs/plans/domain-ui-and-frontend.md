# ExecPlan: User Interface and Frontend

This ExecPlan consolidates the following completed plans into a single UI/frontend domain-scoped document:
- `vue-frontend.md` (COMPLETED - full Vue 3 migration)
- `account-detail-pages.md` (COMPLETED)
- `daily-workflow-dashboard-ledger-reconcile.md` (COMPLETED)
- `reconciliation-feature.md` (COMPLETED)

All major milestone work for UI and frontend is complete. This document serves as a historical record and reference for future work in UI and frontend domain.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

## Purpose / Big Picture

Deliver a modern SPA built with Vue 3, TanStack Query, and Vite, replacing imperative DOM manipulation with declarative rendering. Provide interactive account detail pages for all account types (cash, credit, investment, tangible, loan, accessible) with charts, filtered ledgers, and integrity actions. Build unified dashboard landing page with interactive net worth chart, account panels, and budget watchlist. Implement reconciliation modal framework supporting multiple account types with extensible adapters.

## Progress

- [x] (2025-12-04) Scaffold Vite project with Vue 3, Vue Router, and @tanstack/vue-query
- [x] (2025-12-04) Implement TransactionPage as vertical slice with TanStack Query
- [x] (2025-12-05) Migrate BudgetPage, AccountsPage, AllocationsPage, and TransfersPage to Vue SFCs
- [x] (2025-12-05) Remove legacy static files (index.html, main.js, store.js) and LegacyHost component
- [x] (2025-12-05) Add controllable system clock (X-Test-Date header) for deterministic tests
- [x] (2025-12-05) Wire npm dev and e2e scripts to run backend + Vite together
- [x] (2025-12-05) Move layout and navigation to App.vue
- [x] (2025-12-06) Add Vitest unit tests for Vue components
- [x] (2025-12-05) Implement AccountDetailPage for all account types with charts
- [x] (2025-12-06) Implement DashboardPage with interactive net worth chart
- [x] (2025-12-06) Implement ReconciliationSession modal with extensible adapters
- [x] (2025-12-XX) Create LedgerReconciliationAdapter for cash/credit/accessible/loan
- [x] (2025-12-XX) Create InvestmentReconciliationAdapter for holdings verification
- [x] (2025-12-XX) Create TangibleReconciliationAdapter for valuation updates
- [x] (2025-12-XX) Implement reconciliation backend endpoints and service layer

## Surprises & Discoveries

- Observation: Legacy SPA used destructive `innerHTML` for table rebuilds causing "detached element" flakes in Cypress.
  Evidence: Transactions component cleared and rebuilt `<tbody>` on every update.
  Resolution: Vue's declarative rendering with keyed rows eliminates this flake source entirely.

- Observation: Legacy hash router toggled `.route-page--active` classes and triggered ad-hoc fetches.
  Evidence: `components/router/index.js` used DOM manipulation for routing.
  Resolution: Vue Router's declarative `<RouterView />` provides stable navigation state.

- Observation: Global state store (`store.js`) was a bespoke clone-based system without derivations.
  Evidence: Manual state refreshes scattered across modules after mutations.
  Resolution: TanStack Query cache + computed properties provides automatic reactive updates.

- Observation: Cypress tests used `cy.clock()` which only affects top window, not legacy app in iframe.
  Evidence: Legacy app in iframe had isolated JS context during time travel.
  Resolution: Removed iframe bridge after full Vue migration; all pages now render directly.

- Observation: `cy.visit()` does not reload on hash change, causing state leakage between legacy and Vue routes.
  Evidence: Navigating from legacy iframe to Vue route left artifacts behind.
  Resolution: Added `cy.reload()` workaround during migration period; no longer needed post-migration.

- Observation: Reconciliation modal needed to support three fundamentally different workflows (statement verify, holdings verify, valuation update).
  Evidence: Different account classes have different reconciliation semantics and data requirements.
  Resolution: Created adapter pattern with `ReconciliationSession` as shell and `LedgerReconciliationAdapter`, `InvestmentReconciliationAdapter`, `TangibleReconciliationAdapter` for specific logic.

## Decision Log

- Decision: Adopt Vite as build pipeline instead of no-build import maps.
  Rationale: Vite provides SFC ergonomics, deterministic deps, fast unit tests (Vitest), and optimized builds. Import maps would require magic-string templates and CDN drift.
  Date/Author: 2025-12-04 / Codex

- Decision: Use TanStack Query instead of Pinia or Vuex for state management.
  Rationale: TanStack Query's server-state-first approach eliminates boilerplate for data fetching, caching, and invalidation. Perfect fit for API-heavy financial app.
  Date/Author: 2025-12-04 / Codex

- Decision: Implement router-driven reconciliation entry (`/#/accounts/:accountId/reconcile`) instead of modal-only approach.
  Rationale: Route provides bookmarkable URL, back/forward navigation, and clean browser history. Modal is secondary to routing contract.
  Date/Author: 2025-12-XX / Codex

- Decision: Create adapter components for different reconciliation types.
  Rationale: Allows `ReconciliationSession` modal to be reusable while isolating type-specific logic (ledger worksheet, investment holdings, tangible valuation).
  Date/Author: 2025-12-XX / Codex

- Decision: Keep all CSS classes and data-testids from legacy implementation.
  Rationale: Preserves Cypress test compatibility and visual consistency. No visual refresh required.
  Date/Author: 2025-12-04 / Codex

- Decision: Use X-Test-Date header for backend time control instead of monkeypatching.
  Rationale: Allows time travel without runtime code modification; works for any client (Cypress, manual testing).
  Date/Author: 2025-12-05 / Codex

## Outcomes & Retrospective

Delivered complete modern SPA with the following capabilities:

**Completed:**
- Vue 3 SPA with Vue Router and hash-based routing
- TanStack Query for data fetching, caching, and invalidation
- Vite build pipeline with optimized asset bundling
- Six core pages: Transactions, Accounts, Budgets, Allocations, Transfers, Account Detail, Dashboard
- Account detail pages supporting all account classes with:
  - Interactive performance charts with interval selection
  - Filtered transaction/allocation ledger
  - Integrity actions (Reconcile for ledger, Verify holdings for investment, Update valuation for tangible)
- Dashboard landing page with:
  - Interactive net worth chart with drag-to-select interval analysis
  - Accounts panel with deep links
  - Budget watchlist widget
- Reconciliation modal framework with extensible adapters
- Vitest unit tests for Vue components
- Legacy removal with no iframe bridge

**Remaining Work (tracked in Beads):**
- Multiple UX improvements tracked under `dojo-pjb` epic (various accessibility and UX refinements)

**Implementation Notes:**
- Vue migration complete; all legacy static files removed
- Dashboard uses inline SVG rendering for chart (no external charting library dependency)
- Reconciliation modal uses composition pattern with adapter components
- Time control via `X-Test-Date` header enables deterministic Cypress tests
- All Cypress tests updated to work with Vue SPA directly (no iframe piercing)

## Context and Orientation

Frontend artifacts live entirely in `src/dojo/frontend/vite/`:

**Core Pages:**
- `src/main.js` - App entry point with router, query client, and app mounting
- `src/App.vue` - Root component with layout, nav, and RouterView
- `src/router.js` - Vue Router configuration with hash history

**Page Components:**
- `src/pages/TransactionsPage.vue` - Transaction entry and ledger
- `src/pages/AccountsPage.vue` - Account list and management
- `src/pages/BudgetPage.vue` - Category management and allocations
- `src/pages/AllocationsPage.vue` - Allocation ledger
- `src/pages/TransfersPage.vue` - Transfer workflow
- `src/pages/AccountDetailPage.vue` - Account-specific detail views
- `src/pages/DashboardPage.vue` - Net worth dashboard

**Shared Components:**
- `src/components/TransactionForm.vue` - Transaction entry form
- `src/components/TransactionTable.vue` - Transaction ledger display
- `src/components/AllocationModal.vue` - Quick allocate modal
- `src/components/ReconciliationSession.vue` - Reconciliation modal shell
- `src/components/reconciliation/LedgerReconciliationAdapter.vue` - Statement reconciliation for ledger accounts
- `src/components/reconciliation/InvestmentReconciliationAdapter.vue` - Holdings verification for investments
- `src/components/reconciliation/TangibleReconciliationAdapter.vue` - Valuation updates for tangibles
- `src/components/PortfolioChart.vue` - Investment portfolio chart
- `src/components/HoldingsTable.vue` - Investment holdings display

**Services:**
- `src/services/api.js` - Axios-based API client with TanStack Query integration
- `src/services/format.js` - Currency formatting, date utilities

**Build Config:**
- `vite.config.js` - Vite configuration with API proxy and build output
- `package.json` - Dependencies and npm scripts

The SPA uses hash-based routing (`/#/transactions`, `/#/accounts/:accountId`, etc.). TanStack Query manages server state cache with automatic refetch-on-window-focus. CSS is imported from legacy `src/dojo/frontend/static/styles/` to maintain visual consistency.

## Plan of Work

This plan documents completed work. For future UI enhancements, refer to the `dojo-pjb` epic in Beads which tracks various UX improvements.

## Concrete Steps

For historical context, these steps were already completed:

1. Initialized Vite project with Vue 3, Vue Router 4, and @tanstack/vue-query@5
2. Implemented TransactionPage as vertical slice proving Vue + TanStack Query pattern
3. Created shared TransactionForm and TransactionTable components
4. Migrated remaining pages (Accounts, Budgets, Allocations, Transfers) to Vue SFCs
5. Moved header/navigation into App.vue with RouterLink active states
6. Implemented AccountDetailPage with performance charts, filtered ledger, and integrity actions for all account types
7. Implemented DashboardPage with interactive SVG chart and account/watchlist panels
8. Created ReconciliationSession modal with adapter pattern for extensibility
9. Created three reconciliation adapters (Ledger, Investment, Tangible)
10. Added Vitest configuration and unit tests for Vue components
11. Implemented X-Test-Date header support in budgeting routers
12. Migrated all Cypress tests to work with Vue SPA targets
13. Removed legacy static files and LegacyHost component

## Validation and Acceptance

All acceptance criteria from original plans were met:
- `npm run build` succeeds and produces `src/dojo/frontend/static/dist/`
- `npm run dev` starts Vite dev server and proxies `/api` to FastAPI
- `npm run test:unit` runs Vitest with green results
- `scripts/run-tests --filter e2e` passes all 20 user stories
- All pages render correctly with Vue Router navigation
- Account detail pages show charts, filtered data, and integrity actions for all account types
- Dashboard interactive chart works with hover, drag-select, and interval toggles
- Reconciliation modal opens via route and supports all account classes

## Idempotence and Recovery

- Vite builds are deterministic via Nix hash
- npm install is reproducible via npmDepsHash in flake.nix
- Vue component renders are idempotent given same input data
- Cypress tests can be re-run with `cy.reload()` workarounds during migration period

## Artifacts and Notes

Key frontend artifacts:

```
src/dojo/frontend/vite/
  src/
    main.js                 # App entry point
    App.vue                # Root component
    router.js              # Vue Router config
    pages/
      TransactionsPage.vue      # Transaction ledger
      AccountsPage.vue         # Account list
      BudgetPage.vue           # Budget management
      AllocationsPage.vue       # Allocation ledger
      TransfersPage.vue        # Transfer workflow
      AccountDetailPage.vue    # Account detail (all types)
      DashboardPage.vue        # Net worth dashboard
    components/
      TransactionForm.vue       # Transaction entry
      TransactionTable.vue       # Transaction display
      AllocationModal.vue        # Quick allocate
      ReconciliationSession.vue              # Reconciliation shell
      reconciliation/
        LedgerReconciliationAdapter.vue       # Statement verify
        InvestmentReconciliationAdapter.vue       # Holdings verify
        TangibleReconciliationAdapter.vue        # Valuation update
      PortfolioChart.vue        # Investment chart
      HoldingsTable.vue         # Investment holdings
    services/
      api.js                  # API client
      format.js               # Utilities
  package.json              # Deps and scripts
  vite.config.js            # Build config
```

## Interfaces and Dependencies

**Build Tool:**
- Vite: Build tool and dev server

**Frameworks:**
- Vue 3: Reactive UI framework
- Vue Router 4: Hash-based routing
- @tanstack/vue-query@5: Data fetching and caching

**Testing:**
- Vitest: Unit testing for Vue components
- Cypress: E2E browser testing

**API Communication:**
- Axios: HTTP client (via api.js wrapper)

**Key Invariants:**
- All routes are bookmarkable with hash paths
- TanStack Query cache automatically invalidates on mutations
- CSS classes match legacy implementation for Cypress compatibility
- data-testids provide stable selectors for E2E tests
