/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import budgetPage from "../../support/pages/BudgetPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_credit_transaction_correction_workflow.sql";
const FIXED_NOW = new Date("2024-01-15T12:00:00Z").getTime();

describe("User Story 16 — Credit Transaction Correction Workflow", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.clock(FIXED_NOW);
		cy.intercept("POST", "/api/transactions").as("mutateTransaction");
		cy.intercept("PUT", "/api/transactions/*").as("updateTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
		cy.intercept("GET", "/api/budget-categories*").as("fetchBudgets");
		cy.intercept("GET", "/api/accounts").as("fetchAccounts");
		cy.intercept("GET", "/api/net-worth/current").as("fetchNetWorth");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
	});

	it("corrects a credit card transaction by changing the account and updates all summaries", () => {
		const transactionAmount = "20.00";
		const diningOutCategory = "Dining Out";
		const visaAccount = "Visa Signature";
		const mastercardAccount = "Mastercard Rewards";

		const expectAvailable = (categoryName, expectedAmount) => {
			budgetPage.verifyAvailableAmount(categoryName, expectedAmount);
		};

		// Initial state verification
		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		expectAvailable(diningOutCategory, "$300.00");
		expectAvailable("Visa Signature Payment", "$1,000.00");
		expectAvailable("Mastercard Rewards Payment", "$500.00");

		accountPage.visit();
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		accountPage.verifyAccountBalance(mastercardAccount, "$500.00");
		accountPage.verifyNetWorth("$3,500.00");
		cy.get("#net-worth").invoke("text").as("initialNetWorth");

		// Record a transaction on the wrong credit account (Visa)
		transactionPage.visit();
		cy.wait("@fetchTransactions");
		transactionPage.createOutflowTransaction(
			visaAccount,
			diningOutCategory,
			transactionAmount,
		);
		cy.wait("@mutateTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchTransactions");
		transactionPage.verifyTransactionRowAmount(0, transactionAmount);

		// Verify budgets after initial (wrong) transaction
		const today = new Date(FIXED_NOW);
		const monthStart = today.toISOString().slice(0, 7) + "-01";
		const expectBudgetApi = ({ diningOut, visaPayment, masterPayment }) => {
			cy.request("GET", `/api/budget-categories?month=${monthStart}`).then(
				({ body }) => {
					const amounts = Object.fromEntries(
						body.map((c) => [c.name, c.available_minor]),
					);
					cy.log(`api_budget_state=${JSON.stringify(amounts)}`);
					if (diningOut !== undefined) {
						expect(amounts[diningOutCategory]).to.eq(diningOut);
					}
					if (visaPayment !== undefined) {
						expect(amounts["Visa Signature Payment"]).to.eq(visaPayment);
					}
					if (masterPayment !== undefined) {
						expect(amounts["Mastercard Rewards Payment"]).to.eq(masterPayment);
					}
				},
			);
		};

		expectBudgetApi({
			diningOut: 28000,
			visaPayment: 102000,
			masterPayment: 50000,
		});

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		expectAvailable(diningOutCategory, "$280.00"); // 300 - 20
		expectAvailable("Visa Signature Payment", "$1,020.00"); // 1000 + 20
		expectAvailable("Mastercard Rewards Payment", "$500.00");

		// Verify account balances and net worth after initial transaction
		accountPage.visit();
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		accountPage.verifyAccountBalance(mastercardAccount, "$500.00");
		accountPage.verifyNetWorth("$3,480.00");
		// Net worth should reflect the spending
		cy.get("#net-worth").invoke("text").should("not.eq", "@initialNetWorth");

		// Edit the transaction to correct the account (from Visa to Mastercard)
		transactionPage.visit();
		cy.wait("@fetchTransactions");
		// Use row index 0 as it's the newest transaction (time frozen)
		transactionPage.editTransaction(0);
		transactionPage.selectInlineAccount(mastercardAccount);
		transactionPage.saveInlineEdit();
		cy.wait("@updateTransaction").its("response.statusCode").should("eq", 200);
		cy.wait("@fetchTransactions");

		// Verify budgets after correction
		expectBudgetApi({
			diningOut: 28000,
			visaPayment: 100000,
			masterPayment: 52000,
		});

		budgetPage.visit();
		cy.wait("@fetchBudgets");
		cy.wait("@fetchReady");
		expectAvailable(diningOutCategory, "$280.00"); // Should still be 280
		expectAvailable("Visa Signature Payment", "$1,000.00"); // Back to initial
		expectAvailable("Mastercard Rewards Payment", "$520.00"); // 500 + 20

		// Verify account balances and net worth after correction
		accountPage.visit();
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		accountPage.verifyAccountBalance(visaAccount, "$1,000.00"); // Back to initial
		accountPage.verifyAccountBalance(mastercardAccount, "$520.00"); // Increased liability
		accountPage.verifyNetWorth("$3,480.00");
		cy.get("#net-worth").invoke("text").should("not.eq", "@initialNetWorth"); // Should still reflect spending
	});
});
