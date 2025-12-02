# Cypress Best Practices

This document defines the best practices for writing Cypress End-to-End (E2E) tests within the Dojo application. Follow these rules to keep tests **deterministic**, **performant**, and **stable**, especially in the presence of destructive re-renders and network-driven UI updates.

---

## Core Principles

- **User-Story Driven**
  Each test file (`.cy.js`) corresponds to a canonical user story, validating core budgeting workflows end-to-end.

- **Strict Atomicity**
  Every test (`it` block) must be completely independent. We assume the database is in a pristine state at the start of *every* test.

- **Critical Paths Only**
  Focus on critical flows (e.g., money movement, reconciliation, allocation, error handling) and high-risk interactions. Do **not** try to test every possible UI permutation in Cypress.

- **Abstraction Over Implementation**
  Interact with the UI via **Page Objects** or custom commands. Tests should read like user actions (`budgetPage.assignMoney(...)`), not raw DOM manipulation.

- **Network- and State-Aware**
  When an action changes server state, always wait for the **write** (POST/PATCH/DELETE) and any **subsequent read** (GET) that actually updates the UI before asserting.

- **Render-Aware**
  Our frontend often uses **destructive renders** (e.g., `innerHTML = ""` + rebuild). Cypress tests must assume that rows and cells are frequently destroyed and recreated, and should **re-query** the DOM after such actions.

---

## Database Orchestration Pattern

We use DuckDB and testing endpoints to guarantee an isolated environment for every test case.

### The `beforeEach` Mandate

We do **not** use `before()` (once per file). We use `beforeEach()` (once per test). This guarantees test independence and prevents hidden coupling through shared DB state.

    describe('User Story 01: Payday Assignment', () => {
      beforeEach(() => {
        // 1. Reset DB to empty state
        cy.resetDatabase(); // Custom command for POST /api/testing/reset_db

        // 2. Seed with specific scenario data from tests/fixtures/
        cy.seedDatabase('e2e_seed_payday.sql'); // Custom command for POST /api/testing/seed_db
      });

      it('should distribute income into envelopes', () => {
        // ...
      });
    });

`cy.resetDatabase()` and `cy.seedDatabase()` are custom Cypress commands, typically defined in `cypress/support/commands.js`.

---

## 1. Interaction Abstraction (Page Objects)

To prevent one HTML change from breaking dozens of tests, we centralize selectors and flows into **Page Objects**.

### Pattern

1. Create a class in `cypress/support/pages/` (e.g., `LedgerPage.js`).
2. Define selectors via getters or an `elements` field.
3. Expose semantic methods for user actions and assertions.

    // cypress/support/pages/LedgerPage.js
    class LedgerPage {
      elements = {
        amountInput: () => cy.getBySel('transaction-amount'),
        saveButton: () => cy.getBySel('transaction-save'),
        toast: () => cy.getBySel('toast-success'),
      };

      createTransaction({ amount, category }) {
        this.elements.amountInput().type(amount);
        // ... category selection ...
        this.elements.saveButton().click();
      }

      verifySuccessToast() {
        this.elements.toast().should('be.visible');
      }
    }

    export default new LedgerPage();

Usage in tests:

    import ledgerPage from '../../support/pages/LedgerPage';

    it('should save a transaction', () => {
      ledgerPage.createTransaction({ amount: '50.00', category: 'Groceries' });
      ledgerPage.verifySuccessToast();
    });

All DOM details (selectors, structure) live in one place: the page object.

---

## 2. Resilient Selectors (`data-testid`)

Even within Page Objects, avoid brittle CSS or deep `nth-child` chains. We standardize on **`data-testid`** for stability.

- Good:
  `cy.get('[data-testid="budget-category-groceries"]')`
- Bad:
  `cy.get('.table > tr:nth-child(2) > td.amount')`
- Avoid:
  Text-based selectors when a `data-testid` is available (`cy.contains(...)`) because copy tweaks will break tests.

### 2.1 Column-Level Test IDs for Tables

For tables (budget, transactions, allocations), each column should expose **semantic** `data-testid` attributes at the cell level. Examples:

    <!-- Budget table row -->
    <td data-testid="budget-col-name">Groceries</td>
    <td data-testid="budget-col-budgeted" class="amount-cell">$300.00</td>
    <td data-testid="budget-col-activity" class="amount-cell">-$50.00</td>
    <td data-testid="budget-col-available" class="amount-cell">$250.00</td>

    <!-- Transaction ledger row -->
    <td data-testid="transaction-col-date">2025-11-15</td>
    <td data-testid="transaction-col-payee">Trader Joe's</td>
    <td data-testid="transaction-col-category">Groceries</td>
    <td data-testid="transaction-col-account">Checking</td>
    <td data-testid="transaction-col-amount" class="amount-cell">-$50.00</td>
    <td data-testid="transaction-col-status">Cleared</td>

