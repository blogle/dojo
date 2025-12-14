// cypress/support/e2e.js
import "./commands";

before(() => {
	if (!Cypress.env("CYPRESS_COVERAGE")) {
		return;
	}
	return import(
		"../../src/dojo/frontend/vite/node_modules/@bahmutov/cypress-code-coverage/support.js"
	);
});

const DEFAULT_TEST_DATE = "2025-12-15";

// Freeze frontend time and align backend clock via X-Test-Date.
beforeEach(() => {
	if (!Cypress.env("TEST_DATE")) {
		Cypress.env("TEST_DATE", DEFAULT_TEST_DATE);
	}

	cy.intercept("**", (req) => {
		req.headers["x-test-date"] = Cypress.env("TEST_DATE");
	});
});
