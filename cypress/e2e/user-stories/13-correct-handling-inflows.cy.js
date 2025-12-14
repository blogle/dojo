/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_correct_handling_inflows.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 13 — Correct Handling of Inflows in Ledger", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
		cy.intercept("GET", "/api/accounts*").as("fetchAccounts");
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		// Ensure backend is ready (Checking Account should have $1,000.00)
		cy.ensureBackendState("/api/accounts", (accounts) => {
			const checking = accounts.find((a) => a.name === "House Checking");
			return checking && checking.current_balance_minor === 100000;
		});
	});

	it("renders a refund as a positive inflow and keeps summaries in sync", () => {
		const today = Cypress.env("TEST_DATE");

		transactionPage.visit();
		cy.wait("@fetchTransactions");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.verifyActivity("$0.00");
		// Ensure RTA is loaded (fixture: $1,000 checking - 0 allocated = $1,000)
		budgetPage.verifyReadyToAssign("$1,000.00");
		budgetPage.rememberReadyToAssign();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$1,000.00");

		transactionPage.visit();
		transactionPage.createTransaction(
			"inflow",
			"House Checking",
			"Refunds",
			"200",
		);
		cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.expectReadyToAssignUnchanged();
		budgetPage.verifyActivity("$200.00");

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$1,200.00");

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		cy.contains("#transactions-body tr", "Refunds").within(() => {
			cy.contains("td", today).should("exist");
			cy.get("td.amount-cell").eq(0).should("contain", "—");
			cy.get("td.amount-cell").eq(1).should("contain", "$200.00");
		});
	});
});
