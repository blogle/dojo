const uniqueSlug = (prefix) => `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

const todayISO = () => new Date().toISOString().slice(0, 10);

describe("Admin Pages", () => {
  it("creates an account via the Assets & Liabilities workspace", () => {
    const accountName = uniqueSlug("Cypress Account");

    cy.visit("/");
    cy.contains("a", "Assets & Liabilities").click();
    cy.get("#accounts-page").should("have.class", "active");

    cy.get(".account-group", { timeout: 10000 }).should("have.length", 0);

    cy.get("[data-add-account-button]").should("be.visible").click();
    cy.get("#account-modal").should("have.class", "is-visible");
    cy.get("select[name='type']").should("be.visible").select("checking");
    cy.get("input[name='name']").clear().type(accountName);
    cy.get("input[name='balance']").clear().type("180.00");
    cy.get("[data-add-account-submit]").click();

    cy.contains(".account-card__name", accountName, { timeout: 15000 }).should("be.visible");
    cy.contains(".account-group__title", "Cash & Checking").should("be.visible");
  });

  it("exposes the Budgets navigation link", () => {
    cy.visit("/");
    cy.get("a[data-route-link='budgets']").should("have.attr", "href", "#/budgets");
  });
});
