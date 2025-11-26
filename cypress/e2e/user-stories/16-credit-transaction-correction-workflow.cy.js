/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_credit_transaction_correction_workflow.sql";

describe("User Story 16 — Credit Transaction Correction Workflow", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
    cy.intercept("POST", "/api/transactions").as("mutateTransaction");
    cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
    cy.intercept("GET", "/api/accounts").as("fetchAccounts");
    cy.intercept("GET", "/api/net-worth/current").as("fetchNetWorth");
    cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
  });

  it("corrects a credit card transaction by changing the account and updates all summaries", () => {
    const transactionAmount = "20.00";
    const diningOutCategory = "Dining Out";
    const visaAccount = "Visa Signature";
    const mastercardAccount = "Mastercard Rewards";

    // Initial state verification
    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    budgetPage.verifyAvailableAmount(diningOutCategory, "$300.00");
    budgetPage.verifyAvailableAmount("Visa Signature Payment", "$1,000.00");
    budgetPage.verifyAvailableAmount("Mastercard Rewards Payment", "$500.00");

    accountPage.visit();
    cy.wait("@fetchAccounts");
    cy.wait("@fetchNetWorth");
    accountPage.verifyAccountBalance(visaAccount, "$1,000.00");
    accountPage.verifyAccountBalance(mastercardAccount, "$500.00");
    cy.get("#net-worth").invoke("text").as("initialNetWorth");

    // Record a transaction on the wrong credit account (Visa)
    transactionPage.visit();
    cy.wait("@fetchTransactions");
    transactionPage.createOutflowTransaction(visaAccount, diningOutCategory, transactionAmount);
    cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");
    transactionPage.verifyTransactionRowAmount(0, transactionAmount);

    // Verify budgets after initial (wrong) transaction
    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    budgetPage.verifyAvailableAmount(diningOutCategory, "$280.00"); // 300 - 20
    budgetPage.verifyAvailableAmount("Visa Signature Payment", "$1,020.00"); // 1000 + 20
    budgetPage.verifyAvailableAmount("Mastercard Rewards Payment", "$500.00");

    // Verify account balances and net worth after initial transaction
    accountPage.visit();
    cy.wait("@fetchAccounts");
    cy.wait("@fetchNetWorth");
    accountPage.verifyAccountBalance(visaAccount, "$1,020.00");
    accountPage.verifyAccountBalance(mastercardAccount, "$500.00");
    // Net worth should reflect the spending
    cy.get("#net-worth").invoke("text").should("not.eq", "@initialNetWorth");

    // Edit the transaction to correct the account (from Visa to Mastercard)
    transactionPage.visit();
    cy.wait("@fetchTransactions");
    transactionPage.editTransaction(0); // Assuming it's the first row
    transactionPage.selectInlineAccount(mastercardAccount);
    transactionPage.saveInlineEdit();
    cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");

    // Verify budgets after correction
    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    budgetPage.verifyAvailableAmount(diningOutCategory, "$280.00"); // Should still be 280
    budgetPage.verifyAvailableAmount("Visa Signature Payment", "$1,000.00"); // Back to initial
    budgetPage.verifyAvailableAmount("Mastercard Rewards Payment", "$520.00"); // 500 + 20

    // Verify account balances and net worth after correction
    accountPage.visit();
    cy.wait("@fetchAccounts");
    cy.wait("@fetchNetWorth");
    accountPage.verifyAccountBalance(visaAccount, "$1,000.00"); // Back to initial
    accountPage.verifyAccountBalance(mastercardAccount, "$520.00"); // Increased liability
    cy.get("#net-worth").invoke("text").should("not.eq", "@initialNetWorth"); // Should still reflect spending
  });
});