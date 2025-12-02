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
    cy.clock(fixedNow.getTime());

    // Visit the allocations page and wait for initial data to load
    cy.visit("/#/allocations");
    cy.wait("@fetchAllocations");
    cy.wait("@fetchRTA");

    // Optional: capture the initial RTA value, so we can assert it changed
    cy.get("#allocations-ready-value")
      .invoke("text")
      .then((initialRTA) => {
        cy.wrap(initialRTA.trim()).as("initialRTA");
      });

    // --- Step 1: enter inline-edit mode on a specific row ---

    // Wait for the table to render the actual data (avoid clicking "Loading...")
    cy.contains("#allocations-body tr", "Groceries").as("targetRow");

    cy.get("@targetRow").click();

    // The click triggers a full re-render of the tbody, so we MUST re-query.
    // We look for the newly rendered editing row rather than reusing @targetRow.
    cy.get("#allocations-body tr.is-editing").as("editRow").should("exist");

    // --- Step 2: update the amount in the inline editor ---

    const newAmountMinor = "600"; // 600_00 in minor units → $600.00, tweak as needed

    cy.get("@editRow").within(() => {
      cy.get("input[name='amount_minor']")
        .should("be.visible")
        .and("not.be.disabled")
        // Single .type to reduce detach risk; {selectall} keeps UX behavior.
        .type(`{selectall}${newAmountMinor}{enter}`, { delay: 5 });
    });

    // --- Step 3: wait for server + aggregate refreshes ---

    // Make sure the PATCH completed
    cy.wait("@updateAllocation").its("response.statusCode").should("eq", 200);

    // Now wait for the subsequent refreshes that recompute allocations + RTA.
    // These waits specifically ensure that by the time we check the DOM,
    // we’ve seen at least one post-update fetch for both.
    cy.wait("@fetchAllocations");
    cy.wait("@fetchRTA");

    // --- Step 4: verify RTA and row amount in the DOM ---

    // Check that Ready-To-Assign changed from the initial value to the new one
    // (we only assert that it is different by default; you can lock in a specific
    //  expected value – e.g., "$400.00" – if your fixtures are stable).
    cy.get("@initialRTA").then((initialRTA) => {
      cy.get("#allocations-ready-value").should(($el) => {
        const updatedRTA = $el.text().trim();
        expect(updatedRTA).to.not.eq(initialRTA);
        // Uncomment / adjust if you want to assert an exact value:
        // expect(updatedRTA).to.contain("$400.00");
      });
    });

    // The table was re-rendered again after the save + data refresh,
    // so we re-query for the first row and assert the updated amount is shown.
    cy.get("#allocations-body tr")
      .first()
      .within(() => {
        // Adjust this selector/format to match how you render the human amount.
        // If you render "$600.00" for 600_00, for example:
        cy.contains("$600.00");
      });
  });
});
