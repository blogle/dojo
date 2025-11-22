/// <reference types="cypress" />

const FIXTURE = "tests/fixtures/e2e_manual_transaction_lifecycle.sql";

const getAccountBalance = (name) =>
  cy
    .contains(".account-card__name", name)
    .parents(".account-card")
    .find(".account-card__balance");

const rememberReadyToAssign = () => {
  cy.get("#budgets-ready-value")
    .invoke("text")
    .then((text) => cy.wrap(text.trim()).as("initialReady"));
};

const expectReadyToAssignUnchanged = () => {
  cy.get("@initialReady").then((expected) => {
    cy.get("#budgets-ready-value").should(($value) => {
      expect($value.text().trim()).to.eq(expected);
    });
  });
};

describe("User Story 05 — Manual Transaction Lifecycle", () => {
  beforeEach(() => {
    cy.request("POST", "/api/testing/reset_db");
    cy.request("POST", "/api/testing/seed_db", { fixture: FIXTURE });
  });

  it("edits a pending outflow, toggles cleared, and keeps Ready-to-Assign steady", () => {
    cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");

    cy.visit("/#/budgets");
    cy.wait("@fetchBudgets");
    cy.contains("#budgets-body tr", "Dining Out").should("contain", "$200.00");
    rememberReadyToAssign();

    cy.visit("/#/accounts");
    getAccountBalance("House Checking").should("contain", "$10,000.00");

    cy.visit("/#/transactions");
    cy.get("[data-transaction-account]").select("House Checking");
    cy.get("[data-transaction-category]").select("Dining Out");
    cy.get("#transaction-form input[name='amount']").clear().type("50");
    cy.get("[data-transaction-submit]").click();
    cy.get("[data-testid='transaction-error']").should("have.text", "");

    cy.get("#transactions-body tr").first().within(() => {
      cy.contains("td", "House Checking").should("exist");
      cy.contains("td", "Dining Out").should("exist");
      cy.contains("td.amount-cell", "$50.00");
      cy.get("[data-status-display]").should("have.attr", "data-state", "pending");
    });

    cy.visit("/#/budgets");
    cy.wait("@fetchBudgets");
    cy.contains("#budgets-body tr", "Dining Out").within(() => {
      cy.get("td").last().should("contain", "$150.00");
    });
    expectReadyToAssignUnchanged();

    cy.visit("/#/accounts");
    getAccountBalance("House Checking").should("contain", "$9,950.00");

    cy.visit("/#/transactions");
    cy.get("#transactions-body tr").first().click();
    cy.get("[data-inline-outflow]").clear().type("62");
    cy.get("[data-inline-status-toggle]").click();
    cy.get("[data-inline-outflow]").type("{enter}");

    cy.get("#transactions-body tr").first().within(() => {
      cy.contains("td.amount-cell", "$62.00");
      cy.get("[data-status-display]").should("have.attr", "data-state", "cleared");
    });

    const monthStart = new Date().toISOString().slice(0, 7) + "-01";
    cy.request(`/api/budget-categories?month=${monthStart}`).then(({ body }) => {
      const dining = body.find((category) => category.category_id === "dining_out");
      expect(dining?.available_minor).to.eq(13800);
    });

    cy.get("[data-route-link='budgets']").click();
    cy.contains("#budgets-body tr", "Dining Out").then(($row) => {
      const text = $row.text();
      expect(text).to.include("$138.00");
    });
    expectReadyToAssignUnchanged();

    cy.visit("/#/accounts");
    getAccountBalance("House Checking").should("contain", "$9,938.00");
  });
});
