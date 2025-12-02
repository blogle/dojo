/// <reference types="cypress" />

import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";
import transferPage from "../../support/pages/TransferPage";

const FIXTURE = "tests/fixtures/e2e_categorized_investment_transfer.sql";

describe("User Story 04 — Categorized Investment Transfer", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
  });

  it("moves funds from checking into brokerage while tagging Future Home", () => {
    budgetPage.visit();
    budgetPage.verifyAvailableAmount("Future Home", "$1,000.00");

    accountPage.visit();
    accountPage.verifyAccountBalance("House Checking", "$50,000.00");
    accountPage.verifyAccountBalance("Brokerage", "$5,000.00");

    transferPage.visit();
    transferPage.createTransfer("House Checking", "Brokerage", "Future Home", "1000");
    transferPage.verifyError("");

    budgetPage.visit();
    budgetPage.verifyAvailableAmount("Future Home", "$0.00");

    accountPage.visit();
    accountPage.verifyAccountBalance("House Checking", "$49,000.00");
    accountPage.verifyAccountBalance("Brokerage", "$6,000.00");
  });
});
