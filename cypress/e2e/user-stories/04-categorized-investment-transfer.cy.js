/// <reference types="cypress" />

const FIXTURE = "tests/fixtures/e2e_categorized_investment_transfer.sql";

const getAccountBalance = (accountName) =>
  cy
    .contains(".account-card__name", accountName)
    .parents(".account-card")
    .find(".account-card__balance");

const expectFutureHomeRow = (availableValue) => {
  cy.contains("#budgets-body tr", "Future Home").within(() => {
    cy.get("td").last().should("contain", availableValue);
  });
};

describe("User Story 04 — Categorized Investment Transfer", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: FIXTURE });
  });

  it("moves funds from checking into brokerage while tagging Future Home", () => {
    cy.visit("/#/budgets");
    expectFutureHomeRow("$1,000.00");

    cy.visit("/#/accounts");
    getAccountBalance("House Checking").should("contain", "$50,000.00");
    getAccountBalance("Brokerage").should("contain", "$5,000.00");

    cy.visit("/#/transfers");
    cy.get("[data-transfer-source]").select("House Checking");
    cy.get("[data-transfer-destination]").select("Brokerage");
    cy.get("[data-transfer-category]").select("Future Home");
    cy.get("#transfer-form input[name='amount']").clear().type("1000");
    cy.get("[data-transfer-submit]").click();
    cy.get("[data-testid='transfer-error']").should("have.text", "");

    cy.visit("/#/budgets");
    expectFutureHomeRow("$0.00");

    cy.visit("/#/accounts");
    getAccountBalance("House Checking").should("contain", "$49,000.00");
    getAccountBalance("Brokerage").should("contain", "$6,000.00");
  });
});
