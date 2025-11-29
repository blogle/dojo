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

## 2. Phase 1: Frontend Development - Shared "Editable Ledger" Component

### Objective
Create a reusable and configurable frontend component that allows inline editing of tabular data, supporting various input types and providing optimistic UI updates.

### Tasks
1.  **Component Scaffolding:**
    *   Create a base React component (`EditableLedgerTable` or similar) capable of rendering data based on a provided `columns` definition and `data` array.
    *   Implement basic table structure and styling consistent with existing UI patterns.
2.  **Inline Editing Implementation:**
    *   Develop a click-to-edit mechanism for table cells.
    *   Integrate various input widgets based on column `type` definitions:
        *   `CurrencyInput`: For decimal precision formatting (e.g., `react-number-format` or similar).
        *   `Dropdown`: For relational data selection (Accounts, Categories). Must include search/filtering capabilities.
        *   `StatusToggle`: Compact `Pending/Cleared` widget.
        *   `DatePicker`: For transaction dates.
    *   Manage local component state for pending edits.
3.  **Row-Level State Management:**
    *   Ensure that when an edit occurs, the component captures the `conceptual_id` (e.g., `transaction_id`, `budget_allocation_id`) of the row, rather than the database primary key of the specific history version.
    *   Implement a mechanism to track changes at the row level until "Save" is triggered.
4.  **Optimistic UI Handling:**
    *   Upon a successful API response (after a row save), update the specific row in the table with the new data and version metadata returned by the backend.
    *   Avoid full page refreshes; ensure a smooth, localized UI update.
    *   Implement loading indicators and error states for individual row saves.

### Acceptance Criteria
*   The `EditableLedgerTable` component successfully renders provided data.
*   Users can inline-edit cells using appropriate input widgets (currency, dropdowns, toggles, date pickers).
*   Changes are tracked per row using the conceptual ID.
*   Successful row saves result in an optimistic UI update with new data without page refresh.
*   Error states and loading indicators are displayed correctly during save operations.

---

## 3. Phase 2: Backend Development - SCD-2 Write Pattern ("The Correction Flow")

### Objective
Implement a non-destructive update mechanism in the backend using the SCD-2 pattern, ensuring data integrity and historical traceability for ledger modifications.

### Tasks
1.  **Identify Relevant Tables:**
    *   Confirm the primary tables requiring SCD-2, initially `transactions` and `budget_allocations`.
2.  **Schema Modification:**
    *   Add SCD-2 specific columns to identified tables:
        *   `is_active` (BOOLEAN, default TRUE): Indicates the currently active record.
        *   `recorded_at` (TIMESTAMP WITH TIME ZONE, default NOW()): Timestamp of when the record was created/modified.
        *   `changed_by` (TEXT): Identifier for the user or system component making the change.
    *   Ensure proper indexing for `conceptual_id` and `is_active` for efficient querying.
3.  **API Endpoint Design:**
    *   Design and implement `PUT` endpoints for updating ledger rows (e.g., `PUT /transactions/{transaction_id}`, `PUT /budget_allocations/{allocation_id}`).
    *   The payload should contain the `conceptual_id` and the new field values.
4.  **Atomic Update Transaction Logic:**
    *   Within a single `BEGIN...COMMIT` database transaction block:
        *   **Lock & Fetch:** Retrieve the currently active row for the given `conceptual_id` using a row-level lock (`SELECT ... FOR UPDATE`) to prevent race conditions.
        *   **Soft Retire:** Update the fetched active row by setting its `is_active = FALSE`.
        *   **Insert New Version:** Insert a completely new row with:
            *   The same `conceptual_id`.
            *   The new user-provided values.
            *   `is_active = TRUE`.
            *   `recorded_at = NOW()`.
            *   `changed_by = {current_user}`.
    *   Handle `ROLLBACK` on any failure during the transaction.

### Acceptance Criteria
*   New SCD-2 columns (`is_active`, `recorded_at`, `changed_by`) are added to relevant tables.
*   API endpoints for ledger updates are defined and accessible.
*   A request to "edit" a ledger row successfully executes an atomic transaction:
    *   The previously active row is soft-retired (`is_active = FALSE`).
    *   A new row with updated values is inserted and marked as active (`is_active = TRUE`).
    *   `recorded_at` and `changed_by` are correctly populated.
