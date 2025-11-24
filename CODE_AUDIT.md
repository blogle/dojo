# Codebase Audit and Remediation Plan

This document outlines the findings of a comprehensive audit of the project's codebase against its established documentation and development rules. It categorizes all identified violations and provides a clear, actionable plan for addressing them.

## Purpose / Big Picture

The goal of this audit is to identify all areas of the codebase that deviate from the project's defined standards, as laid out in `AGENTS.md` and the `docs/rules/` directory. By systematically identifying and categorizing these violations, we can create a prioritized roadmap for bringing the codebase into full compliance. This will improve maintainability, reduce technical debt, and ensure that future development adheres to our shared engineering principles.

## Progress

- [x] **Python Backend:** Address all violations of the Python and engineering guidelines.
- [x] **Frontend:** Refactor the frontend to align with the component-based, stateless architecture.
- [x] **Temporal Data Model:** Correct all violations of the temporal data model implementation rules.
- [ ] **Documentation:** Update documentation to reflect any changes made during remediation.

## Surprises & Discoveries

- The frontend is a single, large JavaScript file (`app.js`) with a corresponding monolithic CSS file. This indicates a significant departure from the documented component-based architecture and will require a substantial refactoring effort.
- The use of a `threading.Lock` in the database connection management (`src/dojo/core/db.py`) suggests potential underlying concurrency issues that may need deeper investigation beyond a simple code fix.
- Budget categories needed to expose both current-month availability and the prior-month roll-over separately. `BudgetCategoryDetail` now carries `last_month_available_minor` so the UI and reports can diverge without guessing.
- Repeated `/api/testing/reset_db` calls during Cypress runs can momentarily remove the DuckDB file between requests. Wrapping the DAO's `ready_to_assign`/`month_cash_inflow` readers in a `CatalogException` guard prevents transient "table not found" crashes during those resets.
- Breaking the UI into page-level modules surfaced just how intertwined DOM selection and data fetching had become; introducing a central store forced us to be explicit about each update path and highlighted where we were previously mutating shared objects from event handlers.
- Replacing ad-hoc `BEGIN`/`COMMIT` blocks with a DAO-level transaction context manager gives us a single place to enforce rollback discipline and makes the temporal ledger boundary obvious in code and tests.

## Decision Log

- **Decision:** This document will serve as the primary artifact for tracking the remediation effort.
  **Rationale:** A single, comprehensive document is necessary to provide a clear and actionable plan for addressing the identified issues.
  **Date/Author:** 2025-11-23, Gemini

## Outcomes & Retrospective

The audit revealed a significant number of violations across the entire codebase, from project structure to frontend architecture. The most critical issues are the monolithic frontend and the violations of the temporal data model's immutability principle. Addressing these will require a concerted effort, but will result in a more robust, maintainable, and compliant codebase.

## Context and Orientation

The project is a FastAPI application with a Python backend and a vanilla JavaScript frontend. The backend is organized by domain (`budgeting`, `core`, etc.), and the frontend code resides in `src/dojo/frontend/static/`. The project's rules are documented in `AGENTS.md` and the `docs/rules/` directory.

## Plan of Work



### 1. Python Backend Violations

#### 1.1. Global `app` Object

**Location:** `src/dojo/core/app.py`

**Violation:** A global `app` object is created by calling `create_app()`. `docs/rules/python.md` states: "Page modules must not hold globals or singletons."

**Remediation:**
1.  Remove the line `app = create_app()`.
2.  Update the application server configuration (e.g., uvicorn command in a run script) to call the `create_app` factory directly, like `uvicorn my_project.main:create_app --factory`.

**Status (2025-11-23):** ✅ Removed the global instantiation, updated all docs/scripts (README, plans, Cypress harness) to use `uvicorn dojo.core.app:create_app --factory`, and added a lightweight `/api/testing/*` fallback handler so production builds still return 404 instead of 405.

#### 1.2. `from __future__ import annotations`

**Location:** `src/dojo/budgeting/services.py`

**Violation:** The file uses `from __future__ import annotations`, which is explicitly forbidden in `docs/rules/python.md`.

**Remediation:**
1.  Remove the line `from __future__ import annotations`.
2.  Update any type hints that rely on this feature to use string forward references (e.g., `def my_func(a: 'MyClass') -> 'MyClass':`) or move the type hint to a place where the type has been defined.

