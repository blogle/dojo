class BudgetPage {
    elements = {
        readyToAssignValue: () => cy.get("#budgets-ready-value"),
        activityValue: () => cy.get("#budgets-activity-value"),
        availableValue: () => cy.get("#budgets-available-value"),
        budgetsBody: () => cy.get("#budgets-body"),

        createGroupButton: () => cy.get("[data-open-group-modal]"),
        groupNameInput: () => cy.getBySel("group-name-input"),
        saveGroupButton: () => cy.getBySel("save-group-btn"),

        categoryGroupSelect: () => cy.getBySel("category-group-select"),
        saveCategoryButton: () => cy.getBySel("save-category-btn"),

        addBudgetButton: () => cy.get("[data-open-category-modal]"),
        categoryNameInput: () => cy.getBySel("category-name-input"),
        goalTypeRecurringRadio: () => cy.getBySel("goal-type-recurring"),
        goalTypeTargetDateRadio: () => cy.getBySel("goal-type-target-date"),
        targetDateInput: () => cy.getBySel("target-date-input"),
        targetAmountInput: () => cy.getBySel("target-amount-input"),
        frequencySelect: () => cy.getBySel("frequency-select"),
        recurringDateInput: () => cy.getBySel("recurring-date-input"),
        recurringAmountInput: () => cy.getBySel("recurring-amount-input"),

        budgetDetailModal: () => cy.get("#budget-detail-modal"),
        budgetDetailQuickActions: () => cy.get("[data-quick-actions]"),
        groupDetailModal: () => cy.get("#group-detail-modal"),
        groupDetailQuickActions: () => cy.get("[data-group-quick-actions]"),
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

    categoryRow(name) {
        return cy.contains('[data-testid="budget-category-row"]', name, { timeout: 10000 });
    }

    groupRow(name) {
        return cy.contains('[data-testid="budget-group-row"]', name, { timeout: 10000 });
    }

    verifyCategoryAmount(label, amount) {
        this.categoryRow(label).find("td.amount-cell").eq(0).should("contain", amount);
    }

    verifyAvailableAmount(label, amount) {
        this.categoryRow(label).find("td.amount-cell").eq(2).should("contain", amount);
    }

    verifyCategoryDoesNotExist(label) {
        this.elements.budgetsBody().contains("tr", label).should("not.exist");
    }

    createBudgetGroup(groupName) {
        this.elements.createGroupButton().click();
        this.elements.groupNameInput().clear().type(groupName);
        this.elements.saveGroupButton().click();
        this.groupRow(groupName).should("exist");
    }

    assignCategoryToGroup(categoryName, groupName) {
        this.categoryRow(categoryName)
            .scrollIntoView()
            .within(() => {
                cy.get('[data-testid="edit-category-btn"]').click();
            });
        const groupSelect = this.elements.categoryGroupSelect();
        groupSelect.should("contain", groupName).select(groupName);
        this.elements.saveCategoryButton().click();
        cy.get("#category-modal").should("have.attr", "aria-hidden", "true");
    }

    verifyGroupContainsCategories(groupName, categories) {
        this.groupRow(groupName)
            .should("have.attr", "data-group-id")
            .then((groupId) => {
                categories.forEach((category) => {
                    this.categoryRow(category)
                        .should("have.attr", "data-group-id")
                        .and("eq", groupId);
                });
            });
    }

    verifyCategoryNotInUncategorized(categoryName) {
        this.categoryRow(categoryName)
            .should("have.attr", "data-group-id")
            .and("not.eq", "uncategorized");
    }

    openAddBudgetModal() {
        this.elements.addBudgetButton().click();
    }

    createTargetDateBudget(name, groupName, targetDate, targetAmount) {
        this.elements.categoryNameInput().clear().type(name);
        if (groupName) {
            this.elements.categoryGroupSelect().select(groupName);
        }
        this.elements.goalTypeTargetDateRadio().check({ force: true });
        this.elements.targetDateInput().type(targetDate);
        this.elements.targetAmountInput().clear().type(targetAmount);
        this.elements.saveCategoryButton().click();
    }

    createRecurringBudget(name, groupName, frequency, recurringDate, recurringAmount) {
        this.elements.categoryNameInput().clear().type(name);
        if (groupName) {
            this.elements.categoryGroupSelect().select(groupName);
        }
        this.elements.goalTypeRecurringRadio().check({ force: true });
        this.elements.frequencySelect().select(frequency);
        this.elements.recurringDateInput().type(recurringDate);
        this.elements.recurringAmountInput().clear().type(recurringAmount);
        this.elements.saveCategoryButton().click();
    }

    openBudgetDetailModal(categoryName) {
        this.categoryRow(categoryName).scrollIntoView().click({ force: true });
        this.elements.budgetDetailModal().should("have.class", "is-visible");
    }

    clickQuickAllocateButton(buttonText) {
        this.elements
            .budgetDetailQuickActions()
            .contains("button", buttonText)
            .scrollIntoView()
            .click({ force: true });
    }

    openGroupDetailModal(groupName) {
        this.groupRow(groupName).scrollIntoView().click({ force: true });
        this.elements.groupDetailModal().should("have.class", "is-visible");
    }

    clickGroupQuickActionButton(buttonText) {
        this.elements
            .groupDetailQuickActions()
            .contains("button", buttonText)
            .scrollIntoView()
            .click({ force: true });
    }

    verifyBudgetedAmount(name, amount) {
        this.categoryRow(name).find("td.amount-cell").eq(0).should("contain", amount);
    }

    verifyToast(message) {
        cy.get("#toast-stack").should("contain", message);
    }

    getGroupIdFromName(groupName) {
        return groupName.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "uncategorized";
    }
}

export default new BudgetPage();
