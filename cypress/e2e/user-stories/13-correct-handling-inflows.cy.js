/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_correct_handling_inflows.sql";

describe("User Story 13 — Correct Handling of Inflows in Ledger", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
    cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
    cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
    cy.intercept("GET", "/api/accounts*").as("fetchAccounts");
    cy.intercept("POST", "/api/transactions").as("createTransaction");
  });

  it("renders a refund as a positive inflow and keeps summaries in sync", () => {
    const today = new Date().toISOString().slice(0, 10);

    transactionPage.visit();
    cy.wait("@fetchTransactions");

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    budgetPage.verifyActivity("$0.00");
    budgetPage.rememberReadyToAssign();

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$1,000.00");

    transactionPage.visit();
    transactionPage.createTransaction("inflow", "House Checking", "Refunds", "200");
    cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    budgetPage.expectReadyToAssignUnchanged();
    budgetPage.verifyActivity("$200.00");

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$1,200.00");

    transactionPage.visit();
    cy.wait("@fetchTransactions");
    cy.contains("#transactions-body tr", "Refunds").within(() => {
      cy.contains("td", today).should("exist");
      cy.get("td.amount-cell").eq(0).should("contain", "—");
      cy.get("td.amount-cell").eq(1).should("contain", "$200.00");
    });
  });
});
