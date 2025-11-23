/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_editable_ledger_rows.sql";

describe("User Story 06 — Editable Ledger Rows", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
  });

  it("edits an erroneous utility payment down to 30.00 while keeping Ready-to-Assign stable", () => {
    cy.intercept("POST", "/api/transactions").as("mutateTransaction");
    cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
    cy.intercept("GET", "/api/accounts").as("fetchAccounts");

    const today = new Date();
    const correctedDateObj = new Date(today.getTime());
    if (today.getDate() > 1) {
      correctedDateObj.setDate(today.getDate() - 1);
    }
    const correctedDate = correctedDateObj.toISOString().slice(0, 10);

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Utilities", "$400.00");
    budgetPage.rememberReadyToAssign();

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$5,000.00");

    transactionPage.visit();
    cy.wait("@fetchTransactions");
    transactionPage.createOutflowTransaction("House Checking", "Utilities", "300");
    cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");
    transactionPage.verifyError("");
    transactionPage.verifyTransactionRowAmount(0, "$300.00");
    transactionPage.verifyTransactionStatus(0, "pending");

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Utilities", "$100.00");
    budgetPage.expectReadyToAssignUnchanged();

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$4,700.00");

    transactionPage.visit();
    transactionPage.editTransaction(0);
    transactionPage.setInlineDate(correctedDate);
    transactionPage.selectInlineAccount("House Checking");
    transactionPage.selectInlineCategory("Utilities");
    transactionPage.setInlineMemo("Corrected utility payment");
    transactionPage.setInlineOutflow("30");
    transactionPage.toggleTransactionStatus();
    transactionPage.saveInlineEdit();

    cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");

    transactionPage.verifyTransactionRowByMemo("Corrected utility payment", {
      amount: "$30.00",
      date: correctedDate,
      status: "cleared",
    });

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Utilities", "$370.00");
    budgetPage.expectReadyToAssignUnchanged();

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$4,970.00");
  });
});
