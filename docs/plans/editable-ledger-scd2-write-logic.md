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
*   **Task 1.1: Migration for Budget Allocations SCD-2** - **COMPLETED** (Verified via `0015_ensure_scd2_columns.sql`)
    *   **Description:** Create a new SQL migration file (e.g., `0011_allocation_scd2.sql`) to alter the `budget_allocations` table.
    *   **Requirements:**
        *   Add column `concept_id` (UUID, Not Null). Backfill existing rows by generating new UUIDs or using `allocation_id` if suitable.
        *   Add column `is_active` (BOOLEAN, Default TRUE).
        *   Add column `recorded_at` (TIMESTAMP, Default CURRENT_TIMESTAMP).
        *   Add column `valid_from` (TIMESTAMP, Default CURRENT_TIMESTAMP).
        *   Add column `valid_to` (TIMESTAMP, Default '9999-12-31').
        *   Create index on `(concept_id, is_active)`.
    *   **Deliverable:** A `.sql` migration file in `src/dojo/sql/migrations/`.

*   **Task 1.2: SQL Query for Atomic Transaction Updates** - **COMPLETED**
    *   **Description:** Write the SQL Transaction script to handle the "Correction Flow" for general Transactions.
    *   **Requirements:**
        *   Accept parameters for new values and the target `concept_id`.
        *   Use a transaction block (`BEGIN...COMMIT`).
        *   `UPDATE`: Set `is_active = FALSE`, `valid_to = NOW()` for the current active row matching `concept_id`.
        *   `INSERT`: Create a new row with new values, same `concept_id`, `is_active = TRUE`.
    *   **Deliverable:** A new SQL file `src/dojo/sql/budgeting/update_transaction_scd2.sql`.

*   **Task 1.3: SQL Query for Atomic Allocation Updates** - **COMPLETED**
    *   **Description:** Write the SQL Transaction script to handle the "Correction Flow" for Budget Allocations.
    *   **Requirements:**
        *   Similar logic to Task 1.2 but targeting the `budget_allocations` table.
    *   **Deliverable:** A new SQL file `src/dojo/sql/budgeting/update_allocation_scd2.sql`.

---

## 3. Phase 2: Backend Logic & API

### Context:
Implement the endpoints that utilize the SQL queries from Phase 1.

### Tasks
*   **Task 2.1: Transaction Update Service Method** - **COMPLETED**
    *   **Description:** Add a method `update_transaction` to `TransactionEntryService`.
    *   **Requirements:**
        *   Accept `concept_id` and a Pydantic model `TransactionUpdateRequest`.
        *   Execute the SQL from Task 1.2.
        *   Ensure the operation is atomic.
    *   **Deliverable:** Python method in `src/dojo/budgeting/services.py`.

*   **Task 2.2: PUT Endpoint for Transactions** - **COMPLETED**
    *   **Description:** Create the API route to expose the update logic.
    *   **Requirements:**
        *   `PUT /api/transactions/{concept_id}`.
        *   Validate payload using `TransactionUpdateRequest` schema.
        *   Call `service.update_transaction`.
    *   **Deliverable:** Updated `src/dojo/budgeting/routers.py`.

*   **Task 2.3: Allocation Update Service Method** - **COMPLETED**
    *   **Description:** Add a method `update_allocation` to `TransactionEntryService` (or a dedicated `BudgetingService`).
    *   **Requirements:**
        *   Accept `concept_id` and `BudgetAllocationUpdateRequest`.
        *   Execute the SQL from Task 1.3.
    *   **Deliverable:** Python method in `src/dojo/budgeting/services.py`.

*   **Task 2.4: PUT Endpoint for Allocations** - **COMPLETED**
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
*   **Task 3.1: Implement Net Impact Logic for Allocations** - **COMPLETED**
    *   **Description:** Within the `update_allocation` service method, strictly validate the math before committing.
    *   **Logic:**
        1.  Fetch currently active `amount_minor` (Old).
        2.  Calculate `Delta = New_Amount - Old_Amount`.
        3.  Fetch `Ready to Assign` (RTA) and `Category Available`.
        4.  If `Delta > 0` (increasing allocation): Ensure `RTA >= Delta`.
        5.  If `Delta < 0` (decreasing allocation): Ensure `Category Available >= abs(Delta)`. *Correction from plan: effectively "reclaiming" funds.*
    *   **Deliverable:** Validation logic block inside the service method in `src/dojo/budgeting/services.py`.

*   **Task 3.2: Implement Net Impact Logic for Transactions** - **COMPLETED**
    *   **Description:** Validate transaction updates to prevent impossible states (though less critical than allocations, usually specific to account overdrafts if enforced).
    *   **Logic:** Calculate `Delta` and check against account balance (optional depending on business rules) or Category Availability (critical).
    *   **Deliverable:** Validation logic in `src/dojo/budgeting/services.py`.

---

## 5. Phase 4: Frontend (Shared Editable Utility)

### Context:
The codebase uses vanilla JS. We need to refactor the existing specific logic in `transactions/index.js` into a reusable module.