Cypress helpers:

    verifyAvailableAmount(categoryName, amount) {
      this.categoryRow(categoryName)
        .find('[data-testid="budget-col-available"]')
        .should('contain', amount);
    }

    verifyTransactionAmount(rowIndex, amount) {
      cy.getBySel('transactions-body')
        .find('tr')
        .eq(rowIndex)
        .find('[data-testid="transaction-col-amount"]')
        .should('contain', amount);
    }

This removes reliance on `.eq(n)` or `nth-child` and makes tests tolerant of column additions/reordering.

---

## 3. Network-Driven Assertions & Destructive Re-Renders

Most Dojo flows follow this pattern:

1. User action triggers a **write** (e.g., `POST /api/transactions`).
2. The frontend then triggers one or more **reads** (`GET /api/transactions`, `GET /api/budget-categories`) to refresh the UI.
3. The UI may re-render entire tables (e.g., `tbody.innerHTML = ""` + rebuild).

### 3.1 The “Anti-Flake” Network Rule

When an action changes data on the server and the UI depends on that data:

1. Alias the **write** (POST/PATCH/DELETE).
2. Alias the **read(s)** that refresh the UI.
3. Trigger the action through the UI.
4. Wait for the **write** to succeed.
5. Wait for the **read** to complete.
6. Assert on the DOM via fresh queries.

Example:

    it('should save a transaction and update the ledger', () => {
      cy.intercept('POST', '/api/transactions*').as('createTransaction');
      cy.intercept('GET', '/api/transactions*').as('fetchTransactions');

      ledgerPage.createTransaction({ amount: '300.00', category: 'Rent' });

      cy.wait('@createTransaction')
        .its('response.statusCode')
        .should('eq', 201);

      cy.wait('@fetchTransactions');

      // Re-query the refreshed DOM
      ledgerPage.verifyTransactionAmount(0, '$300.00');
    });

Key point:

> Waiting only on the POST but asserting on UI that’s driven by the GET is a common flake source. Always wait on **both**.

### 3.2 Destructive Renders & Detached DOM Elements

Our components often do:

    const renderTransactions = (bodyEl, transactions) => {
      bodyEl.innerHTML = ''; // destroys all child nodes
      // ... rebuild rows ...
    };

If a test grabs a row before this and then reuses it after:

    cy.get('#transactions-body tr').first().as('row');
    ledgerPage.saveInlineEdit(); // triggers POST + GET + re-render

    cy.get('@row')
      .find('[data-testid="transaction-col-amount"]')
      .should('contain', '$200.00'); // ❌ element is detached

…it will intermittently fail with “element has detached from the DOM”.

Rule:

> Do **not** reuse aliases for nodes that may be destroyed by a re-render. Always **re-query** the DOM after any action that triggers a save/refresh.

Correct pattern:

    ledgerPage.saveInlineEdit(); // triggers backend save + re-render

    cy.wait('@mutateTransaction');
    cy.wait('@fetchTransactions');

    cy.getBySel('transactions-body')
      .find('tr')
      .first()
      .find('[data-testid="transaction-col-amount"]')
      .should('contain', '$200.00');

Safe aliasing:

- OK to alias **static containers** (e.g., `#transactions-body`, modal root).
- Avoid aliasing **rows/cells** across actions that trigger a re-render.

---

## 4. Avoiding Arbitrary Time-Based Waits

### 4.1 No `cy.wait(ms)` for Correctness

- `cy.wait(500)` (or any arbitrary duration) should **never** be used to assert correctness.
- Time-based waits should be a last resort for external, non-deterministic dependencies.
- Prefer:
  - Network waits (`cy.wait('@alias')`), and/or
  - Element-based waits (`cy.get(...).should('be.visible')`, `.should('have.length', n)`).

### 4.2 Testing “Non-Events” (Things That Must Not Happen)

Avoid patterns like:

    let allocationCalled = false;
    cy.intercept('POST', '/api/allocate*', () => {
      allocationCalled = true;
    });

    clickAllocate();
    cy.wait(500);
    expect(allocationCalled).to.be.false; // ❌ racey

In slow environments, the request can fire after 500ms, leading to false negatives.

Preferred pattern: rely on **spies/stubs** and **UI state**.

Example: validating that allocation does **not** happen because of insufficient funds:

    cy.window().then((win) => {
      cy.stub(win, 'alert').as('alertStub');
    });

    cy.intercept('POST', '/api/allocate*').as('allocate');

    openQuickAllocateModal();
    clickConfirm();

    cy.get('@alertStub')
      .should('have.been.calledWith', 'Not enough Ready to Assign funds.');

    // Assert that the allocate endpoint was never called
    cy.get('@allocate').should('not.exist');

