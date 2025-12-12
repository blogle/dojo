// cypress/support/e2e.js
import "@bahmutov/cypress-code-coverage/support";
import "./commands";

// Freeze frontend time and align backend clock via X-Test-Date.
beforeEach(() => {
	const testDate = Cypress.env("TEST_DATE");

	cy.intercept("**", (req) => {
		const headerIsoDate =
			Cypress.env("TEST_DATE") ||
			new Date(Date.now()).toISOString().split("T")[0];
		req.headers["x-test-date"] = headerIsoDate;
	});

	if (testDate) {
		const now = new Date(`${testDate}T00:00:00Z`);
		cy.clock(now.getTime(), ["Date"]);
	}
});
