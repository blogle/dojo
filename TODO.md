- **Title:** Research Off-the-Shelf DuckDB Migration Tool
- **Priority:** P2
- **Effort:** Small
- **Trigger:** Discussion during MVP planning for the auditable ledger revealed the risk of maintaining a custom migration script.
- **Why defer:** The custom script is sufficient for the MVP, and building the core feature is the current priority.
- **Proposed next step:** Dedicate a short timebox to survey the ecosystem for existing Python-based DuckDB migration tools.
- **Acceptance Criteria:** A decision document or update to `ARCHITECTURE.md` recommending a tool or confirming that a custom script remains the best option.
- **Links:** `docs/plans/auditable-ledger-net-worth.md`

---

- **Title:** Replace bare `except Exception` with specific exception handling
- **Priority:** P0
- **Effort:** Medium
- **Trigger:** Codebase analysis identified bare `except Exception` blocks in `src/dojo/budgeting/dao.py` (`BudgetingDAO.transaction`) and `src/dojo/budgeting/services.py`, violating `docs/rules/python.md`.
- **Why defer:** Discovered during a general codebase assessment, prioritizing documentation.
- **Proposed next step:** Replace `except Exception:` with specific `except duckdb.Error as exc:` in `BudgetingDAO.transaction` and relevant service methods. Ensure proper error logging and re-raising of domain-specific exceptions where appropriate.
- **Acceptance Criteria:** No bare `except Exception` found in `src/dojo/budgeting/dao.py` or `src/dojo/budgeting/services.py`. All tests pass.
- **Links:** `src/dojo/budgeting/dao.py`, `src/dojo/budgeting/services.py`, `docs/rules/python.md`

---

- **Title:** Refactor service methods to use `BudgetingDAO.transaction` context manager
- **Priority:** P1
- **Effort:** Large
- **Trigger:** Codebase analysis identified repetitive `dao.begin()`, `dao.commit()`, `dao.rollback()` blocks across various methods in `src/dojo/budgeting/services.py`. The `BudgetingDAO` already provides a `transaction` context manager.
- **Why defer:** Focus was on initial feature implementation and documentation.
- **Proposed next step:** Modify all methods in `src/dojo/budgeting/services.py` that perform multiple database write operations within a single logical unit to use `with dao.transaction():`.
- **Acceptance Criteria:** Elimination of manual `begin/commit/rollback` sequences in `src/dojo/budgeting/services.py`. All tests pass.
- **Links:** `src/dojo/budgeting/dao.py`, `src/dojo/budgeting/services.py`

---

- **Title:** Centralize duplicated `_coerce_month_start` and common validation logic
- **Priority:** P2
- **Effort:** Small
- **Trigger:** Codebase analysis identified duplication of `_coerce_month_start` and `MAX_FUTURE_DAYS` validation across service classes in `src/dojo/budgeting/services.py`.
- **Why defer:** Part of a general code quality improvement, not blocking critical functionality.
- **Proposed next step:** Create a new utility module (e.g., `dojo.core.utils` or `dojo.budgeting.utils`) and move `_coerce_month_start` and other common validation functions there. Update all call sites to use the centralized utility.
- **Acceptance Criteria:** No duplicate `_coerce_month_start` or `MAX_FUTURE_DAYS` validation logic in service files. All tests pass.
- **Links:** `src/dojo/budgeting/services.py`

---

- **Title:** Extract `category_id` generation logic into a dedicated helper
- **Priority:** P2
- **Effort:** Small
- **Trigger:** Codebase analysis identified imperative `category_id` generation logic in `BudgetCategoryAdminService.create_category`.
- **Why defer:** Part of general code quality improvement.
- **Proposed next step:** Extract the `category_id` generation logic into a standalone, testable helper function (e.g., in a new `dojo.budgeting.utils` module) and replace the inline logic with a call to this helper.
- **Acceptance Criteria:** `BudgetCategoryAdminService.create_category` uses a dedicated helper for ID generation. All tests pass.
- **Links:** `src/dojo/budgeting/services.py`

---

- **Title:** Decompose large service classes in `src/dojo/budgeting/services.py`
- **Priority:** P3
- **Effort:** Large
- **Trigger:** Codebase analysis identified `TransactionEntryService`, `AccountAdminService`, and `BudgetCategoryAdminService` as overly large, indicating a "God Object" code smell.
- **Why defer:** This is a refactoring task that requires careful planning and incremental changes; not a blocking issue for current functionality.
- **Proposed next step:** Identify distinct responsibilities within these classes (e.g., account creation, transaction processing, category goal management) and refactor them into smaller, more focused service classes.
- **Acceptance Criteria:** Service classes in `src/dojo/budgeting/services.py` have reduced lines of code and more focused responsibilities. All tests pass.
- **Links:** `src/dojo/budgeting/services.py`- **Title:** Research Off-the-Shelf DuckDB Migration Tool
- **Priority:** P2
- **Effort:** Small
- **Trigger:** Discussion during MVP planning for the auditable ledger revealed the risk of maintaining a custom migration script.
- **Why defer:** The custom script is sufficient for the MVP, and building the core feature is the current priority.
- **Proposed next step:** Dedicate a short timebox to survey the ecosystem for existing Python-based DuckDB migration tools.
- **Acceptance Criteria:** A decision document or update to `ARCHITECTURE.md` recommending a tool or confirming that a custom script remains the best option.
- **Links:** `docs/plans/auditable-ledger-net-worth.md`

