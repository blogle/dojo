import budgetPage from "../../support/pages/BudgetPage";

const FIXTURE = "tests/fixtures/e2e_budget_group_reorder.sql";

describe("User Story 18 — Budget Group Reorder", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/budget-category-groups").as("fetchGroups");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("PUT", "/api/budget-category-groups/*").as("updateGroup");

		budgetPage.visit();
		cy.wait("@fetchGroups");
		cy.wait("@fetchBudgets");
	});

	it("reorders groups via drag and drop and persists after save", () => {
		const initialOrder = ["Housing", "Groceries", "Fun Money"];
		budgetPage.assertGroupOrder(initialOrder);
		budgetPage.assertGroupContainsCategories("Fun Money", ["Eating Out"]);

		budgetPage.enterReorderMode();
		budgetPage.dragGroup("Fun Money", "Housing");
		budgetPage.assertGroupOrder(["Fun Money", "Housing", "Groceries"]);
		budgetPage.assertGroupContainsCategories("Fun Money", ["Eating Out"]);

		budgetPage.saveReorder();
		cy.wait("@updateGroup").its("response.statusCode").should("eq", 200);
		cy.wait("@updateGroup").its("response.statusCode").should("eq", 200);
		cy.wait("@updateGroup").its("response.statusCode").should("eq", 200);
		cy.wait("@fetchGroups");
		cy.wait("@fetchBudgets");

		cy.get("[data-budgets-reorder]").should("not.be.disabled");
		cy.get("[data-budgets-reorder-save]").should("be.disabled");
		cy.get("[data-budgets-reorder-cancel]").should("be.disabled");
		budgetPage.assertGroupOrder(["Fun Money", "Housing", "Groceries"]);

		cy.reload();
		cy.wait("@fetchGroups");
		cy.wait("@fetchBudgets");
		budgetPage.assertGroupOrder(["Fun Money", "Housing", "Groceries"]);
		budgetPage.assertGroupContainsCategories("Fun Money", ["Eating Out"]);
	});

	it("cancels reorder and restores the original ordering", () => {
		const initialOrder = ["Housing", "Groceries", "Fun Money"];
		budgetPage.assertGroupOrder(initialOrder);

		budgetPage.enterReorderMode();
		budgetPage.dragGroup("Housing", "Fun Money");
		budgetPage.assertGroupOrder(["Groceries", "Fun Money", "Housing"]);

		budgetPage.cancelReorder();
		budgetPage.assertGroupOrder(initialOrder);
		cy.get("[data-budgets-reorder]").should("not.be.disabled");
		cy.get("[data-budgets-reorder-save]").should("be.disabled");
		cy.get("[data-budgets-reorder-cancel]").should("be.disabled");
		cy.get("@updateGroup.all").should("have.length", 0);
	});
});
