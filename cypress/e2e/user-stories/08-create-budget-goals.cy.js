import budgetPage from "../../support/pages/BudgetPage";

const FIXTURE = "tests/fixtures/e2e_create_budget_goals.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 08 — Creating a Budget (Recurring or Target Date)", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("POST", "/api/budget-categories").as("createBudget");
		budgetPage.visit();
		cy.wait("@fetchBudgets");
	});

	it("creates a target-date Vacation budget and shows derived monthly target", () => {
		const budgetName = "Vacation";
		const targetDate = "2026-05-01";
		const targetAmount = "1200.00";

		budgetPage.openAddBudgetModal();
		budgetPage.createTargetDateBudget(
			budgetName,
			null,
			targetDate,
			targetAmount,
		);
		cy.wait("@createBudget").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchBudgets");

		budgetPage
			.categoryRow(budgetName)
			.should("be.visible")
			.find("td.amount-cell:nth-child(2)")
			.should("contain", "$0.00");
	});

	it("creates a recurring Car Insurance budget with quarterly frequency", () => {
		const budgetName = "Car Insurance";
		const frequency = "quarterly";
		const recurringDate = "2026-01-01";
		const recurringAmount = "300.00";

		budgetPage.openAddBudgetModal();
		budgetPage.createRecurringBudget(
			budgetName,
			null,
			frequency,
			recurringDate,
			recurringAmount,
		);
		cy.wait("@createBudget").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchBudgets");

		budgetPage
			.categoryRow(budgetName)
			.should("be.visible")
			.find("td.amount-cell:nth-child(2)")
			.should("contain", "$0.00");
	});
});
