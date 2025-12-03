/// <reference types="cypress" />

import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";
import transferPage from "../../support/pages/TransferPage";

const FIXTURE = "tests/fixtures/e2e_categorized_investment_transfer.sql";

describe("User Story 04 — Categorized Investment Transfer", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
	});

	it("moves funds from checking into brokerage while tagging Future Home", () => {
		cy.intercept("POST", "/api/transfers").as("createTransfer");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		budgetPage.verifyAvailableAmount("Future Home", "$1,000.00");

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$50,000.00");
		accountPage.verifyAccountBalance("Brokerage", "$5,000.00");

		transferPage.visit();
		// Transfer page might fetch accounts/categories to populate dropdowns, but likely uses store if recently loaded.
		// We rely on UI assertions in createTransfer to ensure data is present.

		transferPage.createTransfer(
			"House Checking",
			"Brokerage",
			"Future Home",
			"1000",
		);
		cy.wait("@createTransfer").its("response.statusCode").should("eq", 201);
		transferPage.verifyError("");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		budgetPage.verifyAvailableAmount("Future Home", "$0.00");

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$49,000.00");
		accountPage.verifyAccountBalance("Brokerage", "$6,000.00");
	});
});
