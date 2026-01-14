# ExecPlan: Ledger and Budgeting Domain

This ExecPlan consolidates the following completed plans into a single domain-scoped document:
- `assets-liabilities-budget-flows.md` (COMPLETED)
- `envelope-budget-e2e-mvp.md` (COMPLETED)
- `editable-ledger-scd2-write-logic.md` (COMPLETED)
- `auditable-ledger-net-worth.md` (COMPLETED)

All original milestone work for these features is complete. This document serves as the historical record and reference for future work in the ledger and budgeting domain.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

## Purpose / Big Picture

Deliver a complete envelope budgeting system with transaction entry, budget allocation, categorized transfers, and account management. Users can track cash flows, manage ready-to-assign funds, record transactions across multiple account types (cash, credit, loans, accessible), and reconcile against external statements. The system maintains an audit trail of all changes through SCD-2 versioning, enabling accurate historical reconstruction.

## Progress

- [x] (2025-12-XX) Coherent asset/liability model with account classes (cash, credit, investment, tangible, loan, accessible)
- [x] (2025-12-XX) Double-entry categorized transfers between accounts
- [x] (2025-12-XX) Ready to Assign computation and cache updates
- [x] (2025-12-XX) Transaction entry service with validation
- [x] (2025-12-XX) Budget category and group management
- [x] (2025-12-XX) Budget allocation ledger with inline editing
- [x] (2025-12-XX) SCD-2 temporal tables for transactions and allocations
- [x] (2025-12-XX) Quick allocate modal with RTA validation
- [x] (2025-12-XX) Credit payment reserve handling
- [x] (2025-12-XX) Net worth snapshot computation
- [x] (2025-12-XX) Tangible asset valuation via balance adjustments
- [x] (2025-12-XX) Reconciliation workflow for ledger accounts
- [x] (2025-12-XX) Editable ledger components with net impact validation
- [x] (2025-12-XX) 20 Cypress E2E user stories covering core flows

## Surprises & Discoveries

- Observation: Group-level quick allocation fanned out into multiple individual allocation API calls rather than a single atomic transaction.
  Evidence: `cypress/e2e/user-stories/10-group-quick-allocation.cy.js` intercepts POST `/api/budget/allocations` and waits for it twice.
  Resolution: Tracked as open issue `dojo-pjb.4` for future optimization.

- Observation: Window.alert was used for insufficient RTA errors instead of in-modal feedback.
  Evidence: Cypress stories 09 and 10 stub `window.alert`.
  Resolution: Tracked as open issue `dojo-pjb.3` for UI improvement.

- Observation: Credit payment categories are mixed with user categories in transaction pickers.
  Evidence: System-generated payment categories appear alongside budget categories.
  Resolution: Tracked as open issue `dojo-pjb.13` for visual separation.

- Observation: SCD-2 write operations required splitting DML/DDL to avoid index locking.
  Evidence: Migration runner failures during CI runs with index-related errors.
  Resolution: Implemented hardened migration strategy per `db-migrations.md` plan.

## Decision Log

- Decision: Use derived payment category IDs based on account ID for credit card payments.
  Rationale: Ensures each credit account has a dedicated payment envelope while keeping category IDs deterministic and slugged.
  Date/Author: 2025-12-XX / Codex

- Decision: Store all ledger amounts as integers in minor units (cents) or Decimal with fixed quantization.
  Rationale: Prevents floating-point rounding errors in financial calculations. Only round at I/O boundaries.
  Date/Author: 2025-12-XX / Codex

- Decision: Implement SCD-2 with `is_active` flag instead of in-place UPDATE/DELETE.
  Rationale: Enables time-travel and historical reconstruction while preserving audit trail.
  Date/Author: 2025-12-XX / Codex

- Decision: Use group-level quick allocation with individual POSTs rather than bulk endpoint for MVP.
  Rationale: Reduces initial implementation complexity while still providing UX; bulk endpoint can be added later for atomicity.
  Date/Author: 2025-12-XX / Codex

- Decision: Allocate RTA for credit card payments to a reserve category rather than the spent amount.
  Rationale: Prevents Ready to Assign drift when unfunded portion of swipe exists; keeps RTA invariant stable.
  Date/Author: 2025-12-XX / Codex

## Outcomes & Retrospective

Delivered a complete envelope budgeting system with the following capabilities:

**Completed:**
- Transaction entry with validation for inflows, outflows, transfers, and categorized spending
- Hierarchical budget category management with groups
- Budget allocation ledger with inline editing
- Double-entry categorized transfers ensuring RTA neutrality for asset swaps
- Ready to Assign cache that stays synchronized with ledger state
- Net worth computation aggregating all accounts with proper asset/liability sign handling
- Account detail pages showing filtered ledger and integrity actions
- Reconciliation workflow for cash, credit, accessible, and loan accounts
- Tangible asset valuation via balance_adjustment transactions
- 20 Cypress E2E specs covering envelope budgeting, transfers, and corrections

**Remaining Work (tracked in Beads):**
- `dojo-pjb.4`: UX-004 - Make group quick allocation atomic (bulk endpoint + progress)
- `dojo-pjb.13`: UX-015 - Separate system categories in transaction category select
- `dojo-pjb.7`: UX-008 - Budgets/Allocations IA split (separate routes or tabs)
- `dojo-pjb.3`: UX-003 - Replace insufficient RTA window.alert with inline UX feedback

