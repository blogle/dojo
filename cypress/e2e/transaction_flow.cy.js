const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const formatAmount = (minor) => currencyFormatter.format(minor / 100);

const visitLedger = () => {
  cy.visit("/");
  cy.get('select[name="account_id"] option', { timeout: 10000 }).should(($options) => {
    expect($options.length).to.be.greaterThan(0);
  });
};

const setTodayDate = () => {
  cy.get('input[name="transaction_date"]').clear().type(todayISO());
};

const loadNetWorth = () => cy.request("/api/net-worth/current").its("body.net_worth_minor");

const expectNetWorthValue = (expectedMinor) => {
  const expectedText = formatAmount(expectedMinor);
  cy.get("#net-worth-value", { timeout: 10000 }).should(($el) => {
    expect($el.text().trim()).to.eq(expectedText);
  });
};

const todayISO = () => new Date().toISOString().slice(0, 10);

describe("Transaction Flow", () => {
  beforeEach(() => {
    visitLedger();
    setTodayDate();
  });

  it("shows validation errors for missing amount", () => {
    cy.get('input[name="amount"]').clear();
    cy.get('#transaction-form button[type="submit"]').click();
    cy.get('[data-error-for="amount_minor"]').should("have.text", "Enter a numeric amount.");
  });

  it("records a transaction and updates net worth", () => {
    const amountDollars = 12.34;
    const amountMinor = -Math.round(amountDollars * 100);

    loadNetWorth().then((initialNetWorth) => {
      cy.get('input[name="transaction_date"]').clear().type(todayISO());
      cy.get('select[name="account_id"]').select("house_checking");
      cy.get('select[name="category_id"]').select("groceries");
      cy.get('input[name="amount"]').clear().type(amountDollars.toFixed(2));
      cy.get('select[name="flow_direction"]').select("expense");
      cy.get('input[name="memo"]').clear().type("Cypress test");
      cy.get('#transaction-form button[type="submit"]').click();

      cy.get("#submission-status", { timeout: 10000 }).should("have.text", "Transaction recorded.");

      const expectedNetWorth = initialNetWorth + amountMinor;
      expectNetWorthValue(expectedNetWorth);

      cy.request("/api/net-worth/current")
        .its("body.net_worth_minor")
        .should("eq", expectedNetWorth);
    });
  });
});
