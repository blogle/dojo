/// <reference types="cypress" />

const STORAGE_KEY = "dojo-aspire-onboarding-v1";
const SHOT_KEYS = [
	"step-01",
	"step-02",
	"step-03",
	"step-04",
	"step-05",
	"step-06",
	"step-07",
	"step-07-action-bar",
	"step-08",
	"step-09",
	"step-09-account-modal",
	"step-10",
	"step-11",
];

const waitForShotReady = (shotKey) => {
	if (shotKey === "step-01") {
		cy.contains("h2", "Welcome to Dojo");
		return;
	}
	if (shotKey === "step-02") {
		cy.contains("h2", "Connect Google Drive");
		return;
	}
	if (shotKey === "step-03") {
		cy.contains("h2", "Which sheet are we using?");
		return;
	}
	if (shotKey === "step-04") {
		cy.contains("h2", "We found your data");
		return;
	}
	if (shotKey === "step-05") {
		cy.contains("h2", "Budget Accounts");
		return;
	}
	if (shotKey === "step-06") {
		cy.contains("h2", "Budget categories");
		return;
	}
	if (shotKey === "step-07") {
		cy.contains("h2", "Transfer Exceptions");
		return;
	}
	if (shotKey === "step-07-action-bar") {
		cy.contains("Transactions Selected");
		return;
	}
	if (shotKey === "step-08") {
		cy.contains("h2", "Link Overlapping Accounts");
		return;
	}
	if (shotKey === "step-09") {
		cy.contains("h2", "Net Worth Accounts");
		return;
	}
	if (shotKey === "step-09-account-modal") {
		cy.contains("h3", "Select Account Type");
		return;
	}
	if (shotKey === "step-10") {
		cy.contains("h2", "Preview Migration");
		return;
	}
	if (shotKey === "step-11") {
		cy.contains("h2", "Migration Complete");
	}
};

const parityState = {
	verifyResult: {
		looks_like_aspire: true,
		named_range_count: 42,
		missing_named_ranges: [],
	},
	extractionSummary: {
		transactions_count: 4200,
		net_worth_marks_count: 62,
		transactions_date_min: "2018-01-01",
		transactions_date_max: "2025-01-01",
	},
	mappingData: {
		mapping: {
			accounts: {
				"Chase Sapphire": {
					dojo_name: "Chase Sapphire",
					display_type: "Credit Card",
					account_class: "credit",
					is_active: true,
					current_balance_minor: -125000,
					pending_balance_minor: -14520,
				},
				"Wells Fargo Checking": {
					dojo_name: "Wells Fargo Checking",
					display_type: "Checking",
					account_class: "cash",
					is_active: true,
					current_balance_minor: 452050,
					pending_balance_minor: 0,
				},
				"Vanguard Brokerage": {
					dojo_name: "Vanguard Brokerage",
					display_type: "Investment",
					account_class: "investment",
					is_active: true,
					current_balance_minor: 0,
					pending_balance_minor: 0,
				},
				"My Mortgage": {
					dojo_name: "My Mortgage",
					display_type: "Loan",
					account_class: "loan",
					is_active: true,
					current_balance_minor: -24500000,
					pending_balance_minor: 0,
				},
				"Old Savings": {
					dojo_name: "Old Savings",
					display_type: "Savings",
					account_class: "cash",
					is_active: false,
					current_balance_minor: 0,
					pending_balance_minor: 0,
				},
			},
			categories: {
				Groceries: {
					dojo_name: "Groceries",
					group_name: "Living",
					is_active: true,
					config_label: "Recurring (Monthly)",
					configured_budget_minor: 60000,
					budgeted_minor: 60000,
					activity_minor: -14980,
					available_minor: 45020,
				},
				Rent: {
					dojo_name: "Rent",
					group_name: "Fixed",
					is_active: true,
					config_label: "Recurring (Monthly)",
					configured_budget_minor: 180000,
					budgeted_minor: 180000,
					activity_minor: 0,
					available_minor: 180000,
				},
				"Dining Out": {
					dojo_name: "Dining Out",
					group_name: "Fun",
					is_active: true,
					config_label: "Recurring (Monthly)",
					configured_budget_minor: 20000,
					budgeted_minor: 20000,
					activity_minor: -7950,
					available_minor: 12050,
				},
				"Old Car Repair": {
					dojo_name: "Old Car Repair",
					group_name: "Hidden",
					is_active: false,
					config_label: "None",
					configured_budget_minor: 7500,
					budgeted_minor: 0,
					activity_minor: 0,
					available_minor: 2500,
				},
			},
		},
	},
	transfersData: {
		auto_pairs: [[1, 2]],
		exceptions: [
			{
				row_index: 11,
				transaction_date: "2025-10-12",
				amount_minor: -50000,
				category_name: "Uncategorized",
				account_name: "Checking",
				memo: "Transfer to unknown",
			},
			{
				row_index: 12,
				transaction_date: "2025-10-12",
				amount_minor: 50000,
				category_name: "Uncategorized",
				account_name: "Savings",
				memo: "Deposit from Checking",
			},
			{
				row_index: 13,
				transaction_date: "2025-11-01",
				amount_minor: -2000,
				category_name: "Emergency Fund",
				account_name: "Checking",
				memo: "Monthly contribution",
			},
		],
		saved_resolutions: {
			13: {
				kind: "opening_balance",
				linked_row_index: null,
			},
		},
	},
	decisionsData: {
		decisions: {
			Checking: {
				decision: "duplicate_derive_from_ledger",
				ledger_account_id: "Checking",
				reason: "Name match",
				strategy_label: "Merge (recommended)",
			},
			Brokerage: {
				decision: "track_forward",
				destinations: [
					{
						name: "Vanguard Brokerage",
						account_class: "investment",
						account_type: "asset",
						starting_value_minor: 2500000,
						statement_cash_minor: 100000,
						holdings: [
							{ ticker: "VTI", quantity: 20, avg_cost_minor: 120000 },
							{ ticker: "BND", quantity: 10, avg_cost_minor: 80000 },
						],
					},
				],
			},
		},
	},
	previewResult: {
		legacy_net_worth_bucket: [
			{ date: "2024-09-01", value_minor: 10000000 },
			{ date: "2024-10-01", value_minor: 12000000 },
			{ date: "2024-11-01", value_minor: 8000000 },
			{ date: "2024-12-01", value_minor: 11000000 },
			{ date: "2025-01-01", value_minor: 9000000 },
		],
		dojo_net_worth_month_end: [
			{ date: "2024-09-01", value_minor: 10000000 },
			{ date: "2024-10-01", value_minor: 12500000 },
			{ date: "2024-11-01", value_minor: 7500000 },
			{ date: "2024-12-01", value_minor: 11500000 },
			{ date: "2025-01-01", value_minor: 8500000 },
		],
		budget_parity: {
			month_start: "2025-01-01",
			mismatches: 2,
			max_abs_diff_minor: 500,
			rows: [],
		},
		blockers: ["Transfer exceptions unresolved"],
	},
	applyResult: {
		import_status: "completed",
		accounts_created: 4,
		categories_created: 9,
		transactions_imported: 312,
	},
};

