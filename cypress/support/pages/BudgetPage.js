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

class BudgetPage {
	elements = {
		readyToAssignValue: () => getLegacyBody().find("#budgets-ready-value"),
		activityValue: () => getLegacyBody().find("#budgets-activity-value"),
		availableValue: () => getLegacyBody().find("#budgets-available-value"),
		budgetsBody: () => getLegacyBody().find("#budgets-body"),

		reorderButton: () => getLegacyBody().find("[data-budgets-reorder]"),
		reorderSaveButton: () => getLegacyBody().find("[data-budgets-reorder-save]"),
		reorderCancelButton: () =>
			getLegacyBody().find("[data-budgets-reorder-cancel]"),
		groupDragHandles: () => getLegacyBody().find(".group-row__drag-handle"),

		createGroupButton: () => getLegacyBody().find("[data-open-group-modal]"),
		groupNameInput: () => getLegacyBody().find("[data-testid='group-name-input']"),
		saveGroupButton: () => getLegacyBody().find("[data-testid='save-group-btn']"),

		categoryGroupSelect: () =>
			getLegacyBody().find("[data-testid='category-group-select']"),
		saveCategoryButton: () =>
			getLegacyBody().find("[data-testid='save-category-btn']"),

		addBudgetButton: () => getLegacyBody().find("[data-open-category-modal]"),
		categoryNameInput: () =>
			getLegacyBody().find("[data-testid='category-name-input']"),
		goalTypeRecurringRadio: () =>
			getLegacyBody().find("[data-testid='goal-type-recurring']"),
		goalTypeTargetDateRadio: () =>
			getLegacyBody().find("[data-testid='goal-type-target-date']"),
		targetDateInput: () => getLegacyBody().find("[data-testid='target-date-input']"),
		targetAmountInput: () =>
			getLegacyBody().find("[data-testid='target-amount-input']"),
		frequencySelect: () => getLegacyBody().find("[data-testid='frequency-select']"),
		recurringDateInput: () =>
			getLegacyBody().find("[data-testid='recurring-date-input']"),
		recurringAmountInput: () =>
			getLegacyBody().find("[data-testid='recurring-amount-input']"),

		budgetDetailModal: () => getLegacyBody().find("#budget-detail-modal"),
		budgetDetailQuickActions: () => getLegacyBody().find("[data-quick-actions]"),
		groupDetailModal: () => getLegacyBody().find("#group-detail-modal"),
		groupDetailQuickActions: () =>
			getLegacyBody().find("[data-group-quick-actions]"),
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
		return getLegacyBody().contains(
			'[data-testid="budget-category-row"]',
			name,
			{
				timeout: 10000,
			},
		);
	}

	groupRow(name) {
		return getLegacyBody().contains('[data-testid="budget-group-row"]', name, {
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
		getLegacyBody()
			.find('[data-testid="budget-group-row"]')
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
		this.categoryRow(categoryName).scrollIntoView().click();
		getLegacyBody().find("#budget-detail-modal").should("be.visible");
		this.clickBudgetDetailEditButton();
		getLegacyBody().find("#category-modal.is-visible").should("exist");
		const groupSelect = this.elements.categoryGroupSelect();
		groupSelect.should("contain", groupName).select(groupName);
		this.elements.saveCategoryButton().click();
		getLegacyBody()
			.find("#category-modal")
			.should("have.attr", "aria-hidden", "true");
	}

	verifyGroupContainsCategories(groupName, categories) {
		categories.forEach((category) => {
			getLegacyBody()
				.contains('[data-testid="budget-category-row"]', category)
				.should("be.visible");
		});
	}

	verifyCategoryNotInUncategorized(categoryName) {
		this.groupRow("Uncategorized").within(() => {
			cy.contains('[data-testid="budget-category-row"]', categoryName).should(
				"not.exist",
			);
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
		getLegacyBody()
			.find("#budget-detail-modal button[data-detail-edit]", { timeout: 10000 })
			.should("be.visible")
			.and("be.enabled")
			.click();
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
		getLegacyBody().find("#toast-stack").should("contain", message);
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