**Status (2025-11-23):** ✅ Dropped the future import and tightened the type system by casting union values into the literal domains (`AccountState`, `BudgetCategoryDetail`, etc.) so pyright is happy without postponed evaluation.

#### 1.3. Mixing Business Logic and Data Access

**Location:** `src/dojo/*/services.py`

**Violation:** Service modules directly execute SQL queries, mixing business logic with data access. This is a systemic issue. Any service needing database access must go through a Data Access Object (DAO). The `budgeting` service was one example of this violation.

**Remediation:**
1. Create a new `dao.py` (Data Access Object) file within each domain (e.g., `src/dojo/budgeting/dao.py`).
2. Move all `conn.execute()` calls and SQL loading logic from the service files into corresponding methods in the DAO files.
3. Refactor the service methods to call the DAO methods, separating the business logic from the data access.

**Status (2025-11-23):** ✅ All service modules now route through explicit DAOs. Budgeting continues to lean on `BudgetingDAO`, testing utilities call `TestingDAO.run_script`, and the new `CoreDAO` drives the net worth snapshot so no service or router executes SQL directly.

**Notes (2025-11-23):**
- `BudgetingDAO` owns the reference-data queries, so `/api/budget/reference-data` no longer reads `.sql` files inside the router and all DTO coercion stays within the service boundary.
- Added `dojo/core/dao.py` plus typed records to back the net-worth service, ensuring core routers can only see rich objects instead of tuple unpacking.
- Verified with `rg "execute\(" -g"*services.py"` that the services layer remains SQL-free; future data access should extend the DAO objects instead of mixing concerns.

#### 1.4. Magic Numbers and Strings

**Location:** Various modules, including `src/dojo/core/net_worth.py` and formerly `src/dojo/budgeting/services.py`.

**Violation:** The code uses magic numbers or positional unpacking to access tuple elements from database rows. This violates the principle of "Prefer objects over dictionaries for structured data" from `docs/rules/python.md`. Any module directly executing database queries without mapping results to data classes is a potential source of this violation.

**Remediation:**
1. Define `dataclasses` or Pydantic `BaseModel` classes that correspond to the structure of the database rows.
2. In the data access layer (DAO), map the raw tuple results from the database into these data classes.
3. Refactor the service layer to use the data classes, accessing attributes by name (e.g., `my_row.account_id`) instead of by index.

**Status (2025-11-23):** ⚠️ **Partially remediated.** The `budgeting` DAO now returns rich dataclasses, resolving the issue for that service. However, other parts of the code, like `src/dojo/core/net_worth.py`, still use positional unpacking. This pattern must be replaced by mapping raw results to data classes within a DAO.

#### 1.5. Complex Functions

**Location:** System-wide, exemplified in `src/dojo/budgeting/services.py`.

**Violation:** Functions are often overly long and complex, handling multiple responsibilities like validation, data access, and business logic in one place. This is a general code health issue that needs to be addressed wherever it is found.

**Remediation:**
1.  Break down these large functions into smaller, more focused private methods within the service class. For example, `create` could be broken down into `_validate_create_request`, `_build_transaction_response`, etc.
2.  Each smaller function should have a single responsibility.

**Status (2025-11-23):** ⚠️ **Partially remediated.** The transaction and allocation flows within the `budgeting` service have been refactored into smaller, more focused methods. This approach should be applied to other complex functions throughout the codebase during refactoring efforts.

#### 1.6. Inline SQL

**Location:** System-wide. Previously found in `src/dojo/budgeting/services.py`. Also present in `src/dojo/budgeting/routers.py`.

**Violation:** Modules other than DAOs contain inline SQL, and complex queries are not always externalized into `.sql` files as required by `docs/rules/sql.md`. For instance, `src/dojo/budgeting/routers.py` contains inline SQL, which is also a layer violation.

**Remediation:**
1.  Extract the inline SQL from these methods into new `.sql` files in the appropriate directory (e.g., `sql/budgeting/upsert_credit_payment_group.sql`).
2.  Update the methods to use the `load_sql` function to load the queries from the new files.

**Status (2025-11-23):** ✅ All budgeting SQL now lives inside DAOs. The reference-data endpoint consumes the new `BudgetingDAO` helpers, so no router or service layer reaches for `.sql` files directly.

### 2. Frontend Violations

#### 2.1. Monolithic Structure

