/// <reference types="cypress" />

const PAYDAY_FIXTURE = "tests/fixtures/e2e_payday_assignment.sql";
const SYSTEM_CATEGORY_LABELS = [
  "Opening Balance",
  "Balance Adjustment",
  "Account Transfer",
  "Available to Budget",
];

const recordAllocation = (categoryLabel, amountDollars) => {
  cy.get("[data-testid='allocation-form']").within(() => {
    cy.get("[data-allocation-to]").select(categoryLabel);
    cy.get("input[name='amount']").clear().type(amountDollars);
  });
  cy.get("[data-allocation-submit]").click();
  cy.get("[data-testid='allocation-error']").should("have.text", "");
};

describe("User Story 01 — Payday Assignment", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: PAYDAY_FIXTURE });
  });

  it("records a paycheck and assigns it across envelopes", () => {
    cy.visit("/#/transactions");

    cy.get("[data-transaction-account]").should("contain", "House Checking");
    SYSTEM_CATEGORY_LABELS.forEach((label) => {
      cy.get("[data-transaction-category]").contains("option", label).should("exist");
    });

    cy.get("[data-transaction-flow][value='inflow']").check({ force: true });
    cy.get("[data-transaction-account]").select("House Checking");
    cy.get("[data-transaction-category]").select("Available to Budget");
    cy.get("#transaction-form input[name='amount']").clear().type("3000");
    cy.get("[data-transaction-submit]").click();
    cy.get("[data-testid='transaction-error']").should("have.text", "");

    cy.get("#transactions-body tr").should("have.length", 1);
    cy.get("#transactions-body tr").first().within(() => {
      cy.contains("td", "House Checking").should("exist");
      cy.contains("td", "Available to Budget").should("exist");
      cy.contains("td", "$3,000.00").should("exist");
    });

    cy.visit("/#/allocations");
    cy.get("[data-allocation-to]").should("contain", "Rent");
    recordAllocation("Rent", "1500");
    recordAllocation("Groceries", "500");
    recordAllocation("Savings", "1000");

    cy.visit("/#/budgets");
    cy.get("#budgets-ready-value").should("contain", "$0.00");
    cy.get("#budgets-activity-value").should("contain", "$0.00");
    cy.get("#budgets-available-value").should("contain", "$3,000.00");

    [
      { label: "Rent", amount: "$1,500.00" },
      { label: "Groceries", amount: "$500.00" },
      { label: "Savings", amount: "$1,000.00" },
    ].forEach(({ label, amount }) => {
      cy.contains("#budgets-body tr", label).should("contain", amount);
    });

    cy.contains("#budgets-body tr", "Income").should("not.exist");
  });
});
