// cypress/support/commands.js

Cypress.Commands.add("resetDatabase", () => {
	cy.request("POST", "/api/testing/reset_db");
});

Cypress.Commands.add("seedDatabase", (fixturePath) => {
	cy.request("POST", "/api/testing/seed_db", { fixture: fixturePath });
});

// Helper to ensure backend data is ready before UI interaction
// Retry fetching the URL until the predicate returns true
Cypress.Commands.add("ensureBackendState", (url, predicate, options = {}) => {
    const { timeout = 10000, interval = 500 } = options;
    const startTime = Date.now();

    const check = () => {
        cy.request({ url, failOnStatusCode: false }).then((res) => {
            if (Date.now() - startTime > timeout) {
                throw new Error(`ensureBackendState timed out for ${url}`);
            }
            if (res.status === 200 && predicate(res.body)) {
                return; // Success
            } else {
                cy.wait(interval);
                check();
            }
        });
    };
    check();
});

// Custom command for selecting elements by data-testid
Cypress.Commands.add("getBySel", (selector, ...args) => {
	return cy.get(`[data-testid=${selector}]`, ...args);
});