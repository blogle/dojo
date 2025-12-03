class TransactionPage {
	elements = {
		accountSelect: () => cy.get("[data-transaction-account]"),
		categorySelect: () => cy.get("[data-transaction-category]"),
		inflowRadio: () => cy.get("[data-transaction-flow][value='inflow']"),
		outflowRadio: () => cy.get("[data-transaction-flow][value='outflow']"),
		amountInput: () => cy.get("#transaction-form input[name='amount']"),
		submitButton: () => cy.get("[data-transaction-submit]"),
		errorDisplay: () => cy.get("[data-testid='transaction-error']"),
		transactionTableRows: () => cy.get("#transactions-body tr"),
	};

	visit() {
		cy.visit("/#/transactions");
	}

	createOutflowTransaction(account, category, amount) {
		this.elements.outflowRadio().check({ force: true });
		this.elements.accountSelect().select(account);
		this.elements.categorySelect().select(category);
		this.elements.amountInput().clear().type(amount);
		this.elements.submitButton().click();
	}

	createTransaction(type, account, category, amount) {
		if (type === "inflow") {
			this.elements.inflowRadio().check({ force: true });
		} else if (type === "outflow") {
			this.createOutflowTransaction(account, category, amount);
			return;
		}

		this.elements.accountSelect().select(account);
		this.elements.categorySelect().select(category);
		this.elements.amountInput().clear().type(amount);
		this.elements.submitButton().click();
	}

	verifyError(errorMessage) {
		this.elements.errorDisplay().should("have.text", errorMessage);
	}

	verifyTransactionCount(count) {
		this.elements.transactionTableRows().should("have.length", count);
	}

	verifyTransactionRow(rowIndex, account, category, amount) {
		this.elements
			.transactionTableRows()
			.eq(rowIndex)
			.within(() => {
				cy.get('[data-testid="transaction-col-account"]').should(
					"contain",
					account,
				);
				cy.get('[data-testid="transaction-col-category"]').should(
					"contain",
					category,
				);
				// Amount can be in outflow or inflow, check both or just contain text
				cy.contains('[class*="amount-cell"]', amount).should("exist");
			});
	}

	editTransaction(rowIndex) {
		this.elements.transactionTableRows().eq(rowIndex).click();
	}

	setInlineDate(dateString) {
		cy.get("[data-inline-date]").clear().type(dateString);
	}

	selectInlineAccount(accountName) {
		cy.get("[data-inline-account]").select(accountName);
	}

	selectInlineCategory(categoryName) {
		cy.get("[data-inline-category]").select(categoryName);
	}

	setInlineMemo(memo) {
		cy.get("[data-inline-memo]").clear().type(memo);
	}

	setInlineOutflow(amount) {
		cy.get("tr.is-editing [data-inline-outflow]")
			.should("be.visible")
			.should("be.enabled")
			.type("{selectall}{backspace}" + amount);
	}

	editOutflowAmount(amount) {
		this.setInlineOutflow(amount);
	}

	toggleTransactionStatus() {
		cy.get("[data-inline-status-toggle]").click();
	}

	saveInlineEdit() {
		cy.get("[data-inline-outflow]")
			.should("be.enabled")
			.type("{enter}", { force: true });
	}

	verifyTransactionStatus(rowIndex, status) {
		this.elements
			.transactionTableRows()
			.eq(rowIndex)
			.within(() => {
				cy.get("[data-status-display]").should(
					"have.attr",
					"data-state",
					status,
				);
			});
	}

	verifyTransactionRowAmount(rowIndex, amount) {
		this.elements
			.transactionTableRows()
			.eq(rowIndex)
			.within(() => {
				cy.contains("td.amount-cell", amount).should("exist");
			});
	}

	verifyTransactionMemo(rowIndex, memo) {
		this.elements
			.transactionTableRows()
			.eq(rowIndex)
			.within(() => {
				cy.contains("td", memo).should("exist");
			});
	}

	verifyTransactionDate(rowIndex, dateString) {
		this.elements
			.transactionTableRows()
			.eq(rowIndex)
			.within(() => {
				cy.contains("td", dateString).should("exist");
			});
	}

	verifyTransactionRowByMemo(memoText, { amount, date, status } = {}) {
		cy.contains("#transactions-body tr", memoText).within(() => {
			if (date) {
				cy.contains("td", date).should("exist");
			}
			if (amount) {
				cy.contains("td.amount-cell", amount).should("exist");
			}
			if (status) {
				cy.get("[data-status-display]").should(
					"have.attr",
					"data-state",
					status,
				);
			}
		});
	}
}

export default new TransactionPage();
