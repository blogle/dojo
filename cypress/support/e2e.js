// cypress/support/e2e.js
import "./commands";

// Freeze frontend time and align backend clock via X-Test-Date.
beforeEach(() => {
  const now = new Date(2025, 10, 15);
  const isoDate = now.toISOString().split("T")[0];

  cy.intercept("**", (req) => {
    req.headers["x-test-date"] = isoDate;
  });

  cy.clock(now.getTime(), ["Date"]);
});
