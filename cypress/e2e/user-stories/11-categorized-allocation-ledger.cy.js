/// <reference types="cypress" />

import allocationPage from "../../support/pages/AllocationPage";
import budgetPage from "../../support/pages/BudgetPage";

const FIXTURE = "tests/fixtures/e2e_categorized_allocation_ledger.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 11 — Categorized Allocation Ledger Functionality", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
		cy.intercept("GET", "/api/budget/allocations*").as("fetchAllocations");
		cy.intercept("POST", "/api/budget/allocations").as("createAllocation");
	});

	it("keeps Ready-to-Assign steady while both summary cards and the ledger update", () => {
		const today = Cypress.env("TEST_DATE");

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		cy.wait("@fetchAllocations");

		budgetPage.verifyAvailableAmount("Groceries", "$150.00");
		budgetPage.verifyAvailableAmount("Rent", "$50.00");
		budgetPage.verifyReadyToAssign("$900.00");
		budgetPage.rememberReadyToAssign();

		cy.get("#allocations-inflow-value").should("contain", "$500.00");
		cy.get("#allocations-ready-value").should("contain", "$900.00");

		allocationPage.categoryTransfer(
			"Groceries",
			"Rent",
			"50",
			"Initial allocation",
		);
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);

		cy.get("#allocations-body tr")
			.first()
			.within(() => {
				cy.contains("td", today).should("exist");
				cy.get("td.amount-cell").should("contain", "$50.00");
				cy.contains("td", "Groceries").should("exist");
				cy.contains("td", "Rent").should("exist");
				cy.contains("td", "Initial allocation").should("exist");
			});

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.expectReadyToAssignUnchanged();
		budgetPage.verifyAvailableAmount("Groceries", "$100.00");
		budgetPage.verifyAvailableAmount("Rent", "$100.00");

		allocationPage.categoryTransfer(
			"Groceries",
			"Rent",
			"25",
			"Increase to 75",
		);
		cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);

		cy.get("#allocations-body tr")
			.first()
			.within(() => {
				cy.contains("td", today).should("exist");
				cy.get("td.amount-cell").should("contain", "$25.00");
				cy.contains("td", "Groceries").should("exist");
				cy.contains("td", "Rent").should("exist");
				cy.contains("td", "Increase to 75").should("exist");
			});

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		budgetPage.expectReadyToAssignUnchanged();
		budgetPage.verifyAvailableAmount("Groceries", "$75.00");
		budgetPage.verifyAvailableAmount("Rent", "$125.00");
	});
});
