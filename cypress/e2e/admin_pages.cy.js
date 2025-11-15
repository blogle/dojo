const uniqueSlug = (prefix) => `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

const todayISO = () => new Date().toISOString().slice(0, 10);

describe("Admin Pages", () => {
  it("creates, edits, and removes an account", () => {
    const accountId = uniqueSlug("acct");

    cy.visit("/");
    cy.contains("button", "Accounts").click();

    cy.get('#account-form input[name="account_id"]').clear().type(accountId);
    cy.get('#account-form input[name="name"]').clear().type("Cypress Checking");
    cy.get('#account-form select[name="account_type"]').select("asset");
    cy.get('#account-form input[name="currency"]').clear().type("USD");
    cy.get('#account-form input[name="current_balance"]').clear().type("125.50");
    cy.get('#account-form input[name="opened_on"]').clear().type(todayISO());
    cy.get('#account-form input[name="is_active"]').check();
    cy.get('[data-account-submit]').click();

    cy.get('#account-status', { timeout: 10000 }).should("contain", "Account created.");
    cy.get('#accounts-table-body').should("contain", accountId);

    cy.contains("button", "Ledger").click();
    cy.get('select[name="account_id"]').find(`option[value="${accountId}"]`).should("exist");

    cy.contains("button", "Accounts").click();
    cy.get(`[data-account-edit="${accountId}"]`).click();
    cy.get('#account-form input[name="name"]').clear().type("Cypress Checking (Edited)");
    cy.get('#account-form input[name="current_balance"]').clear().type("210.10");
    cy.get('[data-account-submit]').click();
    cy.get('#account-status').should("contain", "Account updated.");

    cy.get(`[data-account-remove="${accountId}"]`).click();
    cy.get('#account-status').should("contain", `Account ${accountId} removed.`);
    cy.get(`[data-account-remove="${accountId}"]`).should("be.disabled");

    cy.contains("button", "Ledger").click();
    cy.get('select[name="account_id"]').find(`option[value="${accountId}"]`).should("not.exist");
  });

  it("creates, edits, and removes a budget category", () => {
    const categoryId = uniqueSlug("cat");

    cy.visit("/");
    cy.contains("button", "Budgets").click();

    cy.get('#category-form input[name="category_id"]').clear().type(categoryId);
    cy.get('#category-form input[name="name"]').clear().type("Cypress Fun");
    cy.get('#category-form input[name="is_active"]').check();
    cy.get('[data-category-submit]').click();

    cy.get('#category-status', { timeout: 10000 }).should("contain", "Category created.");
    cy.get('#categories-table-body').should("contain", categoryId);

    cy.contains("button", "Ledger").click();
    cy.get('select[name="category_id"]').find(`option[value="${categoryId}"]`).should("exist");

    cy.contains("button", "Budgets").click();
    cy.get(`[data-category-edit="${categoryId}"]`).click();
    cy.get('#category-form input[name="name"]').clear().type("Cypress Fun (Edited)");
    cy.get('[data-category-submit]').click();
    cy.get('#category-status').should("contain", "Category updated.");

    cy.get(`[data-category-remove="${categoryId}"]`).click();
    cy.get('#category-status').should("contain", `Category ${categoryId} removed.`);
    cy.get(`[data-category-remove="${categoryId}"]`).should("be.disabled");

    cy.contains("button", "Ledger").click();
    cy.get('select[name="category_id"]').find(`option[value="${categoryId}"]`).should("not.exist");
  });
});
