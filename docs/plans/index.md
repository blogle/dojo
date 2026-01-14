# Plan Index

This index provides an overview of all current planning documents for the Dojo project. Historical ExecPlans have been consolidated into domain-scoped documents to reduce duplication and improve maintainability.

## Current Domain Plans

The following domain-scoped ExecPlans capture all completed work and serve as the primary planning documents for future development:

### Ledger and Budgeting
**Document:** `docs/plans/domain-ledger-and-budgeting.md`

**Consolidates:**
- `assets-liabilities-budget-flows.md` (COMPLETED)
- `envelope-budget-e2e-mvp.md` (COMPLETED)
- `editable-ledger-scd2-write-logic.md` (COMPLETED)

**Completed Features:**
- Coherent asset/liability model with account classes (cash, credit, investment, tangible, loan, accessible)
- Double-entry categorized transfers between accounts
- Ready to Assign computation and cache updates
- Transaction entry service with validation
- Budget category and group management
- Budget allocation ledger with inline editing
- SCD-2 temporal tables for transactions and allocations
- Quick allocate modal with RTA validation
- Credit payment reserve handling
- Net worth snapshot computation
- Tangible asset valuation via balance adjustments
- Reconciliation workflow for ledger accounts
- Editable ledger components with net impact validation
- 20 Cypress E2E user stories

**Outstanding Work:** (Tracked in Beads)
- `dojo-pjb.4`: UX-004 - Make group quick allocation atomic
- `dojo-pjb.13`: UX-015 - Separate system categories in transaction category select
- `dojo-pjb.7`: UX-008 - Budgets/Allocations IA split
- `dojo-pjb.3`: UX-003 - Replace insufficient RTA window.alert with inline UX feedback

---

### Investments and Net Worth
**Document:** `docs/plans/domain-investments-and-net-worth.md`

**Consolidates:**
- `auditable-ledger-net-worth.md` (COMPLETED - net worth portion)
- `investment-tracking.md` (COMPLETED)

**Completed Features:**
- Portfolio state management with positions and cash
- Investment reconciliation workflow (holdings verification)
- Market data integration (Yahoo Finance or similar)
- Portfolio history and time-series data
- Performance metrics (returns, volatility, drawdowns)
- Investment account detail pages with charts
- Net worth computation aggregating all accounts
- Net worth history API with interval queries
- Dashboard landing page with interactive chart

**Outstanding Work:** (Tracked in Beads)
- `dojo-aur`: Write Outcomes & Retrospective for Investment Tracking

---

### Infrastructure and Deployment
**Document:** `docs/plans/domain-infrastructure.md`

**Consolidates:**
- `ci-release-pipeline.md` (COMPLETED)
- `db-migrations.md` (COMPLETED)
- `deployment-pipeline.md` (COMPLETED)
- `cypress-e2e-migration.md` (COMPLETED)
- `spec-aligned-test-suite.md` (COMPLETED - Milestones 1-3 only; Milestones 4-5 explicitly deferred)

**Completed Features:**
- Reproducible Nix-based builds with pinned Python and Node tooling
- Create Nix-based container build producing OCI image
- Implement GitHub Actions CI workflow (test, lint, build)
- Implement GitHub Actions release workflow (semver, changelog, GHCR push)
- Create Kubernetes manifests with Kustomize (deployment, service, ingress)
- Harden migration runner with transactional execution
- Implement migration ID tracking and idempotence checks
- Add CI preflight checks for migration drift
- Implement cache rebuild hook for stale data
- Set up pytest-cov coverage instrumentation
- Create integration test packages by feature area
- Add property tests using Hypothesis with deterministic seeds
- Implement cache integrity specs (Docs Spec 2.9 and 3.9)
- Create deterministic time control for tests (clock fixture)
- Migrate Cypress specs to Vue SPA targets
- Consolidate to 7 spec-aligned E2E journeys
- Add legacy→Vue query invalidation bridge

**Outstanding Work:** (Explicitly deferred per plan decision)
- Performance harness (Milestone 5 of spec-aligned-test-suite) - deferred as low priority

---

### User Interface and Frontend
**Document:** `docs/plans/domain-ui-and-frontend.md`

