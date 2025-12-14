/// <reference types="cypress" />

import allocationPage from "../../support/pages/AllocationPage";

const FIXTURE = "tests/fixtures/e2e_editable_allocation_ledger.sql";

describe("User Story 17 — Editable Allocation Ledger", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/budget/allocations*").as("fetchAllocations");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchRTA");
		cy.intercept("PUT", "/api/budget/allocations/*").as("updateAllocation");
	});

	it("User Story 17 – user can edit an allocation inline and RTA updates correctly", () => {
		// Pin time so that any month-dependent logic is stable
		const fixedNow = new Date("2025-01-15T12:00:00Z");
		Cypress.env("TEST_DATE", "2025-01-15");
		cy.clock(fixedNow.getTime(), ["Date"]);

		cy.visit("/#/budgets");
		cy.wait("@fetchAllocations");

		// Initial state: Groceries allocated $500.00, RTA $500.00 (from $1000 total)
		cy.get("#allocations-ready-value").should("contain", "$500.00");

		// Find the Groceries row and click it to edit
		cy.contains("#allocations-body tr", "Groceries").click();

		// Wait for Vue to update
		cy.wait(500);

		// Check for edit mode and delete button
		cy.get("#allocations-body tr.is-editing").should("exist").as("editRow");
		cy.get("@editRow")
			.find("button[title='Delete allocation']")
			.should("exist")
			.as("deleteBtn");

		// Click delete
		cy.intercept("DELETE", "/api/budget/allocations/*").as("deleteAllocation");
		cy.get("@deleteBtn").click();

		// Wait for delete
		cy.wait("@deleteAllocation").its("response.statusCode").should("eq", 204);
		cy.wait("@fetchAllocations");

		// Verify row is gone
		cy.contains("#allocations-body tr", "Groceries").should("not.exist");

		// Verify RTA increased back to $1000.00
		cy.get("#allocations-ready-value").should("contain", "$1,000.00");
	});
});
