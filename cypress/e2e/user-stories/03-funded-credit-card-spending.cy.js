/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_funded_credit_card_spending.sql";

describe("User Story 03 — Funded Credit Card Spending", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: FIXTURE });
  });

  it("tracks category balances and credit liabilities when spending on card", () => {
    transactionPage.visit();

    transactionPage.createOutflowTransaction("Visa Signature", "Gas", "60");
    transactionPage.verifyError("");

    transactionPage.elements.transactionTableRows().first().within(() => {
      cy.contains("td", "Visa Signature").should("exist");
      cy.contains("td", "Gas").should("exist");
      cy.contains("td.amount-cell", "$60.00");
    });

    budgetPage.visit();
            budgetPage.verifyAvailableAmount('Gas', '$40.00');
    budgetPage.verifyAvailableAmount("Visa Signature", "$60.00");

    accountPage.visit();
    accountPage.verifyAccountBalance("Visa Signature", "-$60.00");
    accountPage.verifyAccountBalance("House Checking", "$5,000.00");
  });
});
