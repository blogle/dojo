const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const formatAmount = (minor) => currencyFormatter.format(minor / 100);

const todayISO = () => new Date().toISOString().slice(0, 10);

const formatAmountFromApi = (minor) => currencyFormatter.format(minor / 100);

describe("Transaction Flow", () => {
  beforeEach(() => {
    cy.visit("/");
  });

  it("shows net worth header matching the API", () => {
    cy.contains("a", "Assets & Liabilities").click();
    cy.request("/api/net-worth/current").then((resp) => {
      const expected = formatAmountFromApi(resp.body.net_worth_minor);
      cy.get("#net-worth").should("have.text", expected);
    });
  });

  it("displays Ready to Assign derived from the backend", () => {
    cy.contains("a", "Assets & Liabilities").click();
    cy.request("/api/budget/ready-to-assign").then((resp) => {
      const expected = formatAmountFromApi(resp.body.ready_to_assign_minor);
      cy.get("#ready-to-assign").should("have.text", expected);
    });
  });
});
