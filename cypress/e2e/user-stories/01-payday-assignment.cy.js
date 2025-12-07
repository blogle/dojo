/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import allocationPage from "../../support/pages/AllocationPage";
import budgetPage from "../../support/pages/BudgetPage";

const PAYDAY_FIXTURE = "tests/fixtures/e2e_payday_assignment.sql";
const SYSTEM_CATEGORY_LABELS = [
	"Opening Balance",
	"Balance Adjustment",
	"Account Transfer",
	"Available to Budget",
];

describe("User Story 01 — Payday Assignment", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(PAYDAY_FIXTURE);
	});

	it("records a paycheck and assigns it across envelopes", () => {
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("POST", "/api/budget/allocations").as("createAllocation");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/allocations*").as("fetchAllocations");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");

		transactionPage.visit();
		cy.wait("@fetchTransactions");

		transactionPage.elements
			.accountSelect()
			.should("contain", "House Checking");
		SYSTEM_CATEGORY_LABELS.forEach((label) => {
			transactionPage.elements
				.categorySelect()
				.contains("option", label)
				.should("exist");
		});

		transactionPage.createTransaction(
			"inflow",
			"House Checking",
			"Available to Budget",
			"3000",
		);
		cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchTransactions");
		transactionPage.verifyError("");

		transactionPage.verifyTransactionCount(1);
		transactionPage.verifyTransactionRow(
			0,
			"House Checking",
			"Available to Budget",
			"$3,000.00",
		);

		allocationPage.visit();
		cy.wait("@fetchAllocations");

		allocationPage.elements.categorySelect().should("contain", "Rent");

		allocationPage.recordAllocation("Rent", "1500");
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchAllocations");
		allocationPage.verifyError("");

		allocationPage.recordAllocation("Groceries", "500");
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchAllocations");
		allocationPage.verifyError("");

		allocationPage.recordAllocation("Savings", "1000");
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchAllocations");
		allocationPage.verifyError("");

		budgetPage.visit();
		cy.wait("@fetchBudgets");

		budgetPage.verifyReadyToAssign("$0.00");
		budgetPage.verifyActivity("$0.00");
		budgetPage.verifyAvailable("$3,000.00");

		[
			{ label: "Rent", amount: "$1,500.00" },
			{ label: "Groceries", amount: "$500.00" },
			{ label: "Savings", amount: "$1,000.00" },
		].forEach(({ label, amount }) => {
			budgetPage.verifyCategoryAmount(label, amount);
		});

		budgetPage.verifyCategoryDoesNotExist("Income");
	});
});
