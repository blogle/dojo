# Cypress End-to-End Testing Guidelines

This directory contains the end-to-end (E2E) tests for the Dojo application. These tests simulate real user behavior to validate core budgeting workflows and prevent regressions.

## Core Principles

*   **User-Story Driven**: Each test file (`.cy.js`) corresponds to a canonical user story (e.g., `01-payday-assignment.cy.js`) as defined in `docs/plans/envelope-budget-e2e-mvp.md`.
*   **Strict Atomicity**: Every test (`it` block) must be completely independent. We assume the database is in a pristine state at the start of *every* test.
*   **Critical Paths Only**: Do not test everything. Focus on critical use cases (e.g., money movement, reconciliation) or complex flows with a high risk of breakage.
*   **Abstraction Over Implementation**: Use **Page Objects** or custom commands to interact with the UI. Tests should read like user actions (`budgetPage.assignMoney(...)`), not DOM manipulation.

## Directory Structure

```text
tests/
├─ fixtures/                # SQL or JSON seeds (Parallel to cypress dir)
│   ├── e2e_seed_payday.sql
│   └── e2e_seed_complex_history.sql
cypress/
├── e2e/
│   └── user-stories/        # One file per Story
│       ├── 01-payday-assignment.cy.js
│       └── 02-covering-overspending.cy.js
├── support/
   ├── commands.js          # DB orchestration & lower-level helpers
   └── pages/               # Page Objects (Interaction Abstraction)
       ├── BudgetPage.js
       ├── LedgerPage.js
       └── NetWorthPage.js
```

## Database Orchestration Pattern

We utilize the speed of DuckDB to ensure a completely isolated environment for every test case.

### The `beforeEach` Mandate

We do **not** use `before()` (once per file). We use `beforeEach()` (once per test). This ensures that even if Test A modifies data, Test B starts fresh.

```javascript
describe('User Story 01: Payday Assignment', () => {
        beforeEach(() => {
                // 1. Reset DB to empty state
                cy.resetDatabase(); // Custom command for POST /api/testing/reset_db
                // 2. Seed with specific scenario data from tests/fixtures/
                cy.seedDatabase('e2e_seed_payday.sql'); // Custom command for POST /api/testing/seed_db
                });

        it('should distribute income...', () => { /* ... */ });
});
```
*Note*: The `cy.resetDatabase()` and `cy.seedDatabase()` are custom Cypress commands. They need to be defined in `cypress/support/commands.js`.

## Best Practices

### 1. Interaction Abstraction (Page Objects)

To prevent brittle tests where a single HTML change breaks dozens of suites, we abstract UI interactions into **Page Objects**. Tests should describe *what* the user is doing, not *how* to find the buttons.

**Pattern:**

1.  Create a class in `cypress/support/pages/` (e.g., `LedgerPage.js`).
2.  Define selectors as private constants or getters.
3.  Expose semantic methods for user actions.

**Example `LedgerPage.js`:**

```javascript
class LedgerPage {
    elements = {
        amountInput: () => cy.getBySel('transaction-amount'),
        saveButton: () => cy.getBySel('save-btn'),
        toast: () => cy.getBySel('toast-success')
    };

    createTransaction(amount, category) {
        this.elements.amountInput().type(amount);
        // ... logic for selecting category ...
        this.elements.saveButton().click();
    }

    verifySuccess() {
        this.elements.toast().should('be.visible');
    }
}

export default new LedgerPage();
```

**Usage in Test:**

```javascript
import ledgerPage from '../../support/pages/LedgerPage';

it('should save a transaction', () => {
    // Resilient to HTML changes because logic is centralized in LedgerPage
    ledgerPage.createTransaction('50.00', 'Groceries');
    ledgerPage.verifySuccess();
});
```

### 2. Resilient Selectors (`data-testid`)

Even within Page Objects, avoid targeting brittle CSS classes. Use stable attributes like `data-testid`.

*   **Good:** `cy.get('[data-testid="budget-category-groceries"]')`
*   **Bad:** `cy.get('.table > tr:nth-child(2) > td.amount')`

### 3. Waiting for the Network (The "Anti-Flake" Rule)

The UI is optimistic, but tests must be deterministic. When an action triggers a backend write, you **must** wait for the response before asserting the UI update.

**Pattern:**

1.  **Alias** the route.
2.  **Trigger** the action.
3.  **Wait** for the alias.
4.  **Assert** the outcome.

```javascript
it('should save a transaction', () => {
        cy.intercept('POST', '/api/transactions').as('createTransaction');

        ledgerPage.save(); // Triggers the POST

        // Explicitly wait for backend confirmation
        cy.wait('@createTransaction').its('response.statusCode').should('eq', 201);

        ledgerPage.verifyRowExists();
});
```

### 4. Other Best Practices

#### `describe` and `it` Blocks

Organize your tests logically using `describe` and `it` blocks to improve readability and reporting.

*   `describe`: Use to group related tests, typically for a single user story or a major feature.
*   `it`: Use for individual test cases, describing a specific assertion or interaction.

#### Assertions

Use clear and specific assertions (`.should('contain', 'text')`, `.should('have.value', 'value')`, `.should('eq', 'value')`) to validate the expected outcomes.

#### Navigating the UI

Always navigate through the UI as a user would. Avoid directly manipulating the URL unless it's a specific test case for URL routing.

```javascript
cy.visit('/'); // Visit the base URL
cy.get('[data-testid="nav-link-transactions"]').click(); // Navigate via UI
```

## Contributing New Tests

When adding a new E2E test for a user story:

1.  Create a new file `cypress/e2e/user-stories/XX-your-story-name.cy.js` (replace `XX` with the next sequential number).
2.  Add a `beforeEach` hook to reset the database and seed it with a relevant SQL fixture. The path should be relative to the project root (e.g., `tests/fixtures/e2e_your_story_name.sql`).
3.  Implement the test steps, interactions, and assertions, following the guidelines above.
4.  Ensure the test passes locally before submitting.

### Running Tests

It is recommended to run Cypress tests using either Electron (the default browser for `npx cypress run`) or Chrome.

To run all tests:
```bash
npx cypress run --e2e
```

To run tests in headed mode  with Chrome:
```bash
npx cypress open --e2e --browser chrome --headed
```

---
**Note**: This README is a living document and will be updated as our E2E testing strategy evolves.
