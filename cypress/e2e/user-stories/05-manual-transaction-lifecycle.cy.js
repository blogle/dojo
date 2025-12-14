/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_manual_transaction_lifecycle.sql";
// Fixed date: Nov 15, 2025
const TEST_DATE = "2025-11-15";
const FIXED_NOW = new Date("2025-11-15T12:00:00Z").getTime();

describe("User Story 05 — Manual Transaction Lifecycle", () => {
	beforeEach(() => {
		const isoDate = new Date(FIXED_NOW).toISOString();
		cy.on("window:before:load", (win) => {
			win.localStorage.setItem("DOJO_TEST_DATE", isoDate);
		});
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		// Ensure backend is ready (checking Nov 2025 state)
		cy.ensureBackendState(
			"/api/budget-categories?month=2025-11-01",
			(categories) => {
				const dining = categories.find((c) => c.name === "Dining Out");
				return dining && dining.available_minor === 20000;
			},
		);
	});

	it("edits a pending outflow, toggles cleared, and keeps Ready-to-Assign steady", () => {
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		cy.intercept("PUT", "/api/transactions/*").as("updateTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchRTA");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchRTA");
		budgetPage.verifyAvailableAmount("Dining Out", "$200.00");
		// Ensure RTA is loaded (fixture: $10,000 checking - $200 allocated = $9,800)
		budgetPage.verifyReadyToAssign("$9,800.00");
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
		cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
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
		// Clean up legacy artifacts (if any) when returning from legacy routes
		cy.reload();
		cy.wait("@fetchTransactions");
		transactionPage.editTransaction(0);
		transactionPage.editOutflowAmount("62");
		transactionPage.toggleTransactionStatus();

		// Verify UI updated before saving
		cy.get("[data-inline-status-toggle]").should(
			"have.attr",
			"data-state",
			"cleared",
		);

		transactionPage.saveInlineEdit();
		cy.wait("@updateTransaction").then((interception) => {
			// Verify payload
			expect(interception.request.body.status).to.eq("cleared");
			expect(interception.response.statusCode).to.eq(200);
		});
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
