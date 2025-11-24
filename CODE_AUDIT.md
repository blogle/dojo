# Codebase Audit and Remediation Plan

This document outlines the findings of a comprehensive audit of the project's codebase against its established documentation and development rules. It categorizes all identified violations and provides a clear, actionable plan for addressing them.

## Purpose / Big Picture

The goal of this audit is to identify all areas of the codebase that deviate from the project's defined standards, as laid out in `AGENTS.md` and the `docs/rules/` directory. By systematically identifying and categorizing these violations, we can create a prioritized roadmap for bringing the codebase into full compliance. This will improve maintainability, reduce technical debt, and ensure that future development adheres to our shared engineering principles.

## Progress

- [ ] **Python Backend:** Address all violations of the Python and engineering guidelines.
- [ ] **Frontend:** Refactor the frontend to align with the component-based, stateless architecture.
- [ ] **Temporal Data Model:** Correct all violations of the temporal data model implementation rules.
- [ ] **Documentation:** Update documentation to reflect any changes made during remediation.

## Surprises & Discoveries

- The frontend is a single, large JavaScript file (`app.js`) with a corresponding monolithic CSS file. This indicates a significant departure from the documented component-based architecture and will require a substantial refactoring effort.
- The use of a `threading.Lock` in the database connection management (`src/dojo/core/db.py`) suggests potential underlying concurrency issues that may need deeper investigation beyond a simple code fix.

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

#### 1.2. `from __future__ import annotations`

**Location:** `src/dojo/budgeting/services.py`

**Violation:** The file uses `from __future__ import annotations`, which is explicitly forbidden in `docs/rules/python.md`.

**Remediation:**
1.  Remove the line `from __future__ import annotations`.
2.  Update any type hints that rely on this feature to use string forward references (e.g., `def my_func(a: 'MyClass') -> 'MyClass':`) or move the type hint to a place where the type has been defined.

#### 1.3. Mixing Business Logic and Data Access

**Location:** `src/dojo/budgeting/services.py`

**Violation:** The service classes directly execute SQL queries, mixing business logic with data access.

**Remediation:**
1. Create a new `dao.py` (Data Access Object) file within each domain (e.g., `src/dojo/budgeting/dao.py`).
2. Move all `conn.execute()` calls and SQL loading logic from the service files into corresponding methods in the DAO files.
3. Refactor the service methods to call the DAO methods, separating the business logic from the data access.

#### 1.4. Magic Numbers and Strings

**Location:** `src/dojo/budgeting/services.py`

**Violation:** The code uses magic numbers to access tuple elements from database rows (e.g., `row[0]`, `row[7]`). This violates the principle of "Prefer objects over dictionaries for structured data" from `docs/rules/python.md`.

**Remediation:**
1. Define `dataclasses` or Pydantic `BaseModel` classes that correspond to the structure of the database rows.
2. In the data access layer (DAO), map the raw tuple results from the database into these data classes.
3. Refactor the service layer to use the data classes, accessing attributes by name (e.g., `my_row.account_id`) instead of by index.

#### 1.5. Complex Functions

**Location:** `src/dojo/budgeting/services.py`

**Violation:** Functions like `create` and `transfer` are overly long and complex, handling validation, data access, and business logic in one place.

**Remediation:**
1.  Break down these large functions into smaller, more focused private methods within the service class. For example, `create` could be broken down into `_validate_create_request`, `_build_transaction_response`, etc.
2.  Each smaller function should have a single responsibility.

#### 1.6. Inline SQL

**Location:** `src/dojo/budgeting/services.py`

**Violation:** The `_ensure_credit_payment_group` and `_ensure_credit_payment_category` methods contain complex inline SQL. `docs/rules/sql.md` requires complex queries to be in `.sql` files.

**Remediation:**
1.  Extract the inline SQL from these methods into new `.sql` files in the appropriate directory (e.g., `sql/budgeting/upsert_credit_payment_group.sql`).
2.  Update the methods to use the `load_sql` function to load the queries from the new files.

### 2. Frontend Violations

#### 2.1. Monolithic Structure

**Location:** `src/dojo/frontend/static/app.js`, `src/dojo/frontend/static/styles.css`

**Violation:** The entire frontend is contained in two monolithic files, violating the "Domain-Driven Structure" and "Component-Based Architecture" principles in `docs/rules/frontend.md`.

**Remediation:**
1. Create a new directory structure under `src/dojo/frontend/` that reflects a component-based architecture (e.g., `components/`, `services/`).
2. Break down `app.js` into smaller modules. For example, create a `services/api.js` for API calls, a `services/state.js` for state management, and then a directory for each component (e.g., `components/transaction-list/`).
3. Each component directory should contain its own JavaScript and CSS file.

#### 2.2. Global State Mutation

**Location:** `src/dojo/frontend/static/app.js`

**Violation:** The global `state` object is mutated directly.

**Remediation:**
1.  Implement a simple state management pattern in `services/state.js`. This could be a class or a set of functions that manage the state.
2.  The state management module should expose a `getState()` function and a `setState()` function.
3.  `setState()` should be the only way to update the state, and it should always create a new state object instead of mutating the old one.
4.  Refactor the rest of the code to use these functions for state management.

#### 2.3. No BEM in CSS

**Location:** `src/dojo/frontend/static/styles.css`

**Violation:** The CSS does not consistently use the BEM naming convention.

**Remediation:**
1.  As part of the component refactoring, rename all CSS classes to follow the BEM convention. For example, `.account-card__header` should be the standard.
2.  Each component should have its own CSS file with styles scoped to that component.

### 3. Temporal Data Model Violations

**Problem:** The immutability principle of the temporal data model is being violated.

**Location:** `src/dojo/budgeting/services.py`

**Violation:**
1.  In the `create` method, the reversal of a previous transaction is not performed in the same atomic transaction as the insertion of the new one.
2.  The use of `update_account_balance.sql` and `upsert_category_monthly_state.sql` suggests that some tables are being updated in place, which may violate the temporal data model rules if these tables are considered temporal.

**Remediation:**
1.  Refactor the `create` method to ensure that the entire process of closing an old transaction and creating a new one is wrapped in a single `BEGIN`/`COMMIT` block.
2.  Investigate the schema of the `accounts` and `category_monthly_state` tables. If they are intended to be temporal, they must be converted to follow the SCD Type 2 pattern (i.e., using `is_active` flags and inserting new rows for updates). If they are not temporal, this should be explicitly documented.

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
