class BudgetPage {
	elements = {
		readyToAssignValue: () => cy.get("#budgets-ready-value"),
		activityValue: () => cy.get("#budgets-activity-value"),
		availableValue: () => cy.get("#budgets-available-value"),
		budgetsBody: () => cy.get("#budgets-body"),

		reorderButton: () => cy.get("[data-budgets-reorder]"),
		reorderSaveButton: () => cy.get("[data-budgets-reorder-save]"),
		reorderCancelButton: () =>
			cy.get("[data-budgets-reorder-cancel]"),
		groupDragHandles: () => cy.get(".group-row__drag-handle"),

		createGroupButton: () => cy.get("[data-testid='create-group-btn']"),
		groupNameInput: () => cy.get("[data-testid='group-name-input']"),
		saveGroupButton: () => cy.get("[data-testid='save-group-btn']"),

		categoryGroupSelect: () =>
			cy.get("[data-testid='category-group-select']"),
		saveCategoryButton: () =>
			cy.get("[data-testid='save-category-btn']"),

		addBudgetButton: () => cy.get("[data-testid='add-budget-button']"),
		categoryNameInput: () =>
			cy.get("[data-testid='category-name-input']"),
		goalTypeRecurringRadio: () =>
			cy.get("[data-testid='goal-type-recurring']"),
		goalTypeTargetDateRadio: () =>
			cy.get("[data-testid='goal-type-target-date']"),
		targetDateInput: () => cy.get("[data-testid='target-date-input']"),
		targetAmountInput: () =>
			cy.get("[data-testid='target-amount-input']"),
		frequencySelect: () => cy.get("[data-testid='frequency-select']"),
		recurringDateInput: () =>
			cy.get("[data-testid='recurring-date-input']"),
		recurringAmountInput: () =>
			cy.get("[data-testid='recurring-amount-input']"),

		budgetDetailModal: () => cy.get("#budget-detail-modal"),
		budgetDetailQuickActions: () =>
			cy.get("#budget-detail-modal .quick-allocations__actions"),
		groupDetailModal: () => cy.get("#group-detail-modal"),
		groupDetailQuickActions: () =>
			cy.get("#group-detail-modal .quick-allocations__actions"),
	};

	visit() {
		cy.visit("/#/budgets");
	}

	rememberReadyToAssign() {
		this.elements
			.readyToAssignValue()
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
		return cy.contains(
			'[data-testid="budget-category-row"]',
			name,
			{
				timeout: 10000,
			},
		);
	}

	groupRow(name) {
		return cy.contains('[data-testid="budget-group-row"]', name, {
			timeout: 10000,
		});
	}

	enterReorderMode() {
		this.elements.reorderButton().click();
		this.elements.reorderButton().should("be.disabled");
		this.elements.reorderSaveButton().should("be.enabled");
		this.elements.reorderCancelButton().should("be.enabled");
		this.elements.groupDragHandles().should("exist");
	}

	dragGroup(sourceName, targetName) {
		cy.window().then((win) => {
			const dataTransfer = new win.DataTransfer();
			this.groupRow(sourceName)
				.trigger("dragstart", { dataTransfer, force: true })
				.trigger("drag", { dataTransfer, force: true });
			this.groupRow(targetName)
				.trigger("dragover", { dataTransfer, force: true })
				.trigger("drop", { dataTransfer, force: true });
			this.groupRow(sourceName).trigger("dragend", { force: true });
		});
	}

	saveReorder() {
		this.elements.reorderSaveButton().click();
	}

	cancelReorder() {
		this.elements.reorderCancelButton().click();
	}

	assertGroupOrder(names) {
		const expectedIds = names.map((name) => this.getGroupIdFromName(name));
		const ignoredIds = new Set(["credit_card_payments", "uncategorized"]);
		cy.get('[data-testid="budget-group-row"]')
			.should(($rows) => {
				const ids = Array.from($rows)
					.map((row) => row.dataset.groupId)
					.filter((id) => !ignoredIds.has(id));
				expect(ids.slice(0, expectedIds.length)).to.deep.equal(expectedIds);
			});
	}

	assertGroupContainsCategories(groupName, categories) {
		this.groupRow(groupName)
			.nextUntil('[data-testid="budget-group-row"]')
			.should("exist")
			.then(($rows) => {
				const labels = Array.from($rows).map((row) =>
					row
						.querySelector('[data-testid="budget-col-name"]')
						?.innerText.trim(),
				);
				categories.forEach((category) => {
					expect(labels).to.include(category);
				});
			});
	}

	verifyCategoryAmount(label, amount) {
		this.categoryRow(label)
			.find('[data-testid="budget-col-budgeted"]')
			.should("contain", amount);
	}

	verifyAvailableAmount(label, amount) {
		this.categoryRow(label)
			.find('[data-testid="budget-col-available"]')
			.should("contain", amount);
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
		this.categoryRow(categoryName).scrollIntoView().click({ force: true });
		cy.get("#budget-detail-modal").should("be.visible");
		this.clickBudgetDetailEditButton();
		cy.get("#category-modal.is-visible").should("exist");
		const groupSelect = this.elements.categoryGroupSelect();
		groupSelect.should("contain", groupName).select(groupName);
		this.elements.saveCategoryButton().click();
		cy.get("#category-modal").should("not.exist");
	}

	verifyGroupContainsCategories(groupName, categories) {
		categories.forEach((category) => {
			cy.contains('[data-testid="budget-category-row"]', category)
				.should("be.visible");
		});
	}

	verifyCategoryNotInUncategorized(categoryName) {
		cy.get("body").then(($body) => {
			const hasUncategorized =
				$body.find('[data-testid="budget-group-row"]:contains("Uncategorized")')
					.length > 0;
			if (hasUncategorized) {
				this.groupRow("Uncategorized").within(() => {
					cy.contains(
						'[data-testid="budget-category-row"]',
						categoryName,
					).should("not.exist");
				});
			}
		});
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

	createRecurringBudget(
		name,
		groupName,
		frequency,
		recurringDate,
		recurringAmount,
	) {
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

	clickBudgetDetailEditButton() {
		cy.get("#budget-detail-modal")
			.contains("button", "Edit settings")
			.scrollIntoView()
			.should("be.visible")
			.and("be.enabled")
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
		this.categoryRow(name)
			.find('[data-testid="budget-col-budgeted"]')
			.should("contain", amount);
	}

	verifyToast(message) {
		cy.get("#toast-stack").should("contain", message);
	}

	getGroupIdFromName(groupName) {
		return (
			groupName
				.toLowerCase()
				.replace(/[^a-z0-9]+/g, "_")
				.replace(/^_+|_+$/g, "") || "uncategorized"
		);
	}
}

export default new BudgetPage();
