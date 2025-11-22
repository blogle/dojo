class BudgetPage {
    elements = {
        readyToAssignValue: () => cy.get("#budgets-ready-value"),
        activityValue: () => cy.get("#budgets-activity-value"),
        availableValue: () => cy.get("#budgets-available-value"),
        budgetsBody: () => cy.get("#budgets-body")
    };

    visit() {
        cy.visit("/#/budgets");
    }

    rememberReadyToAssign() {
        this.elements.readyToAssignValue()
            .invoke("text")
            .then((text) => cy.wrap(text.trim()).as("initialReady"));
    }

    expectReadyToAssignUnchanged() {
        cy.get("@initialReady").then((expected) => {
            this.elements.readyToAssignValue().should(($value) => {
                expect($value.text().trim()).to.eq(expected);
            });
        });
    }

    verifyReadyToAssign(value) {
        this.elements.readyToAssignValue().should("contain", value);
    }

    verifyActivity(value) {
        this.elements.activityValue().should("contain", value);
    }

    verifyAvailable(value) {
        this.elements.availableValue().should("contain", value);
    }

    verifyCategoryAmount(label, amount) {
        this.elements.budgetsBody().contains("tr", label).should("contain", amount);
    }

    verifyCategoryDoesNotExist(label) {
        this.elements.budgetsBody().contains("tr", label).should("not.exist");
    }
}

export default new BudgetPage();
