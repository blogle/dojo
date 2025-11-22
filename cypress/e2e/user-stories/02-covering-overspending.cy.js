/// <reference types="cypress" />

const FIXTURE = "tests/fixtures/e2e_covering_overspending.sql";

const submitDiningOutOutflow = (amountDollars) => {
  cy.get("[data-transaction-account]").select("House Checking");
  cy.get("[data-transaction-category]").select("Dining Out");
  cy.get("#transaction-form input[name='amount']").clear().type(amountDollars);
  cy.get("[data-transaction-submit]").click();
  cy.get("[data-testid='transaction-error']").should("have.text", "");
};

const coverOverspending = (amountDollars) => {
  cy.get("[data-allocation-from]").select("Groceries");
  cy.get("[data-allocation-to]").select("Dining Out");
  cy.get("[data-testid='allocation-form'] input[name='amount']").clear().type(amountDollars);
  cy.get("[data-allocation-submit]").click();
  cy.get("[data-testid='allocation-error']").should("have.text", "");
};

const expectBudgetRow = (label, value) => {
  cy.contains("#budgets-body tr", label).should("contain", value);
};

const rememberReadyToAssign = () => {
  cy.get("#budgets-ready-value")
    .invoke("text")
    .then((text) => cy.wrap(text.trim()).as("initialReady"));
};

const expectReadyToAssignUnchanged = () => {
  cy.get("@initialReady").then((expected) => {
    cy.get("#budgets-ready-value").should(($value) => {
      expect($value.text().trim()).to.eq(expected);
    });
  });
};

describe("User Story 02 — Rolling with the Punches", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: FIXTURE });
  });

  it("covers Dining Out overspending by reallocating Groceries funds", () => {
    cy.visit("/#/budgets");
    expectBudgetRow("Dining Out", "$100.00");
    expectBudgetRow("Groceries", "$500.00");
    rememberReadyToAssign();

    cy.visit("/#/transactions");
    submitDiningOutOutflow("120");

    cy.get("#transactions-body tr").first().within(() => {
      cy.contains("td", "House Checking").should("exist");
      cy.contains("td", "Dining Out").should("exist");
      cy.contains("td.amount-cell", "$120.00");
    });

    cy.visit("/#/budgets");
    expectBudgetRow("Dining Out", "-$20.00");
    expectBudgetRow("Groceries", "$500.00");
    expectReadyToAssignUnchanged();

    cy.visit("/#/accounts");
    cy.contains(".account-card__name", "House Checking")
      .parents(".account-card")
      .find(".account-card__balance")
      .should("contain", "$880.00");

    cy.visit("/#/allocations");
    coverOverspending("20");

    cy.visit("/#/budgets");
    expectBudgetRow("Dining Out", "$0.00");
    expectBudgetRow("Groceries", "$480.00");
    expectReadyToAssignUnchanged();

    cy.visit("/#/accounts");
    cy.contains(".account-card__name", "House Checking")
      .parents(".account-card")
      .find(".account-card__balance")
      .should("contain", "$880.00");
  });
});