**Location:** `src/dojo/frontend/static/app.js`, `src/dojo/frontend/static/styles.css`

**Violation:** The entire frontend is contained in two monolithic files, violating the "Domain-Driven Structure" and "Component-Based Architecture" principles in `docs/rules/frontend.md`.

**Remediation:**
1. Create a new directory structure under `src/dojo/frontend/` that reflects a component-based architecture (e.g., `components/`, `services/`).
2. Break down `app.js` into smaller modules. For example, create a `services/api.js` for API calls, a `services/state.js` for state management, and then a directory for each component (e.g., `components/transaction-list/`).
3. Each component directory should contain its own JavaScript and CSS file.

**Status (2025-11-23):** ✅ Split the original monolith into `services/`, `components/`, and `store` modules (`main.js` now wires accounts, budgets, transactions, transfers, allocations, router, toast, and reference data) with per-feature CSS bundles under `styles/components/` so each page owns its structure and presentation.

#### 2.2. Global State Mutation

**Location:** `src/dojo/frontend/static/app.js`

**Violation:** The global `state` object is mutated directly.

**Remediation:**
1.  Implement a simple state management pattern in `services/state.js`. This could be a class or a set of functions that manage the state.
2.  The state management module should expose a `getState()` function and a `setState()` function.
3.  `setState()` should be the only way to update the state, and it should always create a new state object instead of mutating the old one.
4.  Refactor the rest of the code to use these functions for state management.

**Status (2025-11-23):** ✅ Added `services/state.js` plus a shared `store.js` instance; every feature now reads via `store.getState()` and mutates via `store.setState`/`patchState`, which emit copies so DOM updates no longer rely on hidden shared references.

#### 2.3. No BEM in CSS

**Location:** `src/dojo/frontend/static/styles.css`

**Violation:** The CSS does not consistently use the BEM naming convention.

**Remediation:**
1.  As part of the component refactoring, rename all CSS classes to follow the BEM convention. For example, `.account-card__header` should be the standard.
2.  Each component should have its own CSS file with styles scoped to that component.

**Status (2025-11-23):** ✅ Replaced the single stylesheet with `base.css`, `layout.css`, shared form/ledger styles, and page-specific files under `styles/components/`, updating the markup to use explicit BEM/utility classes (`app-header__link`, `form-panel__field`, `u-muted`, etc.) so styling responsibilities live with their respective components.

### 3. Temporal Data Model Violations

**Problem:** The immutability principle of the temporal data model is being violated.

**Location:** `src/dojo/budgeting/services.py`

**Violation:**
1.  In the `create` method, the reversal of a previous transaction is not performed in the same atomic transaction as the insertion of the new one.
2.  The use of `update_account_balance.sql` and `upsert_category_monthly_state.sql` suggests that some tables are being updated in place, which may violate the temporal data model rules if these tables are considered temporal.

**Remediation:**
1.  Refactor the `create` method to ensure that the entire process of closing an old transaction and creating a new one is wrapped in a single `BEGIN`/`COMMIT` block.
2.  Investigate the schema of the `accounts` and `category_monthly_state` tables. If they are intended to be temporal, they must be converted to follow the SCD Type 2 pattern (i.e., using `is_active` flags and inserting new rows for updates). If they are not temporal, this should be explicitly documented.

**Status (2025-11-23):** ✅ Added a `BudgetingDAO.transaction()` context manager and updated `TransactionEntryService.create` to run reversals, closures, and inserts inside a single atomic block. The new unit test `test_edit_transaction_failure_rolls_back` proves that a forced failure leaves both the ledger and cache unchanged, and the Accounts/Budgeting data-model docs now explicitly describe `accounts` and `budget_category_monthly_state` as mutable caches outside the temporal history.

### 4. Data Model Invariant Violations & Property Test Gaps

A review of the property tests in `tests/property/` against the data model documentation in `docs/data-model/` reveals significant gaps in testing coverage. While some invariants are tested, many critical business logic and data integrity rules are not guaranteed by property tests. This poses a risk to data consistency and correctness.

The existing tests (`test_transactions_properties.py` and `test_net_worth_properties.py`) provide a good starting point, but are insufficient.

-   `test_account_balance_matches_sum` partially covers account balance synchronization but only for new transactions on a single, hardcoded account.
-   `test_only_one_active_version_per_concept` correctly verifies the uniqueness of active transaction versions.
-   `test_net_worth_matches_manual_computation` appears to reveal a bug in the net worth calculation, where investment positions are not correctly incorporated into asset totals. The test itself has a flawed assertion about how net worth is calculated.

