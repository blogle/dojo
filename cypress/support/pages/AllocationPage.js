const getLegacyBody = () => {
	return cy.get("body").then(($body) => {
		if ($body.find('iframe[title="Dojo legacy app"]').length) {
			return cy
				.get('iframe[title="Dojo legacy app"]')
				.its("0.contentDocument.body")
				.should("not.be.empty")
				.then(cy.wrap);
		}
		return cy.get("body");
	});
};

class AllocationPage {
	elements = {
		allocationForm: () => getLegacyBody().find("[data-testid='allocation-form']"),
		categorySelect: () => getLegacyBody().find("[data-allocation-to]"),
		fromCategorySelect: () => getLegacyBody().find("[data-allocation-from]"),
		amountInput: () => getLegacyBody().find("input[name='amount']"),
		memoInput: () => getLegacyBody().find("input[name='memo']"),
		submitButton: () => getLegacyBody().find("[data-allocation-submit]"),
		errorDisplay: () => getLegacyBody().find("[data-testid='allocation-error']"),
	};

	visit() {
		cy.visit("/#/allocations");
	}

	categoryTransfer(fromCategory, toCategory, amountDollars, memo) {
		this.elements.allocationForm().within(() => {
			// Note: .within() scopes subsequent commands to the subject.
			// However, `this.elements.fromCategorySelect()` calls `getLegacyBody()` which starts a NEW chain from `cy.get('body')` or `cy.get('iframe')`.
			// This breaks the .within() scoping if used incorrectly.
			// BUT: `fromCategorySelect` returns a chainable that resolves to the element.
			// If we use it inside .within(), Cypress might complain if we chain off `cy` root.
			// Actually, `getLegacyBody` uses `cy.get`.
			// To be safe, we should avoid `this.elements` inside `.within()` if they restart the chain.
			// Or just don't use `.within()`.

			// Correcting logic: remove .within() and use elements directly.
		});
		
		// Refactoring methods to not use .within() to avoid chain-breaking issues with getLegacyBody helper.
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
		this.elements.categorySelect().select(categoryLabel);
		this.elements.amountInput().clear().type(amountDollars);
		this.elements.submitButton().click();
	}

	verifyError(errorMessage) {
		this.elements.errorDisplay().should("have.text", errorMessage);
	}
}

export default new AllocationPage();
