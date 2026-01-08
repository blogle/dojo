/// <reference types="cypress" />

import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";
import transferPage from "../../support/pages/TransferPage";

const FIXTURE = "tests/fixtures/e2e_investment_transfer_spending.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 12 — Investment Transfers Treated as Spending", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
		cy.intercept("GET", "/api/accounts*").as("fetchAccounts");
		cy.intercept("GET", "/api/net-worth/current").as("fetchNetWorth");
		cy.intercept("POST", "/api/transfers").as("createTransfer");
	});

	it("logs a Down Payment Fund transfer as budget activity without touching net worth", () => {
		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.verifyAvailableAmount("Down Payment Fund", "$400.00");
		budgetPage.verifyActivity("$0.00");

		accountPage.visit();
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		accountPage.verifyAccountBalance("House Checking", "$10,000.00");
		accountPage.verifyAccountBalance("Brokerage", "$2,000.00");
		cy.get("#net-worth")
			.should("contain", "$")
			.invoke("text")
			.as("initialNetWorth");
		cy.get("#ready-to-assign")
			.should("contain", "$")
			.invoke("text")
			.as("initialReadyToAssign");
		cy.get("#assets-total")
			.should("contain", "$")
			.invoke("text")
			.as("initialAssets");
		cy.get("#liabilities-total")
			.should("contain", "$")
			.invoke("text")
			.as("initialLiabilities");

		transferPage.visit();
		transferPage.createTransfer(
			"House Checking",
			"Brokerage",
			"Down Payment Fund",
			"400",
		);
		cy.wait("@createTransfer").its("response.statusCode").should("eq", 201);
		transferPage.verifyError("");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.verifyAvailableAmount("Down Payment Fund", "$0.00");
		budgetPage.verifyActivity("$400.00");
		cy.get("#budgets-ready-value")
			.invoke("text")
			.then((readyAfter) => {
				cy.get("@initialReadyToAssign").then((initialReady) => {
					expect(readyAfter.trim()).to.eq(initialReady.trim());
				});
			});

		accountPage.visit();
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		accountPage.verifyAccountBalance("House Checking", "$9,600.00");
		accountPage.verifyAccountBalance("Brokerage", "$2,400.00");

		cy.get("#net-worth")
			.invoke("text")
			.then((netWorthAfter) => {
				cy.get("@initialNetWorth").then((initialNetWorth) => {
					expect(netWorthAfter.trim()).to.eq(initialNetWorth.trim());
				});
			});

		cy.get("#assets-total")
			.invoke("text")
			.then((assetsAfter) => {
				cy.get("@initialAssets").then((initialAssets) => {
					const initialValue = Number.parseFloat(
						initialAssets.replace(/[^0-9.-]/g, ""),
					);
					const afterValue = Number.parseFloat(
						assetsAfter.replace(/[^0-9.-]/g, ""),
					);
					expect(afterValue).to.eq(initialValue - 400);
				});
			});

		cy.get("#liabilities-total")
			.invoke("text")
			.then((liabilitiesAfter) => {
				cy.get("@initialLiabilities").then((initialLiabilities) => {
					expect(liabilitiesAfter.trim()).to.eq(initialLiabilities.trim());
				});
			});
	});
});