Or with a spy on an in-app function (if exposed):

    cy.spy(api, 'allocateBudget').as('allocateBudget');
    // ...
    clickConfirm();
    cy.get('@allocateBudget').should('not.have.been.called');

Rule:

> When asserting that something does **not** happen, rely on spies/stubs and UI state, not arbitrary sleeps.

---

## 5. Date & Time Control (`cy.clock`, `cy.tick`)

Any test that branches on “today”, “current month”, or relative time must use `cy.clock` to avoid calendar-dependent behavior.

### Pattern

    beforeEach(() => {
      // Freeze time at a stable reference date
      const now = new Date(2025, 10, 15).getTime(); // November 15, 2025
      cy.clock(now);

      cy.resetDatabase();
      cy.seedDatabase('e2e_seed_transactions_base.sql');
    });

This ensures:

- Monthly logic (e.g., “if today is after the 1st…”) is deterministic.
- Bugs don’t only appear (or disappear) on certain calendar days.

If the UI relies on timers (debounce, animations), pair `cy.clock` with `cy.tick(ms)` to control them explicitly.

---

## 6. Visibility and Interactivity Checks

Before interacting with elements, ensure they are **visible** and **interactive**, especially when they appear after async actions.

Examples:

    cy.getBySel('transaction-amount')
      .should('be.visible')
      .and('not.be.disabled')
      .type('100.00');

    cy.getBySel('transaction-save')
      .should('be.visible')
      .and('not.be.disabled')
      .click();

This makes the tests’ expectations explicit and improves debugging when elements are hidden or disabled.

---

## 7. Intercepts: Specificity and Multiple Calls

### 7.1 Specific Aliases and Scoping

Generic intercepts like:

    cy.intercept('GET', '/api/budget-categories*').as('fetchBudgets');

can match:

- Initial page load
- Post-save refresh
- Other incidental refreshes

`cy.wait('@fetchBudgets')` will consume the **first** matched request at that time, which might not be the one triggered by the action under test.

Better pattern: define intercepts close to the action and give them descriptive names.

    // Before performing the inline edit
    cy.intercept('GET', '/api/budget-categories*').as('refetchAfterInlineEdit');

    budgetPage.editCategoryAmount('Groceries', '$300.00');
    budgetPage.saveInlineEdit();

    cy.wait('@refetchAfterInlineEdit');

If you expect multiple calls and need to assert on the count:

    let callCount = 0;

    cy.intercept('GET', '/api/budget-categories*', (req) => {
      callCount += 1;
    }).as('fetchBudgets');

    budgetPage.saveInlineEdit();

    cy.wait('@fetchBudgets').then(() => {
      expect(callCount).to.eq(2); // example
    });

---

## 8. Navigating the UI as a User

Navigate through the app as a user would, via the UI, not by direct URL manipulation, except when testing routing/deep-links explicitly.

    cy.visit('/'); // base URL
    cy.getBySel('nav-link-transactions').click();
    cy.getBySel('transactions-body').should('be.visible');

This ensures navigation flows and layout changes remain covered by tests.

---

## 9. Organizing `describe` and `it` Blocks

- Use `describe` to group related tests, typically one per **user story** or major feature area.
- Use `it` for specific scenarios/outcomes within that story.

Examples:

    describe('User Story 06: Editable Ledger Rows', () => {
      it('allows updating a transaction amount', () => {
        // ...
      });

      it('blocks edits that violate budget constraints', () => {
        // ...
      });
    });

Names should clearly state the behavior being validated, not implementation details.

---

## 10. Common Flakiness Patterns and How We Fix Them

When addressing flakiness, check for:

- **Missing waits on GET after POST**
  - Fix: Always wait for the **refresh GET** that updates the UI, not just the mutation.

- **Reusing DOM aliases across destructive re-renders**
  - Fix: Re-query rows/cells after actions that trigger saves or refreshes.

- **Arbitrary `cy.wait(ms)` used for correctness**
  - Fix: Replace with network waits (`cy.wait('@alias')`), element existence/visibility checks, or spies/stubs.

- **Brittle selectors (`nth-child`, `.eq(n)` on `td.amount-cell`)**
  - Fix: Move to `data-testid` patterns, especially column-level IDs for tables.

- **Calendar-dependent logic**
  - Fix: Use `cy.clock` to pin tests to a stable date/time.

- **Overly generic intercepts**
  - Fix: Scope intercepts closer to the action, use specific alias names, and consider call counts where relevant.

By consistently applying these patterns, we get a test suite that is:

- Resilient to UI refactors,
- Honest about server and network timing,
- Robust against destructive re-renders,
- And deterministic across days and environments.