---

- **Title:** Replace bare `except Exception` with specific exception handling
- **Priority:** P0
- **Effort:** Medium
- **Trigger:** Codebase analysis identified bare `except Exception` blocks in `src/dojo/budgeting/dao.py` (`BudgetingDAO.transaction`) and `src/dojo/budgeting/services.py`, violating `docs/rules/python.md`.
- **Why defer:** Discovered during a general codebase assessment, prioritizing documentation.
- **Proposed next step:** Replace `except Exception:` with specific `except duckdb.Error as exc:` in `BudgetingDAO.transaction` and relevant service methods. Ensure proper error logging and re-raising of domain-specific exceptions where appropriate.
- **Acceptance Criteria:** No bare `except Exception` found in `src/dojo/budgeting/dao.py` or `src/dojo/budgeting/services.py`. All tests pass.
- **Links:** `src/dojo/budgeting/dao.py`, `src/dojo/budgeting/services.py`, `docs/rules/python.md`

---

- **Title:** Refactor service methods to use `BudgetingDAO.transaction` context manager
- **Priority:** P1
- **Effort:** Large
- **Trigger:** Codebase analysis identified repetitive `dao.begin()`, `dao.commit()`, `dao.rollback()` blocks across various methods in `src/dojo/budgeting/services.py`. The `BudgetingDAO` already provides a `transaction` context manager.
- **Why defer:** Focus was on initial feature implementation and documentation.
- **Proposed next step:** Modify all methods in `src/dojo/budgeting/services.py` that perform multiple database write operations within a single logical unit to use `with dao.transaction():`.
- **Acceptance Criteria:** Elimination of manual `begin/commit/rollback` sequences in `src/dojo/budgeting/services.py`. All tests pass.
- **Links:** `src/dojo/budgeting/dao.py`, `src/dojo/budgeting/services.py`

---

- **Title:** Centralize duplicated `_coerce_month_start` and common validation logic
- **Priority:** P2
- **Effort:** Small
- **Trigger:** Codebase analysis identified duplication of `_coerce_month_start` and `MAX_FUTURE_DAYS` validation across service classes in `src/dojo/budgeting/services.py`.
- **Why defer:** Part of a general code quality improvement, not blocking critical functionality.
- **Proposed next step:** Create a new utility module (e.g., `dojo.core.utils` or `dojo.budgeting.utils`) and move `_coerce_month_start` and other common validation functions there. Update all call sites to use the centralized utility.
- **Acceptance Criteria:** No duplicate `_coerce_month_start` or `MAX_FUTURE_DAYS` validation logic in service files. All tests pass.
- **Links:** `src/dojo/budgeting/services.py`

---

- **Title:** Extract `category_id` generation logic into a dedicated helper
- **Priority:** P2
- **Effort:** Small
- **Trigger:** Codebase analysis identified imperative `category_id` generation logic in `BudgetCategoryAdminService.create_category`.
- **Why defer:** Part of general code quality improvement.
- **Proposed next step:** Extract the `category_id` generation logic into a standalone, testable helper function (e.g., in a new `dojo.budgeting.utils` module) and replace the inline logic with a call to this helper.
- **Acceptance Criteria:** `BudgetCategoryAdminService.create_category` uses a dedicated helper for ID generation. All tests pass.
- **Links:** `src/dojo/budgeting/services.py`

---

- **Title:** Decompose large service classes in `src/dojo/budgeting/services.py`
- **Priority:** P3
- **Effort:** Large
- **Trigger:** Codebase analysis identified `TransactionEntryService`, `AccountAdminService`, and `BudgetCategoryAdminService` as overly large, indicating a "God Object" code smell.
- **Why defer:** This is a refactoring task that requires careful planning and incremental changes; not a blocking issue for current functionality.
- **Proposed next step:** Identify distinct responsibilities within these classes (e.g., account creation, transaction processing, category goal management) and refactor them into smaller, more focused service classes.
- **Acceptance Criteria:** Service classes in `src/dojo/budgeting/services.py` have reduced lines of code and more focused responsibilities. All tests pass.
- **Links:** `src/dojo/budgeting/services.py`