/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import allocationPage from "../../support/pages/AllocationPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_covering_overspending.sql";

describe("User Story 02 — Rolling with the Punches", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
  });

  it("covers Dining Out overspending by reallocating Groceries funds", () => {
    cy.intercept("POST", "/api/transactions").as("createTransaction");
    cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
    cy.intercept("POST", "/api/budget/allocations").as("createAllocation");
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
    cy.intercept("GET", "/api/accounts").as("fetchAccounts");

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Dining Out", "$100.00");
    budgetPage.verifyAvailableAmount("Groceries", "$500.00");
    budgetPage.rememberReadyToAssign();

    transactionPage.visit();
    cy.wait("@fetchTransactions");
    transactionPage.createOutflowTransaction("House Checking", "Dining Out", "120");
    cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");
    transactionPage.verifyError("");

    transactionPage.elements.transactionTableRows().first().within(() => {
      cy.contains("td", "House Checking").should("exist");
      cy.contains("td", "Dining Out").should("exist");
      cy.contains("td.amount-cell", "$120.00");
    });

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Dining Out", "-$20.00");
    budgetPage.verifyAvailableAmount("Groceries", "$500.00");
    budgetPage.expectReadyToAssignUnchanged();

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$880.00");

    allocationPage.visit();
    cy.wait("@fetchBudgets");
    allocationPage.categoryTransfer("Groceries", "Dining Out", "20");
    cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchBudgets");
    allocationPage.verifyError("");

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    budgetPage.verifyAvailableAmount("Dining Out", "$0.00");
    budgetPage.verifyAvailableAmount("Groceries", "$480.00");
    budgetPage.expectReadyToAssignUnchanged();

    accountPage.visit();
    cy.wait("@fetchAccounts");
    accountPage.verifyAccountBalance("House Checking", "$880.00");
  });
});
