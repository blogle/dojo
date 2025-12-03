// cypress/support/commands.js

Cypress.Commands.add("resetDatabase", () => {
	cy.request("POST", "/api/testing/reset_db");
});

Cypress.Commands.add("seedDatabase", (fixturePath) => {
	cy.request("POST", "/api/testing/seed_db", { fixture: fixturePath });
});

// Custom command for selecting elements by data-testid
Cypress.Commands.add("getBySel", (selector, ...args) => {
	return cy.get(`[data-testid=${selector}]`, ...args);
});
