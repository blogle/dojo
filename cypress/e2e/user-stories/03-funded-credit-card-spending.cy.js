/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_funded_credit_card_spending.sql";

describe("User Story 03 — Funded Credit Card Spending", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
  });

  it("tracks category balances and credit liabilities when spending on card", () => {
    cy.intercept("POST", "/api/transactions").as("createTransaction");
    cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
    cy.intercept("GET", "/api/accounts").as("fetchAccounts");

    transactionPage.visit();
    cy.wait("@fetchTransactions");

    transactionPage.createOutflowTransaction("Visa Signature", "Gas", "60");
    cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");
    transactionPage.verifyError("");

    transactionPage.elements.transactionTableRows().first().within(() => {
      cy.contains("td", "Visa Signature").should("exist");
      cy.contains("td", "Gas").should("exist");
      cy.contains("td.amount-cell", "$60.00");
    });

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Gas", "$40.00");
    budgetPage.verifyAvailableAmount("Visa Signature", "$60.00");

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("Visa Signature", "$60.00");
    accountPage.verifyAccountBalance("House Checking", "$5,000.00");
  });
});
