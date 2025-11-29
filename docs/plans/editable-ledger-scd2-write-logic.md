# ExecPlan: Editable Ledger Tables and SCD-2 Write Logic

## 1. Overview

### Problem Statement
The application currently lacks a unified and non-destructive mechanism for users to view and modify high-density tabular data, specifically within the Transactions and Budget Allocations domains. Existing update patterns may lead to data loss or incorrect historical accounting.

### Proposed Solution
Develop a shared, reusable frontend "Editable Ledger" UI component coupled with a robust backend implementation of the Slowly Changing Dimension Type 2 (SCD-2) pattern for handling data modifications. This approach ensures that all changes are non-destructive, maintaining a full audit trail of historical data. Furthermore, a "Net Impact" validation rule will be integrated to prevent false negatives during reallocation scenarios.

### Goals
*   Provide a consistent and intuitive user experience for editing tabular data.
*   Implement a non-destructive data modification strategy (SCD-2) in the backend.
*   Ensure data integrity and traceability for all ledger changes.
*   Prevent invalid state transitions through intelligent "Net Impact" validation.

---

## 2. Phase 1: Backend Foundation (Database & Schema)

### Context:
The `transactions` table already supports SCD-2 columns (`concept_id`, `is_active`, `valid_from/to`), but the `budget_allocations` table (`0006_budget_allocations.sql`) does not. It needs to be brought up to parity to support non-destructive edits.

### Tasks
*   **Task 1.1: Migration for Budget Allocations SCD-2**
    *   **Description:** Create a new SQL migration file (e.g., `0011_allocation_scd2.sql`) to alter the `budget_allocations` table.
    *   **Requirements:**
        *   Add column `concept_id` (UUID, Not Null). Backfill existing rows by generating new UUIDs or using `allocation_id` if suitable.
        *   Add column `is_active` (BOOLEAN, Default TRUE).
        *   Add column `recorded_at` (TIMESTAMP, Default CURRENT_TIMESTAMP).
        *   Add column `valid_from` (TIMESTAMP, Default CURRENT_TIMESTAMP).
        *   Add column `valid_to` (TIMESTAMP, Default '9999-12-31').
        *   Create index on `(concept_id, is_active)`.
    *   **Deliverable:** A `.sql` migration file in `src/dojo/sql/migrations/`.

*   **Task 1.2: SQL Query for Atomic Transaction Updates**
    *   **Description:** Write the SQL Transaction script to handle the "Correction Flow" for general Transactions.
    *   **Requirements:**
        *   Accept parameters for new values and the target `concept_id`.
        *   Use a transaction block (`BEGIN...COMMIT`).
        *   `UPDATE`: Set `is_active = FALSE`, `valid_to = NOW()` for the current active row matching `concept_id`.
        *   `INSERT`: Create a new row with new values, same `concept_id`, `is_active = TRUE`.
    *   **Deliverable:** A new SQL file `src/dojo/sql/budgeting/update_transaction_scd2.sql`.

*   **Task 1.3: SQL Query for Atomic Allocation Updates**
    *   **Description:** Write the SQL Transaction script to handle the "Correction Flow" for Budget Allocations.
    *   **Requirements:**
        *   Similar logic to Task 1.2 but targeting the `budget_allocations` table.
    *   **Deliverable:** A new SQL file `src/dojo/sql/budgeting/update_allocation_scd2.sql`.

---

## 3. Phase 2: Backend Logic & API

### Context:
Implement the endpoints that utilize the SQL queries from Phase 1.

### Tasks
*   **Task 2.1: Transaction Update Service Method**
    *   **Description:** Add a method `update_transaction` to `TransactionEntryService`.
    *   **Requirements:**
        *   Accept `concept_id` and a Pydantic model `TransactionUpdateRequest`.
        *   Execute the SQL from Task 1.2.
        *   Ensure the operation is atomic.
    *   **Deliverable:** Python method in `src/dojo/budgeting/services.py`.

*   **Task 2.2: PUT Endpoint for Transactions**
    *   **Description:** Create the API route to expose the update logic.
    *   **Requirements:**
        *   `PUT /api/transactions/{concept_id}`.
        *   Validate payload using `TransactionUpdateRequest` schema.
        *   Call `service.update_transaction`.
    *   **Deliverable:** Updated `src/dojo/budgeting/routers.py`.

*   **Task 2.3: Allocation Update Service Method**
    *   **Description:** Add a method `update_allocation` to `TransactionEntryService` (or a dedicated `BudgetingService`).
    *   **Requirements:**
        *   Accept `concept_id` and `BudgetAllocationUpdateRequest`.
        *   Execute the SQL from Task 1.3.
    *   **Deliverable:** Python method in `src/dojo/budgeting/services.py`.

*   **Task 2.4: PUT Endpoint for Allocations**
    *   **Description:** Create the API route for updating allocations.
    *   **Requirements:**
        *   `PUT /api/budget/allocations/{concept_id}`.
        *   Validate payload.
    *   **Deliverable:** Updated `src/dojo/budgeting/routers.py`.

---

## 4. Phase 3: Validation Logic ("Net Impact")

### Context:
Prevent updates that would result in negative availability (e.g., reducing a funded category below 0).

