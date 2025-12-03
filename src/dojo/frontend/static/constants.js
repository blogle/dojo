export const selectors = {
	monthSpend: "#month-spend",
	monthBudgeted: "#month-budgeted",
	transactionsBody: "#transactions-body",
	assetsTotal: "#assets-total",
	liabilitiesTotal: "#liabilities-total",
	netWorth: "#net-worth",
	readyToAssign: "#ready-to-assign",
	accountGroups: "#account-groups",
	addAccountButton: "[data-add-account-button]",
	accountModal: "#account-modal",
	accountModalLabel: "[data-modal-label]",
	accountModalTitle: "[data-modal-title]",
	accountModalSubtitle: "[data-modal-subtitle]",
	accountModalMetadata: "[data-modal-metadata]",
	accountModalBalance: "[data-modal-balance]",
	modalClose: "[data-close-modal]",
	accountSectionLink: "[data-account-section]",
	modalAddButton: "[data-add-account-submit]",
	modalTypeSelect: "[name=type]",
	modalNameInput: "[name=name]",
	modalBalanceInput: "[name=balance]",
	transactionForm: "#transaction-form",
	transactionSubmit: "[data-transaction-submit]",
	transactionError: "[data-testid='transaction-error']",
	transactionAccountSelect: "[data-transaction-account]",
	transactionCategorySelect: "[data-transaction-category]",
	transactionFlowInputs: "[data-transaction-flow]",
	transferForm: "#transfer-form",
	transferSubmit: "[data-transfer-submit]",
	transferError: "[data-testid='transfer-error']",
	transferSourceSelect: "[data-transfer-source]",
	transferDestinationSelect: "[data-transfer-destination]",
	transferCategorySelect: "[data-transfer-category]",
	allocationForm: "[data-testid='allocation-form']",
	allocationSubmit: "[data-allocation-submit]",
	allocationError: "[data-testid='allocation-error']",
	allocationFromSelect: "[data-allocation-from]",
	allocationToSelect: "[data-allocation-to]",
	allocationDateInput: "[data-allocation-date]",
	allocationsBody: "#allocations-body",
	allocationInflowValue: "#allocations-inflow-value",
	allocationReadyValue: "#allocations-ready-value",
	allocationMonthLabel: "#allocations-month-label",
	budgetsGrid: "[data-budgets-grid]",
	budgetsReadyValue: "#budgets-ready-value",
	budgetsActivityValue: "#budgets-activity-value",
	budgetsAvailableValue: "#budgets-available-value",
	budgetsMonthLabel: "#budgets-month-label",
	categoryModal: "#category-modal",
	categoryModalTitle: "[data-category-modal-title]",
	categoryModalHint: "[data-category-modal-hint]",
	categoryNameInput: "[data-category-name]",
	categorySlugInput: "[data-category-slug]",
	categoryError: "[data-category-error]",
	categoryForm: "[data-category-form]",
	categorySubmit: "[data-category-submit]",
	categoryModalClose: "[data-close-category-modal]",
	categoryGroupSelect: "[data-category-group]",
	groupModal: "#group-modal",
	groupModalTitle: "[data-group-modal-title]",
	groupForm: "[data-group-form]",
	groupSubmit: "[data-group-submit]",
	groupError: "[data-group-error]",
	groupModalClose: "[data-close-group-modal]",
	groupUncategorizedField: "[data-group-uncategorized-field]",
	groupUncategorizedSelect: "[data-group-uncategorized]",
	groupUncategorizedHelper: "[data-group-uncategorized-helper]",
	budgetDetailModal: "#budget-detail-modal",
	budgetDetailTitle: "[data-budget-detail-title]",
	budgetDetailClose: "[data-close-budget-detail-modal]",
	budgetDetailLeftover: "[data-detail-leftover]",
	budgetDetailBudgeted: "[data-detail-budgeted]",
	budgetDetailActivity: "[data-detail-activity]",
	budgetDetailAvailable: "[data-detail-available]",
	budgetDetailQuickActions: "[data-quick-actions]",
	budgetDetailEdit: "[data-detail-edit]",
	groupDetailModal: "#group-detail-modal",
	groupDetailTitle: "[data-group-detail-title]",
	groupDetailClose: "[data-close-group-detail-modal]",
	groupDetailLeftover: "[data-group-detail-leftover]",
	groupDetailBudgeted: "[data-group-detail-budgeted]",
	groupDetailActivity: "[data-group-detail-activity]",
	groupDetailAvailable: "[data-group-detail-available]",
	groupDetailQuickActions: "[data-group-quick-actions]",
	groupDetailEdit: "[data-group-detail-edit]",
	toastStack: "#toast-stack",
};

export const SPECIAL_CATEGORY_IDS = {
	openingBalance: "opening_balance",
	accountTransfer: "account_transfer",
	availableToBudget: "available_to_budget",
	balanceAdjustment: "balance_adjustment",
};

export const SPECIAL_CATEGORY_LABELS = {
	[SPECIAL_CATEGORY_IDS.openingBalance]: "Opening Balance",
	[SPECIAL_CATEGORY_IDS.accountTransfer]: "Account Transfer",
	[SPECIAL_CATEGORY_IDS.availableToBudget]: "Available to Budget",
	[SPECIAL_CATEGORY_IDS.balanceAdjustment]: "Balance Adjustment",
};

export const systemCategoryIds = new Set(Object.values(SPECIAL_CATEGORY_IDS));

export const accountGroupDefinitions = [
	{
		id: "cash",
		title: "Cash & Checking",
		type: "asset",
		description: "Everyday banking and liquid cash.",
	},
	{
		id: "accessible",
		title: "Accessible Assets",
		type: "asset",
		description: "Short-term deposits and cash equivalents.",
	},
	{
		id: "investment",
		title: "Investments",
		type: "asset",
		description: "Brokerage, retirement, and long-term holdings.",
	},
	{
		id: "credit",
		title: "Credit & Borrowing",
		type: "liability",
		description: "Credit cards, lines of credit, and short-duration loans.",
	},
	{
		id: "loan",
		title: "Loans & Mortgages",
		type: "liability",
		description: "Mortgages, auto loans, and other long-term debt.",
	},
	{
		id: "tangible",
		title: "Tangibles",
		type: "asset",
		description: "Appraised property, vehicles, and collectables.",
	},
];

export const accountTypeMapping = {
	checking: {
		account_type: "asset",
		account_class: "cash",
		account_role: "on_budget",
	},
	credit: {
		account_type: "liability",
		account_class: "credit",
		account_role: "on_budget",
	},
	brokerage: {
		account_type: "asset",
		account_class: "investment",
		account_role: "tracking",
	},
	loan: {
		account_type: "liability",
		account_class: "loan",
		account_role: "tracking",
	},
	asset: {
		account_type: "asset",
		account_class: "tangible",
		account_role: "tracking",
	},
};

export const statusToggleIcons = `
  <svg class="status-icon status-icon--check" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6 12.5 L10 16.5 L18 8" />
  </svg>
  <svg class="status-icon status-icon--pending" viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="6.5" />
  </svg>
`;
