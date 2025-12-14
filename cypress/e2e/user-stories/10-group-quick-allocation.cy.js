/// <reference types="cypress" />

import budgetPage from "../../support/pages/BudgetPage";

const INSUFFICIENT_FIXTURE =
	"tests/fixtures/e2e_group_quick_allocate_insufficient.sql";
const SUFFICIENT_FIXTURE =
	"tests/fixtures/e2e_group_quick_allocate_sufficient.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 10 — Group-Level Quick Allocation", () => {
	context("Insufficient Ready-to-Assign", () => {
		beforeEach(() => {
			Cypress.env("TEST_DATE", TEST_DATE);
			cy.clock(FIXED_NOW, ["Date"]);
			cy.resetDatabase();
			cy.seedDatabase(INSUFFICIENT_FIXTURE);
			cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
			cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
			budgetPage.visit();
			cy.wait("@fetchBudgets");
			cy.wait("@fetchReady");
		});

		it("blocks the Spent Last Month action when funds are insufficient", () => {
			budgetPage.verifyReadyToAssign("$25.00");
			cy.window().then((win) => cy.stub(win, "alert").as("alertStub"));

			budgetPage.openGroupDetailModal("Subscriptions");
			budgetPage.clickGroupQuickActionButton("Spent Last Month: $40.00");

			cy.get("@alertStub").should(
				"have.been.calledWith",
				"Not enough Ready to Assign funds.",
			);
			budgetPage.verifyReadyToAssign("$25.00");
			budgetPage.verifyAvailableAmount("Netflix", "$0.00");
			budgetPage.verifyAvailableAmount("Spotify", "$0.00");
		});
	});

	context("Sufficient Ready-to-Assign", () => {
		beforeEach(() => {
			Cypress.env("TEST_DATE", TEST_DATE);
			cy.clock(FIXED_NOW, ["Date"]);
			cy.resetDatabase();
			cy.seedDatabase(SUFFICIENT_FIXTURE);
			cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
			cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
			cy.intercept("POST", "/api/budget/allocations").as("groupAllocation");
			budgetPage.visit();
			cy.wait("@fetchBudgets");
			cy.wait("@fetchReady");
		});

		it("allocates spent-last-month totals across all group categories", () => {
			budgetPage.verifyReadyToAssign("$100.00");

			budgetPage.openGroupDetailModal("Subscriptions");
			budgetPage.clickGroupQuickActionButton("Spent Last Month: $40.00");

			cy.wait("@groupAllocation");
			cy.wait("@groupAllocation");
			cy.wait("@fetchBudgets");
			cy.wait("@fetchReady");

			budgetPage.verifyReadyToAssign("$60.00");
			budgetPage.verifyAvailableAmount("Netflix", "$15.00");
			budgetPage.verifyAvailableAmount("Spotify", "$25.00");
		});
	});
});
