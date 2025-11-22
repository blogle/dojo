/// <reference types="cypress" />

const FIXTURE = "tests/fixtures/e2e_funded_credit_card_spending.sql";

const submitCreditPurchase = (amountDollars) => {
  cy.get("[data-transaction-account]").select("Visa Signature");
  cy.get("[data-transaction-category]").select("Gas");
  cy.get("#transaction-form input[name='amount']").clear().type(amountDollars);
  cy.get("[data-transaction-submit]").click();
  cy.get("[data-testid='transaction-error']").should("have.text", "");
};

describe("User Story 03 — Funded Credit Card Spending", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: FIXTURE });
  });

  it("tracks category balances and credit liabilities when spending on card", () => {
    cy.visit("/#/transactions");

    submitCreditPurchase("60");

    cy.get("#transactions-body tr").first().within(() => {
      cy.contains("td", "Visa Signature").should("exist");
      cy.contains("td", "Gas").should("exist");
      cy.contains("td.amount-cell", "$60.00");
    });

    cy.visit("/#/budgets");
    cy.contains("#budgets-body tr", "Gas").should("contain", "$40.00");
    cy.contains("#budgets-body tr", "Visa Signature Payment").should("contain", "$60.00");

    cy.visit("/#/accounts");
    cy.get("#accounts-page").should("have.class", "active");
    cy.get(".account-card__name", { timeout: 10000 }).should("have.length.greaterThan", 0);
    cy.contains(".account-card__name", "Visa Signature")
      .parents(".account-card")
      .find(".account-card__balance")
      .should("contain", "-$60.00");
    cy.contains(".account-card__name", "House Checking")
      .parents(".account-card")
      .find(".account-card__balance")
      .should("contain", "$5,000.00");
  });
});
