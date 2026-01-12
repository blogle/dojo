/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_editable_ledger_rows.sql";
// Fixed date: Nov 15, 2025
const TEST_DATE = "2025-11-15";
const FIXED_NOW = new Date("2025-11-15T12:00:00Z").getTime();

describe("User Story 06 — Editable Ledger Rows", () => {
	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		// Ensure backend is ready (checking Nov 2025 state)
		cy.ensureBackendState(
			"/api/budget-categories?month=2025-11-01",
			(categories) => {
				const utilities = categories.find((c) => c.name === "Utilities");
				return utilities && utilities.available_minor === 40000;
			},
		);
	});

	it("edits an erroneous utility payment down to 30.00 while keeping Ready-to-Assign stable", () => {
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		cy.intercept("PUT", "/api/transactions/*").as("updateTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchRTA");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");

		const correctedDate = "2025-11-14";

		budgetPage.visit();
		cy.wait(["@fetchBudgets", "@fetchRTA"]);
		budgetPage.verifyAvailableAmount("Utilities", "$400.00");
		// Ensure RTA is loaded (fixture: $5000 checking - $400 allocated = $4600)
		budgetPage.verifyReadyToAssign("$4,600.00");
		budgetPage.rememberReadyToAssign();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$5,000.00");

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		transactionPage.createOutflowTransaction(
			"House Checking",
			"Utilities",
			"300",
		);
		cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchTransactions");
		transactionPage.verifyError("");
		transactionPage.verifyTransactionRowAmount(0, "$300.00");
		transactionPage.verifyTransactionStatus(0, "pending");

		budgetPage.visit();
		cy.wait(["@fetchBudgets", "@fetchRTA"]);
		budgetPage.verifyAvailableAmount("Utilities", "$100.00");
		budgetPage.expectReadyToAssignUnchanged();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$4,700.00");

		transactionPage.visit();
		transactionPage.editTransaction(0);
		transactionPage.setInlineDate(correctedDate);
		transactionPage.selectInlineAccount("House Checking");
		transactionPage.selectInlineCategory("Utilities");
		transactionPage.setInlineMemo("Corrected utility payment");
		transactionPage.setInlineOutflow("30");
		transactionPage.toggleTransactionStatus();
		transactionPage.saveInlineEdit();

		cy.wait("@updateTransaction").its("response.statusCode").should("eq", 200);
		cy.wait("@fetchTransactions");

		transactionPage.verifyTransactionRowByMemo("Corrected utility payment", {
			amount: "$30.00",
			date: correctedDate,
			status: "cleared",
		});

		budgetPage.visit();
		cy.wait(["@fetchBudgets", "@fetchRTA"]);
		budgetPage.verifyAvailableAmount("Utilities", "$370.00");
		budgetPage.expectReadyToAssignUnchanged();

		accountPage.visit();
		cy.wait("@fetchAccounts");
		accountPage.verifyAccountBalance("House Checking", "$4,970.00");
	});

	it("removes a transaction by deleting the inline row", () => {
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		cy.intercept("PUT", "/api/transactions/*").as("updateTransaction");
		cy.intercept("DELETE", "/api/transactions/*").as("deleteTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");

		const transactionMemo = "Transaction to be removed";

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		transactionPage.createOutflowTransaction(
			"House Checking",
			"Utilities", // Use 'Utilities' as per fixture
			"50",
		);
		cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchTransactions");
		transactionPage.verifyTransactionRowAmount(0, "$50.00");
		transactionPage.verifyTransactionStatus(0, "pending");

		// Enter edit mode to set a memo and delete.
		transactionPage.editTransaction(0);
		transactionPage.setInlineMemo(transactionMemo);
		transactionPage.deleteInlineTransaction();
		cy.wait("@deleteTransaction").then(({ response }) => {
			expect([200, 204]).to.include(response?.statusCode);
		});
		cy.wait("@fetchTransactions");
		cy.contains("#transactions-body tr", transactionMemo).should("not.exist");
	});
});
