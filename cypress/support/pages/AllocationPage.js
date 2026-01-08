class AllocationPage {
	elements = {
		allocationForm: () => cy.get("[data-testid='allocation-form']"),
		categorySelect: () => cy.get("[data-allocation-to]"),
		fromCategorySelect: () => cy.get("[data-allocation-from]"),
		dateInput: () => cy.get("[data-allocation-date]"),
		amountInput: () => cy.get("input[name='amount']"),
		memoInput: () => cy.get("input[name='memo']"),
		submitButton: () => cy.get("[data-allocation-submit]"),
		errorDisplay: () => cy.get("[data-testid='allocation-error']"),
		tableRows: () => cy.get("#allocations-body tr"),
		readyToAssignValue: () => cy.get("#budgets-ready-value"),
		monthInflowValue: () => cy.get("#budgets-activity-value"),
	};

	visit() {
		cy.visit("/#/budgets");
	}

	verifyMonthInflow(value) {
		this.elements.monthInflowValue().should("contain", value);
	}

	getReadyToAssign() {
		return this.elements
			.readyToAssignValue()
			.invoke("text")
			.then((text) => {
				const numeric = Number.parseFloat(text.replace(/[^0-9.-]/g, ""));
				return Math.trunc(numeric);
			});
	}

	verifyReadyToAssign(value) {
		this.elements.readyToAssignValue().should("contain", value);
	}

	categoryTransfer(fromCategory, toCategory, amountDollars, memo) {
		cy.get("[data-testid='open-allocation-modal']").click();
		this.elements.allocationForm().should("be.visible");
		this.elements.fromCategorySelect().select(fromCategory);
		this.elements.categorySelect().select(toCategory);
		const memoField = this.elements.memoInput();
		memoField.clear();
		if (memo) {
			memoField.type(memo);
		}
		this.elements.amountInput().clear().type(amountDollars);
		this.elements.submitButton().click();
	}

	recordAllocation(categoryLabel, amountDollars) {
		cy.get("[data-testid='open-allocation-modal']").click();
		this.elements.allocationForm().should("be.visible");
		this.elements.categorySelect().select(categoryLabel);
		this.elements.amountInput().clear().type(amountDollars);
		this.elements.submitButton().click();
	}

	verifyError(errorMessage) {
		this.elements.errorDisplay().should("have.text", errorMessage);
	}

	verifyFormError(errorMessage) {
		this.verifyError(errorMessage);
	}

	createAllocation(date, amount, from, to, memo) {
		cy.get("[data-testid='open-allocation-modal']").click();
		this.elements.allocationForm().should("be.visible");
		this.elements.dateInput().type(date);
		if (from) {
			this.elements.fromCategorySelect().select(from);
		} else {
			this.elements.fromCategorySelect().select(""); // Ready to Assign
		}
		this.elements.categorySelect().select(to);
		this.elements.amountInput().clear().type(amount);
		if (memo) {
			this.elements.memoInput().clear().type(memo);
		}
		this.elements.submitButton().click();
	}

	verifyAllocationRow(index, date, amount, from, to, memo) {
		this.elements
			.tableRows()
			.eq(index)
			.within(() => {
				cy.contains("td", date);
				cy.contains("td.amount-cell", amount);
				if (from) cy.contains("td", from);
				if (to) cy.contains("td", to);
				if (memo) cy.contains("td", memo);
			});
	}

	editAllocation(index) {
		this.elements.tableRows().eq(index).click();
	}

	setInlineAmount(amount) {
		cy.get("tr.is-editing .amount-cell input").clear().type(amount);
	}

	setInlineToCategory(category) {
		cy.get("tr.is-editing select").select(category);
	}

	setInlineMemo(memo) {
		cy.get("tr.is-editing input[type='text']").clear().type(memo);
	}

	saveInlineEdit() {
		cy.get("tr.is-editing input[type='text']").type("{enter}");
	}
}

export default new AllocationPage();
