const uniqueSlug = (prefix) => `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
const todayISO = () => new Date().toISOString().slice(0, 10);
const parseDisplay = (value) => Number(value.replace(/[^0-9.-]/g, "")) || 0;

describe("Budgeting Flow", () => {
  beforeEach(() => {
    cy.visit("/");
  });

  it("completes the full income -> allocate -> spend cycle", () => {
    const incomeMemo = `Paycheck ${Date.now()}`;
    const expenseMemo = `Groceries ${Date.now()}`;
    const categoryName = `Food ${Date.now()}`;
    const incomeAmount = 1000.00;
    const allocateAmount = 500.00;
    const spendAmount = 125.50;

    // 1. Record Income
    cy.visit("/#/transactions");
    cy.get("[data-testid='transaction-form']").within(() => {
      cy.get("input[name='transaction_date']").clear().type(todayISO());
      cy.get("input[name='transaction-flow'][value='inflow']").check({ force: true });
      cy.get("[data-transaction-account]").select("house_checking");
      cy.get("[data-transaction-category]").select("income");
      cy.get("input[name='memo']").clear().type(incomeMemo);
      cy.get("input[name='amount']").clear().type(incomeAmount.toString());
      cy.get("[data-transaction-submit]").click();
    });
    cy.get("[data-testid='transaction-error']").should("have.text", "");

    // 2. Create Category
    cy.visit("/#/budgets");
    cy.get("[data-open-category-modal]").click();
    cy.get("[data-category-name]").clear().type(categoryName);
    // Slug is auto-generated
    cy.get("[data-category-submit]").click();
    cy.get("#category-modal").should("have.attr", "aria-hidden", "true");

    // 3. Allocate Funds
    cy.visit("/#/allocations");
    cy.get("[data-testid='allocation-form']").within(() => {
      cy.get("input[name='allocation_date']").clear().type(todayISO());
      // Wait for category to appear in dropdown
      cy.get("[data-allocation-to]").contains(categoryName, { timeout: 10000 });
      // Select by text content since value is dynamic slug
      cy.get("[data-allocation-to]").contains(categoryName).then($option => {
        cy.get("[data-allocation-to]").select($option.val());
      });
      cy.get("input[name='amount']").clear().type(allocateAmount.toString());
      cy.get("[data-allocation-submit]").click();
    });
    cy.get("[data-testid='allocation-error']").should("have.text", "");
    // Wait for success toast or table update
    cy.contains(".toast", "Moved", { timeout: 10000 }).should("be.visible");

    // 4. Verify Budget Available
    cy.visit("/#/budgets");
    cy.get("#budgets-body").contains("tr", categoryName).within(() => {
      // Use .amount-cell to avoid Name column. Available is the 3rd amount cell (index 2)
      cy.get(".amount-cell").eq(2).invoke("text").then(text => {
        expect(parseDisplay(text)).to.equal(allocateAmount);
      });
    });

    // 5. Record Expense
    cy.visit("/#/transactions");
    cy.get("[data-testid='transaction-form']").within(() => {
      cy.get("input[name='transaction_date']").clear().type(todayISO());
      cy.get("input[name='transaction-flow'][value='outflow']").check({ force: true });
      cy.get("[data-transaction-account]").select("house_checking");
      // Select the new category
      cy.get("[data-transaction-category]").contains(categoryName).then($option => {
        cy.get("[data-transaction-category]").select($option.val());
      });
      cy.get("input[name='memo']").clear().type(expenseMemo);
      cy.get("input[name='amount']").clear().type(spendAmount.toString());
      cy.get("[data-transaction-submit]").click();
    });
    
    // Wait for transaction to appear in ledger to ensure it posted
    cy.contains("tr", expenseMemo).should("be.visible");

    // 6. Verify Budget Updated
    cy.visit("/#/budgets");
    cy.get("#budgets-body").contains("tr", categoryName).within(() => {
      // Available = Allocated - Spent
      // Use .amount-cell to avoid Name column. Available is the 3rd amount cell (index 2)
      cy.get(".amount-cell").eq(2).should(($cell) => {
        const text = $cell.text();
        expect(parseDisplay(text)).to.be.closeTo(allocateAmount - spendAmount, 0.01);
      });
      // Activity = Spent (displayed as positive)
      // Activity is the 2nd amount cell (index 1)
      cy.get(".amount-cell").eq(1).should(($cell) => {
        const text = $cell.text();
        expect(parseDisplay(text)).to.be.closeTo(spendAmount, 0.01);
      });
    });
  });
});