**Consolidates:**
- `vue-frontend.md` (COMPLETED - full Vue 3 migration)
- `account-detail-pages.md` (COMPLETED)
- `daily-workflow-dashboard-ledger-reconcile.md` (COMPLETED)
- `reconciliation-feature.md` (COMPLETED)

**Completed Features:**
- Scaffold Vite project with Vue 3, Vue Router, and @tanstack/vue-query
- Implement TransactionPage as vertical slice with TanStack Query
- Migrate BudgetPage, AccountsPage, AllocationsPage, and TransfersPage to Vue SFCs
- Remove legacy static files (index.html, main.js, store.js) and LegacyHost component
- Add controllable system clock (X-Test-Date header) for deterministic tests
- Wire npm dev and e2e scripts to run backend + Vite together
- Move layout and navigation to App.vue
- Add Vitest unit tests for Vue components
- Implement AccountDetailPage for all account types with charts
- Implement DashboardPage with interactive net worth chart
- Implement ReconciliationSession modal with extensible adapters
- Create LedgerReconciliationAdapter for cash/credit/accessible/loan
- Create InvestmentReconciliationAdapter for holdings verification
- Create TangibleReconciliationAdapter for valuation updates
- Implement reconciliation backend endpoints and service layer

**Outstanding Work:** (Tracked in Beads under `dojo-pjb` epic)
- Multiple UX improvements tracked as open issues (see epic for details)

---

## Historical (Archived) Plans

The following original ExecPlans have been fully consolidated into domain-scoped documents above. These files are kept in `docs/plans/archive/` for historical reference but should not be used as active planning documents:

- `account-detail-pages.md` → Consolidated into `domain-ui-and-frontend.md`
- `assets-liabilities-budget-flows.md` → Consolidated into `domain-ledger-and-budgeting.md`
- `auditable-ledger-net-worth.md` → Consolidated into `domain-investments-and-net-worth.md`
- `ci-release-pipeline.md` → Consolidated into `domain-infrastructure.md`
- `cypress-e2e-migration.md` → Consolidated into `domain-infrastructure.md`
- `daily-workflow-dashboard-ledger-reconcile.md` → Consolidated into `domain-ui-and-frontend.md`
- `db-migrations.md` → Consolidated into `domain-infrastructure.md`
- `deployment-pipeline.md` → Consolidated into `domain-infrastructure.md`
- `editable-ledger-scd2-write-logic.md` → Consolidated into `domain-ledger-and-budgeting.md`
- `envelope-budget-e2e-mvp.md` → Consolidated into `domain-ledger-and-budgeting.md`
- `investment-tracking.md` → Consolidated into `domain-investments-and-net-worth.md`
- `reconciliation-feature.md` → Consolidated into `domain-ui-and-frontend.md`
- `spec-aligned-test-suite.md` → Consolidated into `domain-infrastructure.md`
- `vue-frontend.md` → Consolidated into `domain-ui-and-frontend.md`

## Using These Plans

When starting new work in a domain:

1. **Start with the domain-scoped plan** listed above for that area
2. **Check the "Outstanding Work" section** for any tracked Beads issues
3. **Reference historical archived plans** only if necessary for deep context on specific implementation details
4. **Check ARCHITECTURE.md** for current system context
5. **Follow PLANS.md format** when creating new ExecPlans for future work

## Creating New Plans

All new ExecPlans should be created as domain-scoped documents following these guidelines:

- One plan per domain/feature area (e.g., `domain-forecasting.md`, `domain-optimization.md`)
- Include completed work summary in "Progress" section with checkmarks
- Document all surprises, decisions, and outcomes as living document sections
- Reference outstanding Beads issues for future work
- Maintain self-containment per `.agent/PLANS.md`

## Tracking Outstanding Work

Outstanding work is tracked in **Beads** (`.beads/issues.jsonl`). View with:

```bash
bd list
```

Or view specific issues:

```bash
bd show <issue-id>
```

## Maintenance

When work from a domain plan is completed:
1. Update the "Progress" section in the domain plan with full checkmarks
2. Add outcomes to "Outcomes & Retrospective" section
3. Create a Beads issue for any new follow-up work discovered
4. Optionally archive the plan if the domain is feature-complete and no new work is anticipated
