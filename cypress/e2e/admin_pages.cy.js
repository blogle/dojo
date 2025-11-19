const uniqueSlug = (prefix) => `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

const todayISO = () => new Date().toISOString().slice(0, 10);

const parseDisplay = (value) => Number(value.replace(/[^0-9.-]/g, "")) || 0;

describe("Admin Pages", () => {
  it.skip("creates an account via the Assets & Liabilities workspace", () => {
    const accountName = uniqueSlug("Cypress Account");

    cy.visit("/");
    cy.contains("a", "Assets & Liabilities").click();
    cy.get("#accounts-page").should("have.class", "active");

    cy.get(".account-group", { timeout: 10000 }).should("have.length", 0);

    cy.get("[data-add-account-button]").should("be.visible").click();
    cy.get("#account-modal").should("have.attr", "aria-hidden", "false");
    cy.get("select[name='type']").should("be.visible").select("checking");
    cy.get("input[name='name']").should("be.visible").clear().type(accountName);
    cy.get("input[name='balance']").should("be.visible").clear().type("180.00");
    cy.get("[data-add-account-submit]").click();

    cy.contains(".account-card__name", accountName, { timeout: 15000 }).should("be.visible");
    cy.contains(".account-group__title", "Cash & Checking").should("be.visible");
  });

  it("exposes the Budgets navigation link", () => {
    cy.visit("/");
    cy.get("a[data-route-link='budgets']").should("have.attr", "href", "#/budgets");
  });

  it("records expenses and inflows via the transaction form", () => {
    const expenseMemo = `Cypress expense ${Date.now()}`;
    const inflowMemo = `Cypress inflow ${Date.now()}`;

    cy.visit("/#/transactions");
    cy.get("[data-testid='transaction-form']").within(() => {
      cy.get("input[name='transaction_date']").clear().type(todayISO());
      cy.get("[data-transaction-account]").select("house_checking");
      cy.get("[data-transaction-category]").select("groceries");
      cy.get("input[name='memo']").clear().type(expenseMemo);
      cy.get("input[name='amount']").clear().type("23.45");
      cy.get("[data-transaction-submit]").click();
    });

    cy.get("[data-testid='transaction-error']").should("have.text", "");
    cy.get("#transactions-body tr").first().within(() => {
      cy.get("td").eq(3).should("contain.text", expenseMemo);
      cy.get("td").eq(4).invoke("text").should("include", "23.45");
    });

    cy.get("[data-testid='transaction-form']").within(() => {
      cy.get("input[name='memo']").clear().type(inflowMemo);
      cy.get("input[name='amount']").clear().type("150.00");
      cy.get("input[name='transaction-flow'][value='inflow']").check({ force: true });
      cy.get("[data-transaction-category]").select("income");
      cy.get("[data-transaction-account]").select("house_checking");
      cy.get("[data-transaction-submit]").click();
    });

    cy.get("[data-testid='transaction-error']").should("have.text", "");
    cy.get("#transactions-body tr").first().within(() => {
      cy.get("td").eq(3).should("contain.text", inflowMemo);
      cy.get("td").eq(5).invoke("text").should("include", "150.00").and("not.contain", "-");
    });

    cy.get("#transactions-body tr").first().click();
    cy.get("#transactions-body tr").first().within(() => {
      cy.get("[data-inline-inflow]").clear().type("175.00{enter}");
    });
    cy.get("#transactions-body tr").first().within(() => {
      cy.get("td").eq(3).should("contain.text", inflowMemo);
      cy.get("td").eq(5).invoke("text").should("include", "175.00");
    });
  });

  it("creates a category and allocates funds via the dedicated ledger", () => {
    const categoryName = `Envelope ${Date.now()}`;
    const categorySlug = uniqueSlug("envelope").toLowerCase().replace(/[^a-z0-9]+/g, "_");
    const allocationAmount = 12.34;
    let readyBefore;
    let availableBefore;

    cy.visit("/#/budgets");
    cy.get("[data-open-category-modal]").click();
    cy.get("[data-category-name]").clear().type(categoryName);
    cy.get("[data-category-slug]").clear().type(categorySlug);
    cy.get("[data-category-submit]").click();
    cy.get("#category-modal").should("have.attr", "aria-hidden", "true");

    cy.get("#budgets-ready-value").invoke("text").then((text) => {
      readyBefore = parseDisplay(text);
    });
    cy.contains(".budget-card", categoryName, { timeout: 15000 })
      .find(".budget-card__meta span")
      .first()
      .invoke("text")
      .then((text) => {
        availableBefore = parseDisplay(text);
      });

    cy.contains("a", "Allocations").click();
    cy.get("#allocations-page").should("have.class", "active");
    cy.get("[data-testid='allocation-form']").within(() => {
      cy.get("[data-allocation-to]").select(categorySlug);
      cy.get("input[name='amount']").clear().type(allocationAmount.toString());
      cy.get("input[name='memo']").clear().type("Cypress allocation");
      cy.get("input[name='allocation_date']").clear().type(todayISO());
      cy.root().submit();
    });

    cy.get("[data-testid='allocation-error']").should("have.text", "");
    cy.get("#allocations-body tr").first().within(() => {
      cy.get("td").eq(3).should("contain.text", categoryName);
    });

    cy.contains("a", "Budgets").click();
    cy.contains(".budget-card", categoryName)
      .find(".budget-card__meta span")
      .first()
      .should(($span) => {
        const next = parseDisplay($span.text());
        expect(next).to.be.closeTo(availableBefore + allocationAmount, 0.01);
      });
    cy.get("#budgets-ready-value").should(($value) => {
      const next = parseDisplay($value.text());
      expect(next).to.be.closeTo(readyBefore - allocationAmount, 0.01);
    });
  });

  it("runs the categorized transfer flow", () => {
    const memo = `Cypress transfer ${Date.now()}`;

    cy.visit("/#/transfers");
    cy.get("#transfer-form", { timeout: 10000 }).should("be.visible");
    cy.get("#transfer-form").within(() => {
      cy.get("input[name='transaction_date']").clear().type(todayISO());
      cy.get("[data-transfer-source]").select("house_checking");
      cy.get("[data-transfer-destination]").select("house_credit_card");
      cy.get("[data-transfer-category]").select("groceries");
      cy.get("input[name='memo']").clear().type(memo);
      cy.get("input[name='amount']").clear().type("42.50");
      cy.get("[data-transfer-submit]").click();
    });

    cy.get("[data-testid='transfer-error']").should("have.text", "");
    cy.get(".toast", { timeout: 10000 })
      .should("contain.text", "Transfer")
      .invoke("text")
      .then((text) => {
        const match = text.match(/Transfer\s+([0-9a-f-]+)/i);
        expect(match, "concept id present").to.not.be.null;
        const conceptId = match[1];
        cy.get(`#transactions-body tr[data-concept-id='${conceptId}']`, { timeout: 10000 }).should("have.length.at.least", 2);
      });
  });
});