**Implementation Notes:**
- SCD-2 logic works correctly for transactions and allocations
- RTA computation is accurate and validated through service layer
- Transfers properly maintain double-entry semantics
- Credit payment reserve handling keeps RTA stable
- Net worth snapshots include inactive accounts for historical queries

## Context and Orientation

All ledger and budgeting functionality lives in the `/budgeting` domain module. Key files:

- `src/dojo/budgeting/services.py` - TransactionEntryService, BudgetCategoryAdminService, AccountAdminService
- `src/dojo/budgeting/dao.py` - BudgetingDAO for DuckDB access
- `src/dojo/budgeting/routers.py` - FastAPI endpoints for budgeting operations
- `src/dojo/budgeting/schemas.py` - Pydantic models for request/response validation
- `src/dojo/sql/budgeting/` - SQL queries for transactions, allocations, categories
- `cypress/e2e/user-stories/` - E2E tests (01-17, 19)

The system uses DuckDB with SCD-2 temporal tables. Account classes are: `cash`, `credit`, `investment`, `tangible`, `loan`, `accessible`. Budget categories can be organized into groups. Transfers are categorized transactions that move money between accounts without affecting net worth or budgets.

## Plan of Work

This plan documents completed work. For future enhancements in this domain, refer to the outstanding issues listed in Outcomes & Retrospective.

## Concrete Steps

For historical context, these steps were already completed:

1. Implemented account class system with derived payment categories for credit accounts in `src/dojo/budgeting/services.py`
2. Created SCD-2 tables `transaction_versions` and `budget_allocation_versions` in `src/dojo/sql/migrations/0011_core.sql`
3. Built TransactionEntryService with validation for RTA sufficiency and double-entry transfer semantics in `src/dojo/budgeting/services.py`
4. Implemented reconciliation service in `src/dojo/core/reconciliation.py` with worksheet and commit logic
5. Created 20 Cypress E2E specs covering payroll assignment, overspending coverage, credit spending, transfers, transaction lifecycle, and more
6. Built account detail pages with chart, filtered ledger, and integrity actions in `src/dojo/frontend/vite/src/pages/AccountDetailPage.vue`

## Validation and Acceptance

All acceptance criteria from original plans were met:
- `scripts/run-tests --skip-e2e` passes with green unit and integration tests
- `scripts/run-tests --filter e2e` passes all 20 user stories
- Budget allocations can be created, edited, and deleted with RTA updates
- Transfers maintain double-entry invariants and net worth neutrality
- Reconciliation workflow allows checkpointing with statement balance and pending totals
- Account detail pages render correctly for all account types

## Idempotence and Recovery

- SCD-2 operations are idempotent by design (new version on each edit)
- Migrations are written to be re-runnable safely
- Transaction validation prevents invalid state transitions

## Artifacts and Notes

Key artifacts from completed work:

```
src/dojo/budgeting/services.py
  - TransactionEntryService: Handles transaction creation, updates, and transfers
  - BudgetCategoryAdminService: Manages categories and groups
  - AccountAdminService: Account CRUD operations

src/dojo/budgeting/routers.py
  - POST /transactions - Create new transaction
  - PUT /transactions/{concept_id} - Update transaction (SCD-2)
  - POST /budget/allocations - Create or update allocation
  - DELETE /budget/allocations/{concept_id} - Delete allocation
  - GET /budget/categories - List categories with monthly state
  - GET /budget/ready-to-assign - Get RTA for current month

src/dojo/sql/migrations/
  - 0001_core.sql: Initial schema
  - 0002_account_classes.sql: Account class types
  - 0005_transaction_status.sql: Status enum
  - 0006_budget_allocations.sql: Allocation tables
  - 0011_ensure_scd2_columns.sql: SCD-2 metadata
  - 0012_account_reconciliations.sql: Reconciliation checkpoints

cypress/e2e/user-stories/
  - 01-payday-assignment.cy.js: RTA funding from paycheck
  - 02-covering-overspending.cy.js: Overspending handling
  - 03-funded-credit-card-spending.cy.js: Credit swipe flows
  - 04-categorized-investment-transfer.cy.js: Investment as spending
  - 05-manual-transaction-lifecycle.cy.js: Transaction CRUD
  - 06-editable-ledger-rows.cy.js: Inline editing
  - 07-18, 19: Budget management
  - 20-investment-tracking.cy.js: Investment account reconciliation
```

## Interfaces and Dependencies

**External Dependencies:**
- DuckDB: Primary database for transactional and analytical workloads
- FastAPI: Web framework for API endpoints
- Pydantic: Request/response validation
- TanStack Query (Vue): Data fetching and caching in frontend

**Internal Modules:**
- `dojo.core.db`: DuckDB connection management
- `dojo.core.clock`: System time control for deterministic tests
- `dojo.core.reconciliation`: Reconciliation service logic

**Key Invariants:**
- Ready to Assign = on-budget cash - Σ category available_minor
- Transfers must create paired transactions with opposite signs
- Net worth change = Σ account balance deltas - transfer net (always zero)
- SCD-2: Only one active version per concept exists at any time
