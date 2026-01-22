/// <reference types="cypress" />

import accountPage from "../../support/pages/AccountPage";

const INVESTMENT_FIXTURE = "tests/fixtures/e2e_investment_tracking.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 20 — Investment Tracking", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(INVESTMENT_FIXTURE);
	});

	it("navigates from accounts to portfolio and shows NAV + holdings", () => {
		cy.intercept("GET", "/api/accounts*").as("fetchAccounts");
		cy.intercept("GET", "/api/investments/accounts/*").as("fetchPortfolio");
		cy.intercept("GET", "/api/investments/accounts/*/history*").as(
			"fetchHistory",
		);

		accountPage.visit();
		cy.wait("@fetchAccounts");

		cy.contains(".account-card__name", "Brokerage Account")
			.parents(".account-card")
			.click();

		cy.contains("button", "Verify holdings").click();

		cy.location("hash").should(
			"contain",
			"/accounts/brokerage_account/verify-holdings",
		);
		cy.wait("@fetchPortfolio");
		cy.wait("@fetchHistory");

		cy.get(".investments-kv")
			.should("contain", "NAV")
			.and("contain", "$1,100.00");
		cy.get(".investments-header__perf")
			.should("contain", "+$50.00")
			.and("contain", "(+4.76%)");
		cy.get("[data-testid=investment-holdings]").should("contain", "AAPL");
		cy.get("[data-testid=investment-cash-input]").should("exist");
	});
});