const onboardingStatusForStep = (step) => {
	if (step === 1) {
		return {
			onboarding_mode: null,
			onboarding_status: "not_started",
			migration_session_id: null,
			should_onboard: true,
		};
	}
	return {
		onboarding_mode: "aspire",
		onboarding_status: "in_progress",
		migration_session_id: "parity-session",
		should_onboard: true,
	};
};

const draftForStep = (step, shotKey) => {
	const draft = {
		currentStep: step,
		spreadsheet: "https://docs.google.com/spreadsheets/d/mockup-sheet",
		verifyResult: parityState.verifyResult,
		extractionSummary: parityState.extractionSummary,
		mappingData: parityState.mappingData,
		transfersData: parityState.transfersData,
		decisionsData: parityState.decisionsData,
		previewResult: parityState.previewResult,
		applyResult: step === 11 ? parityState.applyResult : null,
		transferDraft:
			shotKey === "step-07-action-bar"
				? {}
				: {
						13: {
							kind: "opening_balance",
							linked_row_index: null,
						},
					},
		transferPendingKind: {
			11: "opening_balance",
			12: "balance_adjustment",
			13: "opening_balance",
		},
		transferSelection:
			shotKey === "step-07-action-bar"
				? {
						11: true,
						12: true,
					}
				: {},
	};

	return draft;
};

const parityDescribe = Cypress.env("ONBOARDING_PARITY")
	? describe
	: describe.skip;

parityDescribe("Aspire onboarding visual parity capture", () => {
	beforeEach(() => {
		cy.viewport(1440, 1024);
		cy.intercept("GET", "/api/onboarding/google-oauth/status", {
			connected: true,
			expires_at_s: null,
		});
		cy.intercept(
			"GET",
			"/api/onboarding/aspire/mapping",
			parityState.mappingData,
		);
		cy.intercept(
			"GET",
			"/api/onboarding/aspire/transfers",
			parityState.transfersData,
		);
		cy.intercept(
			"GET",
			"/api/onboarding/aspire/net-worth",
			parityState.decisionsData,
		);
		cy.intercept(
			"GET",
			"/api/onboarding/aspire/preview",
			parityState.previewResult,
		);
	});

	SHOT_KEYS.forEach((shotKey) => {
		const step =
			shotKey === "step-07-action-bar"
				? 7
				: shotKey === "step-09-account-modal"
					? 9
					: Number(shotKey.split("-")[1]);

		it(`captures ${shotKey}`, () => {
			const onboardingStatus = onboardingStatusForStep(step);
			cy.intercept("GET", "/api/onboarding/status", onboardingStatus);

			cy.visit("/#/onboarding", {
				onBeforeLoad(win) {
					win.localStorage.setItem(
						STORAGE_KEY,
						JSON.stringify(draftForStep(step, shotKey)),
					);
				},
			});

			if (shotKey === "step-09-account-modal") {
				cy.contains("button", "+ Add Destination Account").first().click({
					force: true,
				});
			}

			waitForShotReady(shotKey);
			cy.wait(200);
			cy.screenshot(shotKey, { capture: "viewport", overwrite: true });
		});
	});
});