*   Concurrent update attempts are safely handled (e.g., via locking).

---

## 4. Phase 3: Validation Logic - "Net Impact" Rule

### Objective
Implement a robust validation engine that calculates the net impact of a proposed change, treating the "Old Version" as virtually credited back before debiting the "New Version," preventing false negatives in scenarios like reallocations.

### Tasks
1.  **Integrate Validation:**
    *   Place the "Net Impact" validation logic *within* the atomic update transaction in the backend, prior to the `Soft Retire` and `Insert New Version` steps. This ensures validation is based on the most current data.
2.  **Calculate Delta:**
    *   For a given update, calculate the `Delta` for relevant numeric fields (e.g., `amount` for transactions, `allocation_value` for budgets).
    *   `Delta = New Value - Old Value`.
3.  **Implement Validation Rule:**
    *   Retrieve the `Current Available` funds/balance relevant to the transaction/allocation being modified.
    *   Apply the validation: `Current Available - Delta` must result in a value greater than or equal to zero (or some defined minimum threshold).
    *   If validation fails, `ROLLBACK` the entire transaction and return an appropriate error message to the frontend.
    *   Explicitly handle the "Old Version" being virtually credited back: `Current Available - (New Value - Old Value) >= 0` effectively becomes `(Current Available + Old Value) - New Value >= 0`.
4.  **Scenario Handling:**
    *   Specifically address the "Reallocation with Zero Availability" scenario to ensure the logic correctly allows a reduction in allocation even if `Ready to Assign` is currently zero.

### Acceptance Criteria
*   All ledger update requests pass through the "Net Impact" validation.
*   The `Delta` is correctly calculated for modified fields.
*   The validation logic correctly determines if an operation is permissible based on the `Current Available` funds and the `Net Impact` of the change.
*   The "Reallocation with Zero Availability" scenario (reducing an allocation when available funds are zero) passes validation successfully.
*   Invalid changes are rejected with clear error messages.

---

## 5. Phase 4: Testing Strategy

### Objective
Ensure the correctness, robustness, and adherence to all specified requirements for both frontend and backend components.

### Tasks
1.  **Unit Tests:**
    *   **Frontend:**
        *   Test `EditableLedgerTable` component rendering with various data and column configurations.
        *   Test inline editing functionality for each input type.
        *   Verify row-level state management and conceptual ID capture.
        *   Simulate API responses to test optimistic UI updates, loading states, and error handling.
    *   **Backend:**
        *   Test individual functions responsible for locking, soft-retiring, and inserting new versions in isolation.
        *   Test `Delta` calculation logic for various inputs.
        *   Test "Net Impact" validation logic with valid, invalid, and edge-case scenarios (e.g., zero availability reallocation).
2.  **Integration Tests:**
    *   **Backend API:**
        *   Test the full `PUT` API endpoints, verifying that the atomic SCD-2 transaction correctly executes (old row `is_active=FALSE`, new row inserted `is_active=TRUE`).
        *   Verify that "Net Impact" validation is triggered and correctly prevents/allows changes.
        *   Test concurrent update scenarios to ensure locking mechanisms work as expected.
    *   **Frontend-Backend Interaction:**
        *   Use mock API calls in frontend tests or spin up a test backend to verify the full flow: user edit -> API call -> optimistic UI update -> (optional) error display.
3.  **End-to-End (E2E) Tests (Cypress):**
    *   Create new Cypress tests in `cypress/e2e/user-stories/` or modify existing ones to cover key user flows:
        *   Editing a transaction's amount and category, observing the SCD-2 effect (UI updates, backend reflects new active record).
        *   Editing a budget allocation and verifying the "Net Impact" rule, especially the reallocation scenario with zero availability.
        *   Testing error handling when validation fails.

### Acceptance Criteria
*   All unit, integration, and E2E tests pass consistently.
*   Test coverage for new/modified code meets project standards.
*   E2E tests confirm that critical user stories for editing ledger data behave as expected from the user's perspective, including visual updates and correct validation.

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