The following sections detail the missing property tests required to validate the documented invariants for each service.

#### 4.1. Accounts Service Invariants (`docs/data-model/accounts-service.md`)

-   **Violation:** The core invariants for the Accounts service are not covered by property tests.
-   **Remediation:**
    1.  **Balance Synchronization:** Create a property test that generates a series of transactions (creations, updates, and deletions) across multiple accounts and verifies that `accounts.current_balance_minor` is always equal to the sum of the corresponding transactions.
    2.  **One-to-One Details:** Create a property test that generates accounts of various classes and ensures that exactly one corresponding record is created in the correct `*_account_details` table.
    3.  **Credit Account Categories:** Create a property test that creates a credit account and verifies that a corresponding "Credit Card Payment" budget category is also created.

#### 4.2. Budgeting Service Invariants (`docs/data-model/budgeting-service.md`)

-   **Violation:** None of the budgeting service's primary invariants are covered by property tests.
-   **Remediation:**
    1.  **Conservation of Money:** Create a property test that performs random reallocations between budget categories within a month and asserts that the sum of all `available_minor` balances remains constant.
    2.  **Cache Correctness:** Create a property test that generates a history of transactions for a given month and verifies that the `allocated_minor`, `inflow_minor`, `activity_minor`, and `available_minor` columns in the `budget_category_monthly_state` table match the values derived directly from the `transactions` and `budget_allocations` tables.
    3.  **Group-Category Relationship:** Create a property test to verify that every `budget_category` has a valid `group_id` linking it to a `budget_category_group`.

#### 4.3. Investments Service Invariants (`docs/data-model/investments-service.md`)

-   **Violation:** Investment-related invariants are completely untested. The existing net worth test suggests the implementation may be incorrect.
-   **Remediation:**
    1.  **Account Balance Synchronization:** Create a property test that generates investment positions (buys, sells) for an investment account and verifies that the account's `current_balance_minor` in the `accounts` table correctly reflects the sum of the `market_value_minor` of all active positions.
    2.  **Position Uniqueness:** Create a property test to ensure that for any given `account_id`, there is only one active position per instrument.
    3.  **Account Class:** Create a property test to ensure that positions can only be created for accounts with an `account_class` of `investment`.

#### 4.4. Transactions Service Invariants (`docs/data-model/transactions-service.md`)

-   **Violation:** While the uniqueness of the active version is tested, other critical invariants are not.
-   **Remediation:**
    1.  **Chronological Integrity:** Create a property test that performs multiple edits on a single transaction and verifies that the `valid_from` and `valid_to` timestamps are always correctly ordered, with no overlaps or gaps.
    2.  **Referential Integrity:** Create a property test that attempts to create transactions pointing to non-existent or inactive `account_id`s and `category_id`s and asserts that the operation fails as expected.

## Validation and Acceptance

- All `ruff` and `pyright` checks must pass.
- All existing unit and e2e tests must pass.
- For each remediation, new unit tests should be added to verify the fix and prevent regressions.
- A manual review of the application should be conducted to ensure that all functionality remains intact after the refactoring.

## Artifacts and Notes

**Example of Inline SQL Violation:**
```python
# From src/dojo/budgeting/services.py
def _ensure_credit_payment_group(self, conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        INSERT INTO budget_category_groups (group_id, name, sort_order)
        VALUES (?, ?, ?)
        ON CONFLICT (group_id) DO UPDATE
        SET name = EXCLUDED.name,
            sort_order = EXCLUDED.sort_order,
            is_active = TRUE,
            updated_at = NOW()
        """,
        [CREDIT_PAYMENT_GROUP_ID, CREDIT_PAYMENT_GROUP_NAME, CREDIT_PAYMENT_GROUP_SORT_ORDER],
    )
```

**Example of Magic Number Violation:**
```python
# From src/dojo/budgeting/services.py
def _row_to_category(self, row: Tuple[Any, ...]) -> BudgetCategoryDetail:
    # ...
    if len(row) >= 15:
        last_month_allocated = int(row[13])
        last_month_activity = int(row[14])

    return BudgetCategoryDetail(
        category_id=row[0],
        group_id=row[1],
        name=row[2],
        # ...
    )
```