### Tasks
*   **Task 4.1: Extract `hydrateInlineEditRow` to Utility** - **COMPLETED**
    *   **Description:** Move the logic for converting a table row `<tr>` into inputs from `components/transactions/index.js` to a new module `services/ui-ledger.js`.
    *   **Requirements:**
        *   Create `makeRowEditable(trElement, config)`.
        *   `config` should map column indices to input types (`date`, `select`, `money`, `text`).
    *   **Deliverable:** New file `src/dojo/frontend/static/services/ui-ledger.js`.

*   **Task 4.2: Create Reusable Input Renderers** - **COMPLETED**
    *   **Description:** Create helper functions to generate the HTML string for specific inputs.
    *   **Deliverable:**
        *   `renderDateInput(value)`
        *   `renderMoneyInput(minorValue)`
        *   `renderSelect(options, selectedValue)`
    *   **Deliverable:** Functions added to `src/dojo/frontend/static/services/ui-ledger.js`.

## 6. Phase 5: Frontend Integration

### Tasks
*   **Task 5.1: Refactor Transactions Page** - **COMPLETED**
    *   **Description:** Update `components/transactions/index.js` to use the new `makeRowEditable` utility from Task 4.1 instead of its custom implementation.
    *   **Deliverable:** simplified `transactions/index.js`.

*   **Task 5.2: Implement Inline Editing for Allocations** - **COMPLETED**
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

---
Phase 1: Backend Foundation (Database & Schema)

Task 1.1: Migration for Budget Allocations SCD-2

File: src/dojo/sql/migrations/0011_allocation_scd2.sql

We need to evolve the budget_allocations table to support history. Since DuckDB has limited ALTER TABLE support for complex constraints, we will add columns and backfill.
SQL

-- 1. Add SCD-2 columns
ALTER TABLE budget_allocations ADD COLUMN concept_id UUID;
ALTER TABLE budget_allocations ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE budget_allocations ADD COLUMN valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE budget_allocations ADD COLUMN valid_to TIMESTAMP DEFAULT '9999-12-31 00:00:00';
ALTER TABLE budget_allocations ADD COLUMN recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 2. Backfill concept_id
-- For existing rows, the allocation_id serves as the initial concept_id
UPDATE budget_allocations SET concept_id = allocation_id WHERE concept_id IS NULL;

-- 3. Add Index for performance
CREATE INDEX IF NOT EXISTS idx_allocations_concept_active 
ON budget_allocations (concept_id, is_active);

Task 1.2: SQL for Atomic Transaction Updates

File: src/dojo/sql/budgeting/update_transaction_scd2.sql

This script performs the "Soft Retire" and "Insert New" dance.
SQL

-- Param: $concept_id, $new_amount, $new_category, $new_account, $new_memo, $new_date
BEGIN TRANSACTION;

-- 1. Soft Retire the current active version
UPDATE transactions 
SET 
    is_active = FALSE,
    valid_to = CURRENT_TIMESTAMP
WHERE 
    concept_id = $concept_id 
    AND is_active = TRUE;

-- 2. Insert the new version
INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    status,
    recorded_at,
    valid_from,
    valid_to,
    is_active,
    source
)
VALUES (
    uuid(), -- Generate new version ID
    $concept_id,
    $account_id, -- New or existing value
    $category_id, -- New or existing value
    $transaction_date,
    $amount_minor,
    $memo,
    'pending', -- Reset status on edit, or pass $status to keep it
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    '9999-12-31 00:00:00',
    TRUE,
    'user_edit'
);

COMMIT;

Task 1.3: SQL for Atomic Allocation Updates

File: src/dojo/sql/budgeting/update_allocation_scd2.sql

Similar logic for allocations.
SQL

BEGIN TRANSACTION;

UPDATE budget_allocations 
SET is_active = FALSE, valid_to = CURRENT_TIMESTAMP 
WHERE concept_id = $concept_id AND is_active = TRUE;

