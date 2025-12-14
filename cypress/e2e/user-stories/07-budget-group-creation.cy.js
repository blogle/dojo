import budgetPage from "../../support/pages/BudgetPage";

const FIXTURE = "tests/fixtures/e2e_budget_group_creation.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 07 — Budget Group Creation and Assignment Flow", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/budget-category-groups").as("fetchGroups");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("POST", "/api/budget-category-groups").as("createGroup");
		cy.intercept("PUT", "/api/budget-categories/*").as("updateCategory");

		budgetPage.visit();
		cy.wait("@fetchGroups");
		cy.wait("@fetchBudgets");
	});

	it("creates a Subscriptions group and assigns Netflix + Spotify", () => {
		const groupName = "Subscriptions";
		const categories = ["Netflix", "Spotify"];

		budgetPage.createBudgetGroup(groupName);
		cy.wait("@createGroup")
			.its("response.statusCode")
			.should((statusCode) => {
				expect([200, 201]).to.include(statusCode);
			});
		cy.wait("@fetchBudgets");
		cy.wait("@fetchGroups");

		categories.forEach((category) => {
			budgetPage.assignCategoryToGroup(category, groupName);
			cy.wait("@updateCategory").its("response.statusCode").should("eq", 200);
			cy.wait("@fetchBudgets");
		});
		cy.wait("@fetchBudgets");

		budgetPage.verifyGroupContainsCategories(groupName, categories);
		categories.forEach((category) =>
			budgetPage.verifyCategoryNotInUncategorized(category),
		);
	});
});
