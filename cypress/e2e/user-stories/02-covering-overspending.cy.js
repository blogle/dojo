/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import allocationPage from "../../support/pages/AllocationPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_covering_overspending.sql";

describe("User Story 02 — Rolling with the Punches", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		// Ensure backend is ready before starting the test
		cy.ensureBackendState("/api/budget-categories", (categories) => {
			const dining = categories.find((c) => c.name === "Dining Out");
			return dining && dining.available_minor === 10000;
		});
	});

	it("covers Dining Out overspending by reallocating Groceries funds", () => {
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("POST", "/api/budget/allocations").as("createAllocation");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchRTA");
		cy.intercept("GET", "/api/budget/allocations*").as("fetchAllocations");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchRTA");
		cy.get('[data-testid="budget-col-available"]').each(($el) => {
			cy.log(`Available Amount: ${$el.text()}`);
		});
		budgetPage.verifyAvailableAmount("Dining Out", "$100.00");
		budgetPage.verifyAvailableAmount("Groceries", "$500.00");
        // Ensure RTA is loaded (fixture: $1000 checking - $600 allocated = $400)
        budgetPage.verifyReadyToAssign("$400.00");
		budgetPage.rememberReadyToAssign();

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		transactionPage.createOutflowTransaction(
			"House Checking",
			"Dining Out",
			"120",
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
				cy.contains("td.amount-cell", "$120.00");
			});

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.get('[data-testid="budget-col-available"]').each(($el) => {
			cy.log(`Available Amount After Transaction: ${$el.text()}`);
		});
		budgetPage.verifyAvailableAmount("Dining Out", "-$20.00");
		budgetPage.verifyAvailableAmount("Groceries", "$500.00");
		budgetPage.expectReadyToAssignUnchanged();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$880.00");

		allocationPage.visit();
		cy.wait("@fetchAllocations");
		allocationPage.categoryTransfer("Groceries", "Dining Out", "20");
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchAllocations");
		allocationPage.verifyError("");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.get('[data-testid="budget-col-available"]').each(($el) => {
			cy.log(`Available Amount After Allocation: ${$el.text()}`);
		});
		budgetPage.verifyAvailableAmount("Dining Out", "$0.00");
		budgetPage.verifyAvailableAmount("Groceries", "$480.00");
		budgetPage.expectReadyToAssignUnchanged();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$880.00");
	});
});
