# Cypress End-to-End Testing Guidelines

This directory contains the end-to-end (E2E) tests for the Dojo application. These tests simulate real user behavior to validate core budgeting workflows and prevent regressions.

## Core Principles

For detailed best practices on writing stable and performant Cypress tests, refer to the [Cypress Best Practices Guide](../../docs/rules/cypress.md).

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

We utilize the speed of DuckDB to ensure a completely isolated environment for every test case. For detailed best practices on database orchestration within Cypress tests, refer to the [Cypress Best Practices Guide](../../docs/rules/cypress.md).

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



## Contributing New Tests

When adding a new E2E test for a user story:

1.  Create a new file `cypress/e2e/user-stories/XX-your-story-name.cy.js` (replace `XX` with the next sequential number).
2.  Add a `beforeEach` hook to reset the database and seed it with a relevant SQL fixture. The path should be relative to the project root (e.g., `tests/fixtures/e2e_your_story_name.sql`).
3.  Implement the test steps, interactions, and assertions, following the guidelines in the [Cypress Best Practices Guide](../../docs/rules/cypress.md).
4.  Ensure the test passes locally before submitting.

### Running Tests

We use the repository's unified test runner `run-tests` (available on PATH), which configures the environment and defaults (Chrome) automatically.

To run all E2E tests:
```bash
run-tests --filter e2e
```

To run a specific user story:
```bash
run-tests --filter e2e:01-payday-assignment
```

For interactive debugging, you can still use the Cypress CLI directly:
```bash
npx cypress open --e2e --browser chrome
```
