/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import allocationPage from "../../support/pages/AllocationPage";

const FIXTURE = "tests/fixtures/e2e_monthly_summary_cards.sql";
// Fixed date: Jan 15, 2024
const TEST_DATE = "2024-01-15";
const FIXED_NOW = new Date("2024-01-15T12:00:00Z").getTime();

const formatBudgetMonthLabel = () => {
	const today = new Date(FIXED_NOW);
	const monthStart = new Date(today.getFullYear(), today.getMonth());
	return monthStart.toLocaleDateString(undefined, {
		year: "numeric",
		month: "long",
	});
};

describe("User Story 14 — Display of Monthly Summary Cards Across Pages", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
		cy.intercept("GET", "/api/budget/allocations*").as("fetchAllocations");
		cy.intercept("POST", "/api/transactions").as("persistTransaction");
		cy.intercept("PUT", "/api/transactions/*").as("updateTransaction");
		cy.intercept("POST", "/api/budget/allocations").as("createAllocation");
	});

	it("keeps the summary chips accurate while editing ledger rows and allocation entries", () => {
		transactionPage.visit();
		cy.wait("@fetchTransactions");
		cy.get("#month-spend").should("contain", "$150.00");
		cy.get("#month-budgeted").should("contain", "$450.00");
		// Re-query row to avoid staleness if re-renders happen
		cy.contains("#transactions-body tr", "Groceries run").should("exist");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		cy.get("#budgets-ready-value")
			.should("not.contain", "—")
			.invoke("text")
			.as("initialReady");
		budgetPage.verifyActivity("$150.00");
		budgetPage.verifyAvailable("$500.00");
		cy.get("#budgets-month-label")
			.invoke("text")
			.then((label) => {
				expect(label.trim()).to.eq(formatBudgetMonthLabel());
			});

		transactionPage.visit();
		cy.wait("@fetchTransactions"); // Ensure table is loaded before clicking
		cy.get("#month-spend").should("contain", "$150.00"); // Wait for JS render to complete
		cy.contains("#transactions-body tr", "Groceries run").click();
		transactionPage.setInlineOutflow("200");
		cy.get("[data-inline-outflow]").should("have.value", "200");
		transactionPage.saveInlineEdit();
		cy.wait("@updateTransaction").its("response.statusCode").should("eq", 200);
		cy.wait("@fetchTransactions");

		cy.get("#transactions-body tr").should("have.length", 2); // Ensure no duplicate created
		// Wait for the table to update first to ensure the fetch is processed
		transactionPage.verifyTransactionRowByMemo("Groceries run", {
			amount: "$200.00",
		});

		cy.get("#month-spend").should("contain", "$200.00");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.verifyActivity("$200.00");

		allocationPage.visit();
		cy.wait("@fetchAllocations");
		allocationPage.categoryTransfer(
			"Available to Budget",
			"Rent",
			"100",
			"Monthly shift",
		);
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);
		// Note: allocationPage might trigger refetches, but we navigate away immediately

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		cy.get("@initialReady").then((initialReady) => {
			cy.get("#budgets-ready-value")
				.should("not.contain", "—")
				.invoke("text")
				.should((currentReady) => {
					expect(currentReady).not.to.eq(initialReady);
				});
		});

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		cy.get("#month-budgeted").should("contain", "$550.00");
		cy.get("#month-spend").should("contain", "$200.00");
	});
});
