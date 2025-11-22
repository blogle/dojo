class TransferPage {
    elements = {
        sourceSelect: () => cy.get("[data-transfer-source]"),
        destinationSelect: () => cy.get("[data-transfer-destination]"),
        categorySelect: () => cy.get("[data-transfer-category]"),
        amountInput: () => cy.get("#transfer-form input[name='amount']"),
        submitButton: () => cy.get("[data-transfer-submit]"),
        errorDisplay: () => cy.get("[data-testid='transfer-error']")
    };

    visit() {
        cy.visit("/#/transfers");
    }

    createTransfer(source, destination, category, amount) {
        this.elements.sourceSelect().select(source);
        this.elements.destinationSelect().select(destination);
        this.elements.categorySelect().select(category);
        this.elements.amountInput().clear().type(amount);
        this.elements.submitButton().click();
    }

    verifyError(errorMessage) {
        this.elements.errorDisplay().should("have.text", errorMessage);
    }
}

export default new TransferPage();