INSERT INTO budget_allocations (
    allocation_id,
    concept_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo,
    is_active,
    valid_from,
    recorded_at
) VALUES (
    uuid(),
    $concept_id,
    $allocation_date,
    $month_start, -- Usually kept same as original unless date moved months
    $from_category_id,
    $to_category_id,
    $amount_minor,
    $memo,
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

COMMIT;

Phase 2: Backend Logic & API

Task 2.1 & 2.2: Transaction Update Logic

File: src/dojo/budgeting/schemas.py
Python

class TransactionUpdateRequest(BaseModel):
    transaction_date: date
    account_id: str
    category_id: str
    amount_minor: int
    memo: str | None = None

File: src/dojo/budgeting/routers.py
Python

@router.put("/transactions/{concept_id}", response_model=TransactionResponse)
def update_transaction(
    concept_id: UUID,
    payload: TransactionUpdateRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    service: TransactionEntryService = _TRANSACTION_SERVICE_DEP,
):
    return service.update_transaction(conn, concept_id, payload)

Task 2.3 & 2.4: Allocation Update Logic

File: src/dojo/budgeting/schemas.py
Python

class BudgetAllocationUpdateRequest(BaseModel):
    allocation_date: date
    to_category_id: str
    amount_minor: int # The NEW absolute amount
    memo: str | None = None

Phase 3: Validation Logic ("Net Impact")

Task 3.1: Net Impact Implementation

File: src/dojo/budgeting/services.py

This code belongs inside TransactionEntryService.update_allocation.
Python

def update_allocation(self, conn, concept_id: UUID, payload: BudgetAllocationUpdateRequest):
    # 1. Fetch current active state
    # (You will need a simple SELECT query for this)
    current = conn.execute(
        "SELECT amount_minor, month_start, to_category_id FROM budget_allocations WHERE concept_id = ? AND is_active = TRUE", 
        [str(concept_id)]
    ).fetchone()
    
    if not current:
        raise HTTPException(404, "Allocation not found")
        
    old_amount, month_start, category_id = current
    
    # 2. Calculate Delta
    delta = payload.amount_minor - old_amount
    
    # 3. Validation
    if delta > 0:
        # We are increasing the allocation, need to check RTA
        rta = self.ready_to_assign(conn, month_start)
        if rta < delta:
            raise BudgetingError(f"Insufficient funds. Need {delta}, have {rta}")
            
    elif delta < 0:
        # We are decreasing allocation (reclaiming funds). 
        # Check if the category has enough available to give back.
        cat_state = conn.execute(
            "SELECT available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",
            [category_id, month_start]
        ).fetchone()
        
        available = cat_state[0] if cat_state else 0
        reclaim_amount = abs(delta)
        
        if available < reclaim_amount:
            raise BudgetingError(f"Cannot reduce allocation. Category only has {available} available.")

    # 4. If pass, execute SQL from Task 1.3
    # ...

Phase 4: Frontend (Shared Editable Utility)

Task 4.1: ui-ledger.js Utility

File: src/dojo/frontend/static/services/ui-ledger.js

This replaces the hardcoded innerHTML logic in transactions/index.js.
JavaScript

import { formatAmount, minorToDollars } from "./format.js";

export const renderMoneyInput = (valueMinor, name) => {
  const dollars = valueMinor ? minorToDollars(Math.abs(valueMinor)) : "";
  return `<input type="number" step="0.01" name="${name}" value="${dollars}" class="table-input money" />`;
};

export const renderDateInput = (isoDate, name) => {
  return `<input type="date" name="${name}" value="${isoDate}" class="table-input" />`;
};

/**
 * Transforms a static row into an editable row based on config.
 * @param {HTMLElement} row - The TR element
 * @param {Object} data - The raw data object for this row
 * @param {Array} config - Definition of columns
 */
export const makeRowEditable = (row, data, config) => {
  row.classList.add("is-editing");
  
  // Clear current cells and rebuild based on config
  row.innerHTML = "";
  
  config.forEach(col => {
    const td = document.createElement("td");
    
    if (col.type === "money") {
      td.innerHTML = renderMoneyInput(data[col.key], col.name);
    } else if (col.type === "date") {
      td.innerHTML = renderDateInput(data[col.key], col.name);
    } else if (col.type === "select") {
      // Logic to render select and populate options
      td.innerHTML = `<select name="${col.name}"></select>`;
      // You'll need a way to pass options in or load them here
    } else if (col.type === "text") {
      td.innerHTML = `<input type="text" name="${col.name}" value="${data[col.key] || ''}" />`;
    } else if (col.type === "actions") {
       td.innerHTML = `<button data-action="save">Save</button> <button data-action="cancel">Cancel</button>`;
    }
    
    row.appendChild(td);
  });
  
  // Focus first input
  const firstInput = row.querySelector("input, select");
  if(firstInput) firstInput.focus();
};

Phase 5: Frontend Integration

Task 5.2: Allocations Frontend

File: src/dojo/frontend/static/components/allocations/index.js

Update the render loop to attach listeners.
JavaScript

// Inside renderAllocationsPage loop...
row.addEventListener("click", (e) => {
    // Prevent trigger if clicking a button
    if (e.target.tagName === "BUTTON") return;
    
    // Check if already editing any row
    if (store.getState().editingAllocationId) return; 

    startEditingAllocation(row, entry);
});

const startEditingAllocation = (row, entry) => {
    const config = [
        { type: "date", key: "allocation_date", name: "allocation_date" },
        { type: "money", key: "amount_minor", name: "amount_minor" },
        // ... other columns
        { type: "actions" } // Save/Cancel buttons
    ];

    makeRowEditable(row, entry, config);

    // Attach Save Handler
    const saveBtn = row.querySelector('[data-action="save"]');
    saveBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const inputs = row.querySelectorAll("input, select");
        const payload = {};
        inputs.forEach(input => {
             // Logic to convert dollars back to minor units for 'money' types
             // and gather other values
        });
        
        try {
            await api.budgets.updateAllocation(entry.concept_id, payload);
            // On success, reload data
        } catch (err) {
            // Show error toast
        }
    });
};