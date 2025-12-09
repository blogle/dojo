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
