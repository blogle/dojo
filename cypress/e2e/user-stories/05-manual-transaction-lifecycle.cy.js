/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_manual_transaction_lifecycle.sql";
// Fixed date: Nov 15, 2025
const FIXED_NOW = new Date("2025-11-15T12:00:00Z").getTime();

describe("User Story 05 — Manual Transaction Lifecycle", () => {
	beforeEach(() => {
		const isoDate = new Date(FIXED_NOW).toISOString();
		cy.on("window:before:load", (win) => {
			win.localStorage.setItem("DOJO_TEST_DATE", isoDate);
		});
		cy.clock(FIXED_NOW);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
	});

	it("edits a pending outflow, toggles cleared, and keeps Ready-to-Assign steady", () => {
		cy.intercept("POST", "/api/transactions").as("mutateTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		budgetPage.verifyAvailableAmount("Dining Out", "$200.00");
		budgetPage.rememberReadyToAssign();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$10,000.00");

		transactionPage.visit();
		// Force reload to ensure clean state when switching from LegacyHost (iframe) to Vue Page
		cy.reload();
		cy.wait(1000); // Wait for Vue to hydrate
		cy.wait("@fetchTransactions");

		transactionPage.createOutflowTransaction(
			"House Checking",
			"Dining Out",
			"50",
		);
		cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchTransactions");
		transactionPage.verifyError("");

		transactionPage.elements
			.transactionTableRows()
			.first()
			.within(() => {
				cy.contains("td", "House Checking").should("exist");
				cy.contains("td", "Dining Out").should("exist");
				cy.contains("td.amount-cell", "$50.00");
			});
		transactionPage.verifyTransactionStatus(0, "pending");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		budgetPage.verifyAvailableAmount("Dining Out", "$150.00");
		budgetPage.expectReadyToAssignUnchanged();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$9,950.00");

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		transactionPage.editTransaction(0);
		transactionPage.editOutflowAmount("62");
		transactionPage.toggleTransactionStatus();
		transactionPage.saveInlineEdit();
		cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchTransactions");

		transactionPage.verifyTransactionRowAmount(0, "$62.00");
		transactionPage.verifyTransactionStatus(0, "cleared");

		const monthStart = "2025-11-01";
		cy.request(`/api/budget-categories?month=${monthStart}`).then(
			({ body }) => {
				const dining = body.find(
					(category) => category.category_id === "dining_out",
				);
				expect(dining?.available_minor).to.eq(13800);
			},
		);

		cy.get("[data-route-link='budgets']").click(); // Navigating via UI for budgets page
		cy.wait("@fetchBudgets");
		budgetPage.verifyAvailableAmount("Dining Out", "$138.00");
		budgetPage.expectReadyToAssignUnchanged();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$9,938.00");
	});
});
