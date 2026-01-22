/// <reference types="cypress" />

import transactionPage from "../../support/pages/TransactionPage";
import accountPage from "../../support/pages/AccountPage";

const FIXTURE = "tests/fixtures/e2e_account_onboarding_ledger.sql";
const TEST_DATE = "2025-12-15";
const FIXED_NOW = new Date("2025-12-15T12:00:00Z").getTime();

const checkingAccount = {
	type: "checking",
	name: "Home Checking",
	balance: "5000",
	heroDisplay: "$5,000.00",
	ledgerDisplay: "$5,000.00",
	modalDisplay: "$5,000.00",
};

const creditAccount = {
	type: "credit",
	name: "Rewards Credit",
	balance: "1200",
	heroDisplay: "$1,200.00",
	ledgerDisplay: "$1,200.00",
	modalDisplay: "$1,200.00",
};

describe("User Story 15 — Account Onboarding Ledger Integrity", () => {
	const addAccountThroughModal = (account) => {
		cy.get("[data-add-account-button]").click();
		cy.get("#account-modal").should("be.visible");

		// Step 1: Select Type
		// account.type is "checking" or "credit", mapped to "Cash & Checking" or "Credit Card"
		const typeLabel =
			account.type === "checking" ? "Cash & Checking" : "Credit Card";
		cy.contains(".type-card", typeLabel).click();
		cy.contains("button", "Next").click();

		// Step 2: Details
		// The label depends on type: "Account Nickname" or "Card Nickname"
		const nameLabel =
			account.type === "checking" ? "Account Nickname" : "Card Nickname";
		cy.contains("label", nameLabel).find("input").clear().type(account.name);
		cy.contains("button", "Next").click();

		// Step 3: Balance
		// Label depends on type
		const balanceLabel =
			account.type === "checking"
				? "Current Ledger Balance"
				: "Current Amount Owed";
		cy.contains("label", balanceLabel)
			.find("input")
			.clear()
			.type(account.balance);
		// Ensure date is filled (defaults to today, which is mocked, so fine)
		cy.contains("button", "Next").click();

		// Step 4: Review & Submit
		cy.contains("button", "Create Account").click();

		cy.wait("@createAccount").its("response.statusCode").should("eq", 201);
		cy.wait("@createTransaction").its("response.statusCode").should("eq", 201);
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		cy.wait("@fetchReady");
	};

	const verifyOpeningBalanceRow = (account) => {
		cy.contains("#transactions-body tr", account.name, {
			timeout: 20000,
		}).within(() => {
			cy.contains("td", "Opening Balance").should("exist");
			cy.contains("td.amount-cell", account.ledgerDisplay).should("exist");
			cy.contains("td", "Opening balance").should("exist");
		});
	};

	const verifyModalBalance = (account) => {
		const expectedBalance = account.modalDisplay ?? account.heroDisplay;
		cy.contains(".account-card__name", account.name)
			.closest(".account-card")
			.click();
		// Account detail is now a routed page instead of a modal.
		cy.get(".investments-header__value").should("contain", expectedBalance);
		cy.go("back");
	};

	beforeEach(() => {
		Cypress.env("TEST_DATE", TEST_DATE);
		cy.clock(FIXED_NOW, ["Date"]);
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		cy.intercept("GET", "/api/accounts*").as("fetchAccounts");
		cy.intercept("GET", "/api/net-worth/current").as("fetchNetWorth");
		cy.intercept("GET", "/api/budget/ready-to-assign*").as("fetchReady");
		cy.intercept("POST", "/api/accounts").as("createAccount");
		cy.intercept("POST", "/api/transactions").as("createTransaction");
		cy.intercept("GET", "/api/transactions*").as("fetchTransactions");
	});

	it("records opening balances, shows cards/modals, and reconciles hero stats", () => {
		accountPage.visit();
		cy.wait("@fetchAccounts");
		cy.wait("@fetchNetWorth");
		cy.wait("@fetchReady");

		addAccountThroughModal(checkingAccount);
		addAccountThroughModal(creditAccount);

		cy.get("#assets-total").should("contain", checkingAccount.heroDisplay);
		cy.get("#liabilities-total").should("contain", creditAccount.heroDisplay);
		cy.get("#net-worth").should("contain", "$3,800.00");

		transactionPage.visit();
		cy.wait("@fetchTransactions");
		verifyOpeningBalanceRow(checkingAccount);
		verifyOpeningBalanceRow(creditAccount);

		accountPage.visit();

		accountPage.verifyAccountBalance(
			checkingAccount.name,
			checkingAccount.heroDisplay,
		);
		accountPage.verifyAccountBalance(
			creditAccount.name,
			creditAccount.heroDisplay,
		);
		verifyModalBalance(checkingAccount);
		verifyModalBalance(creditAccount);
	});
});
