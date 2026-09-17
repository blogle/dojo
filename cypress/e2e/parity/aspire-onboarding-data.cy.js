const STORAGE_KEY = "dojo-aspire-onboarding-v1";
const FIXTURE = "tests/fixtures/base_budgeting.sql";

const interceptOnboardingShell = () => {
	cy.intercept("GET", "/api/onboarding/status", {
		onboarding_mode: "aspire",
		onboarding_status: "in_progress",
		migration_session_id: "sess-data",
		should_onboard: true,
		aspire_migration_allow_partial_mapping: false,
	});
	cy.intercept("GET", "/api/onboarding/google-oauth/status", {
		connected: true,
		expires_at_s: null,
	});
};

describe("Aspire onboarding mapping data", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		interceptOnboardingShell();
	});

	it("refreshes mapping data to populate step 5 balances", () => {
		cy.intercept("GET", "/api/onboarding/aspire/mapping", {
			mapping_status: "completed",
			mapping: {
				accounts: {
					Checking: {
						dojo_name: "House Checking",
						account_class: "cash",
						account_role: "on_budget",
						is_active: true,
						display_type: "Cash",
						current_balance_minor: 12345,
						pending_balance_minor: -500,
					},
				},
				categories: {},
			},
			aspire_hidden_accounts: [],
			aspire_hidden_categories: [],
			aspire_special_labels: { v_Today: "2025-01-10" },
			aspire_status_symbols: {},
		});

		cy.visit("/#/onboarding", {
			onBeforeLoad(win) {
				win.localStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						currentStep: 5,
						mappingData: {
							mapping_status: "completed",
							mapping: {
								accounts: {
									Checking: {
										dojo_name: "House Checking",
										account_class: "cash",
										account_role: "on_budget",
										is_active: true,
									},
								},
								categories: {},
							},
							aspire_special_labels: { v_Today: "2025-01-10" },
						},
					}),
				);
			},
		});

		cy.contains("Step 5 of 11").should("be.visible");
		cy.contains("House Checking").should("be.visible");
		cy.contains("$123.45").should("be.visible");
		cy.contains("-$5.00").should("be.visible");
	});

	it("renders step 6 configured budget and supports category editing", () => {
		cy.intercept("GET", "/api/onboarding/aspire/mapping", {
			mapping_status: "completed",
			mapping: {
				accounts: {},
				categories: {
					Groceries: {
						dojo_name: "Groceries",
						group_name: "Living",
						is_active: true,
						goal_type: "target_date",
						goal_amount_minor: 120000,
						goal_target_date: "2026-01-01",
						goal_frequency: null,
						configured_budget_minor: 9231,
						available_minor: 0,
						budgeted_minor: 0,
						activity_minor: 0,
					},
				},
			},
			aspire_hidden_accounts: [],
			aspire_hidden_categories: [],
			aspire_special_labels: { v_Today: "2025-01-10" },
			aspire_status_symbols: {},
		});

		cy.visit("/#/onboarding", {
			onBeforeLoad(win) {
				win.localStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						currentStep: 6,
						mappingData: {
							mapping: {
								categories: {
									Groceries: {
										dojo_name: "Groceries",
										group_name: "Living",
										is_active: true,
									},
								},
							},
						},
					}),
				);
			},
		});

		cy.contains("Step 6 of 11").should("be.visible");
		cy.contains("Groceries").should("be.visible");
		// 120000 cents over 13 months (Jan 2025..Jan 2026) => $92.31
		cy.contains("$92.31").should("be.visible");

		cy.get("button.edit-icon").first().click();
		cy.contains("Edit category").should("be.visible");
		cy.contains("Recurring").click();
		cy.get("input[type='number']").clear().type("50");
		cy.contains("Save Changes").click();
		cy.contains("Recurring (monthly)").should("be.visible");
		cy.contains("$50.00").should("be.visible");
	});

	it("renders step 9 net worth cards with destination CTA", () => {
		cy.intercept("GET", "/api/onboarding/aspire/net-worth", {
			decisions: {
				Investments: {
					decision: "track_forward",
					classification: "asset",
					cutover_date: "2025-01-10",
					destinations: [],
				},
			},
			last_reported_by_category_minor: {
				Investments: 250000,
			},
		});

		cy.visit("/#/onboarding", {
			onBeforeLoad(win) {
				win.localStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						currentStep: 9,
						decisionsData: {
							decisions: {
								Investments: {
									decision: "track_forward",
									classification: "asset",
									destinations: [],
								},
							},
						},
					}),
				);
			},
		});

		cy.contains("Step 9 of 11").should("be.visible");
		cy.contains("Net Worth Accounts").should("be.visible");
		cy.contains("Investments").should("be.visible");
		cy.contains("+ Add Destination Account").should("be.visible");
	});
});
