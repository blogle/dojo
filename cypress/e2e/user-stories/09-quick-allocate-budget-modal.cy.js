import budgetPage from "../../support/pages/BudgetPage";

const SUFFICIENT_FIXTURE =
	"tests/fixtures/e2e_quick_allocate_budget_sufficient.sql";
const INSUFFICIENT_FIXTURE =
	"tests/fixtures/e2e_quick_allocate_budget_insufficient.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

describe("User Story 09 — Quick Allocate Actions from Budget Modal", () => {
	context("Successful Allocation", () => {
		beforeEach(() => {
			Cypress.env("TEST_DATE", TEST_DATE);
			cy.clock(FIXED_NOW, ["Date"]);
			cy.resetDatabase();
			cy.seedDatabase(SUFFICIENT_FIXTURE);
			cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
			cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
			cy.intercept("POST", "/api/budget/allocations").as("allocateBudget");
			budgetPage.visit();
			cy.wait("@fetchBudgets");
			cy.wait("@fetchReady");
		});

		it("creates an allocation row and updates balances when Ready-to-Assign is sufficient", () => {
			const categoryName = "Netflix";
			const quickAllocateAmount = "$15.00";
			const expectedRTAAfter = "$185.00"; // $200 - $15
			const expectedAvailableAfter = "$15.00"; // $0 + $15
			const quickAllocateLabel = `Budgeted Last Month: ${quickAllocateAmount}`;

			budgetPage.verifyReadyToAssign("$200.00");
			budgetPage.verifyAvailableAmount(categoryName, "$0.00");

			budgetPage.openBudgetDetailModal(categoryName);
			budgetPage.clickQuickAllocateButton(quickAllocateLabel);
			cy.wait("@allocateBudget").its("response.statusCode").should("eq", 201);
			cy.wait("@fetchBudgets");
			cy.wait("@fetchReady");

			budgetPage.verifyReadyToAssign(expectedRTAAfter);
			budgetPage.verifyAvailableAmount(categoryName, expectedAvailableAfter);
		});
	});

	context("Insufficient Funds", () => {
		let allocationCalled = false;

		beforeEach(() => {
			allocationCalled = false;
			Cypress.env("TEST_DATE", TEST_DATE);
			cy.clock(FIXED_NOW, ["Date"]);
			cy.resetDatabase();
			cy.seedDatabase(INSUFFICIENT_FIXTURE);
			cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
			cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
			cy.intercept("POST", "/api/budget/allocations", (req) => {
				allocationCalled = true;
				req.continue();
			}).as("allocateBudget");
			budgetPage.visit();
			cy.wait("@fetchBudgets");
			cy.wait("@fetchReady");
		});

		it("shows an error and skips the allocation when Ready-to-Assign is insufficient", () => {
			const categoryName = "Netflix";
			const quickAllocateAmount = "$15.00";
			const initialRTA = "$10.00";
			const initialAvailable = "$0.00";
			const quickAllocateLabel = `Budgeted Last Month: ${quickAllocateAmount}`;

			budgetPage.verifyReadyToAssign(initialRTA);
			budgetPage.verifyAvailableAmount(categoryName, initialAvailable);

			cy.window().then((win) => cy.stub(win, "alert").as("alertStub"));

			budgetPage.openBudgetDetailModal(categoryName);
			budgetPage.clickQuickAllocateButton(quickAllocateLabel);

			cy.get("@alertStub").should(
				"have.been.calledWith",
				"Not enough Ready to Assign funds.",
			);
			cy.wrap(null).then(() => {
				expect(allocationCalled).to.be.false;
			});

			budgetPage.verifyReadyToAssign(initialRTA);
			budgetPage.verifyAvailableAmount(categoryName, initialAvailable);
		});
	});
});
