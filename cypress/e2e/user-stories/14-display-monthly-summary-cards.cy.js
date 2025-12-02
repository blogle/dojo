/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import allocationPage from "../../support/pages/AllocationPage";

const FIXTURE = "tests/fixtures/e2e_monthly_summary_cards.sql";

const formatBudgetMonthLabel = () => {
  const today = new Date();
  const monthStart = new Date(today.getFullYear(), today.getMonth());
  return monthStart.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
  });
};

describe("User Story 14 — Display of Monthly Summary Cards Across Pages", () => {
  beforeEach(() => {
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
    cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
    cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
    cy.intercept("POST", "/api/transactions").as("persistTransaction");
    cy.intercept("POST", "/api/budget/allocations").as("createAllocation");
  });

  it("keeps the summary chips accurate while editing ledger rows and allocation entries", () => {
    transactionPage.visit();
    cy.wait("@fetchTransactions");
    cy.get("#month-spend").should("contain", "$150.00");
    cy.get("#month-budgeted").should("contain", "$450.00");
    cy.contains("#transactions-body tr", "Groceries run").should("exist");

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    cy.get("#budgets-ready-value")
      .should("not.contain", "—")
      .invoke("text")
      .as("initialReady");
    budgetPage.verifyActivity("$150.00");
    budgetPage.verifyAvailable("$500.00");
    cy.get("#budgets-month-label")
      .invoke("text")
      .then((label) => {
        expect(label.trim()).to.eq(formatBudgetMonthLabel());
      });

    transactionPage.visit();
    cy.contains("#transactions-body tr", "Groceries run").click();
    cy.get("[data-inline-outflow]").clear();
    cy.get("[data-inline-outflow]")
      .should("not.be.disabled")
      .type("200", { force: true });
    transactionPage.saveInlineEdit();
    cy.wait("@persistTransaction").its("response.statusCode").should("eq", 201);
    cy.wait("@fetchTransactions");
    cy.get("#month-spend").should("contain", "$200.00");

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    budgetPage.verifyActivity("$200.00");

    allocationPage.visit();
    allocationPage.categoryTransfer("Ready to Assign", "Rent", "100", "Monthly shift");
    cy.wait("@createAllocation").its("response.statusCode").should("eq", 201);

    budgetPage.visit();
    cy.wait("@fetchBudgets");
    cy.wait("@fetchReady");
    cy.get("@initialReady").then((initialReady) => {
      cy.get("#budgets-ready-value")
        .should("not.contain", "—")
        .invoke("text")
        .should((currentReady) => {
          expect(currentReady).not.to.eq(initialReady);
        });
    });

    transactionPage.visit();
    cy.wait("@fetchTransactions");
    cy.get("#month-budgeted").should("contain", "$550.00");
    cy.get("#month-spend").should("contain", "$200.00");
  });
});