### Tasks
*   **Task 3.1: Implement Net Impact Logic for Allocations**
    *   **Description:** Within the `update_allocation` service method, strictly validate the math before committing.
    *   **Logic:**
        1.  Fetch currently active `amount_minor` (Old).
        2.  Calculate `Delta = New_Amount - Old_Amount`.
        3.  Fetch `Ready to Assign` (RTA) and `Category Available`.
        4.  If `Delta > 0` (increasing allocation): Ensure `RTA >= Delta`.
        5.  If `Delta < 0` (decreasing allocation): Ensure `Category Available >= abs(Delta)`. *Correction from plan: effectively "reclaiming" funds.*
    *   **Deliverable:** Validation logic block inside the service method in `src/dojo/budgeting/services.py`.

*   **Task 3.2: Implement Net Impact Logic for Transactions**
    *   **Description:** Validate transaction updates to prevent impossible states (though less critical than allocations, usually specific to account overdrafts if enforced).
    *   **Logic:** Calculate `Delta` and check against account balance (optional depending on business rules) or Category Availability (critical).
    *   **Deliverable:** Validation logic in `src/dojo/budgeting/services.py`.

---

## 5. Phase 4: Frontend (Shared Editable Utility)

### Context:
The codebase uses vanilla JS. We need to refactor the existing specific logic in `transactions/index.js` into a reusable module.

### Tasks
*   **Task 4.1: Extract `hydrateInlineEditRow` to Utility**
    *   **Description:** Move the logic for converting a table row `<tr>` into inputs from `components/transactions/index.js` to a new module `services/ui-ledger.js`.
    *   **Requirements:**
        *   Create `makeRowEditable(trElement, config)`.
        *   `config` should map column indices to input types (`date`, `select`, `money`, `text`).
    *   **Deliverable:** New file `src/dojo/frontend/static/services/ui-ledger.js`.

*   **Task 4.2: Create Reusable Input Renderers**
    *   **Description:** Create helper functions to generate the HTML string for specific inputs.
    *   **Deliverable:**
        *   `renderDateInput(value)`
        *   `renderMoneyInput(minorValue)`
        *   `renderSelect(options, selectedValue)`
    *   **Deliverable:** Functions added to `src/dojo/frontend/static/services/ui-ledger.js`.

## 6. Phase 5: Frontend Integration

### Tasks
*   **Task 5.1: Refactor Transactions Page**
    *   **Description:** Update `components/transactions/index.js` to use the new `makeRowEditable` utility from Task 4.1 instead of its custom implementation.
    *   **Deliverable:** simplified `transactions/index.js`.

*   **Task 5.2: Implement Inline Editing for Allocations**
    *   **Description:** Update `components/allocations/index.js` to support inline editing.
    *   **Requirements:**
        *   Add "Edit" listeners to the allocation rows.
        *   Use `makeRowEditable` with configuration for Date, Amount, From, To, and Memo.
        *   Handle "Save" by calling the new `PUT /api/budget/allocations` endpoint.
        *   Handle optimistic UI updates (replace inputs with text on success).
    *   **Deliverable:** Updated `components/allocations/index.js`.

---

## 6. Milestones & Timeline (High-Level)

*   **M1 (Week 1-2): Frontend Editable Component MVP:**
    *   Basic `EditableLedgerTable` component with rendering and one input type (e.g., text/currency) for inline editing.
    *   Row-level state capture.
*   **M2 (Week 3-4): Backend SCD-2 Core Logic:**
    *   Schema modifications for `transactions` table.
    *   `PUT /transactions/{transaction_id}` endpoint with atomic SCD-2 logic (lock, soft-retire, insert).
*   **M3 (Week 5-6): Net Impact Validation Integrated:**
    *   "Net Impact" validation fully implemented and integrated into the `transactions` SCD-2 flow.
    *   Full test coverage for validation logic.
*   **M4 (Week 7-8): Frontend Polish & Budget Allocations Integration:**
    *   All input types implemented in `EditableLedgerTable`.
    *   Optimistic UI updates finalized.
    *   SCD-2 logic and Net Impact validation extended to `budget_allocations`.
*   **M5 (Week 9): Comprehensive Test Suite & Documentation:**
    *   Complete unit, integration, and E2E test suite.
    *   Update `ARCHITECTURE.md` and `docs/data-model/overview.md` with SCD-2 changes.

---

## 7. Open Questions / Dependencies

*   **Frontend Framework/Libraries:** Confirm current frontend framework (assuming React based on `cypress` structure). Specific libraries for currency input, date pickers, dropdowns will need to be identified or chosen if not already established within the project.
*   **SCD-2 Column Details:** Finalize exact data types, constraints, and default values for `is_active`, `recorded_at`, `changed_by` columns.
*   **Conceptual ID for Budget Allocations:** Clarify how `conceptual_id` will be identified for budget allocation rows, especially if it differs from `transaction_id`.
*   **User Identification for `changed_by`:** Determine the mechanism for reliably obtaining the `current_user` for the `changed_by` column in the backend.
*   **Error Handling Strategy:** Define specific error codes/messages for validation failures and how they will be communicated to the frontend.
*   **Access Control:** Consider if any role-based access control (RBAC) needs to be integrated with the edit functionality.