class AllocationPage {
	elements = {
		allocationForm: () => cy.get("[data-testid='allocation-form']"),
		categorySelect: () => cy.get("[data-allocation-to]"),
		fromCategorySelect: () => cy.get("[data-allocation-from]"),
		amountInput: () => cy.get("input[name='amount']"),
		memoInput: () => cy.get("input[name='memo']"),
		submitButton: () => cy.get("[data-allocation-submit]"),
		errorDisplay: () => cy.get("[data-testid='allocation-error']"),
	};

	visit() {
		cy.visit("/#/allocations");
	}

	categoryTransfer(fromCategory, toCategory, amountDollars, memo) {
		this.elements.allocationForm().within(() => {
			this.elements.fromCategorySelect().select(fromCategory);
			this.elements.categorySelect().select(toCategory);
			const memoField = this.elements.memoInput();
			memoField.clear();
			if (memo) {
				memoField.type(memo);
			}
			this.elements.amountInput().clear().type(amountDollars);
		});
		this.elements.submitButton().click();
	}

	recordAllocation(categoryLabel, amountDollars) {
		this.elements.allocationForm().within(() => {
			this.elements.categorySelect().select(categoryLabel);
			this.elements.amountInput().clear().type(amountDollars);
		});
		this.elements.submitButton().click();
	}

	verifyError(errorMessage) {
		this.elements.errorDisplay().should("have.text", errorMessage);
	}
}

export default new AllocationPage();
