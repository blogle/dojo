/// <reference types="cypress" />

import allocationPage from "../../support/pages/AllocationPage";

const FIXTURE = "tests/fixtures/e2e_editable_allocation_ledger.sql";

describe("User Story 17 — Editable Allocation Ledger", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
  });

  it("edits an allocation to increase and decrease amount, verifying Ready-to-Assign updates", () => {
    cy.intercept("PUT", "/api/budget/allocations/*").as("updateAllocation");
    cy.intercept("GET", "/api/budget/allocations*").as("fetchAllocations");
    cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchRTA");

    allocationPage.visit();
    cy.wait("@fetchAllocations");
    cy.wait("@fetchRTA");

    // 1. Verify Initial State
    // RTA = 1000 - 500 = 500
    cy.get("#allocations-ready-value").should("contain", "$500.00");
    // Allocation Row
    cy.get("#allocations-body tr").first().as("targetRow");
    cy.get("@targetRow").find("td").eq(3).should("contain", "Groceries"); // To column is index 3
    cy.get("@targetRow").find("td.amount-cell").should("contain", "$500.00");

    // 2. Edit: Increase to $600.00
    // Clicking triggers a re-render, so we must re-query
    cy.get("@targetRow").click();
    
    // Wait for edit mode
    cy.get("#allocations-body tr.is-editing").as("editRow");
    
    // Use selectall to replace content in one go, avoiding potential detachments between clear and type
    cy.get("@editRow")
      .find("input[name='amount_minor']")
      .should("be.enabled")
      .type("{selectall}600{enter}");

    cy.wait("@updateAllocation").its("response.statusCode").should("eq", 200);
    cy.wait("@fetchAllocations");
    cy.wait("@fetchRTA");

    // 3. Verify Impact (Increase)
    // New Allocation: 600. Delta: +100. RTA: 500 - 100 = 400.
    cy.get("#allocations-ready-value").should("contain", "$400.00");
    cy.get("#allocations-body tr").first().as("updatedRow");
    cy.get("@updatedRow").find("td.amount-cell").should("contain", "$600.00");

    // 4. Edit: Decrease to $200.00
    cy.get("@updatedRow").click();
    
    cy.get("#allocations-body tr.is-editing").as("editRow2");

    cy.get("@editRow2")
      .find("input[name='amount_minor']")
      .should("be.enabled")
      .type("{selectall}200{enter}");

    cy.wait("@updateAllocation").its("response.statusCode").should("eq", 200);
    cy.wait("@fetchAllocations");
    cy.wait("@fetchRTA");

    // 5. Verify Impact (Decrease)
    // New Allocation: 200. Previous: 600. Delta: -400. RTA: 400 + 400 = 800.
    cy.get("#allocations-ready-value").should("contain", "$800.00");
    cy.get("#allocations-body tr").first().find("td.amount-cell").should("contain", "$200.00");
  });
});
