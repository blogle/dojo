/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import allocationPage from "../../support/pages/AllocationPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_covering_overspending.sql";

describe("User Story 02 — Rolling with the Punches", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: FIXTURE });
  });

  it("covers Dining Out overspending by reallocating Groceries funds", () => {
    budgetPage.visit();
    budgetPage.verifyAvailableAmount("Dining Out", "$100.00");
    budgetPage.verifyAvailableAmount("Groceries", "$500.00");
    budgetPage.rememberReadyToAssign();

    transactionPage.visit();
    transactionPage.createOutflowTransaction("House Checking", "Dining Out", "120");
    transactionPage.verifyError("");

    transactionPage.elements.transactionTableRows().first().within(() => {
      cy.contains("td", "House Checking").should("exist");
      cy.contains("td", "Dining Out").should("exist");
      cy.contains("td.amount-cell", "$120.00");
    });

    budgetPage.visit();
            budgetPage.verifyAvailableAmount('Dining Out', '-$20.00');
    budgetPage.verifyAvailableAmount("Groceries", "$500.00");
    budgetPage.expectReadyToAssignUnchanged();

    accountPage.visit();
    accountPage.verifyAccountBalance("House Checking", "$880.00");

    allocationPage.visit();
    allocationPage.categoryTransfer("Groceries", "Dining Out", "20");
    allocationPage.verifyError("");

    budgetPage.visit();
    budgetPage.verifyAvailableAmount("Dining Out", "$0.00");
    budgetPage.verifyAvailableAmount("Groceries", "$480.00");
    budgetPage.expectReadyToAssignUnchanged();

    accountPage.visit();
    accountPage.verifyAccountBalance("House Checking", "$880.00");
  });
});
