const STORAGE_KEY = "dojo-aspire-onboarding-v1";
const FIXTURE = "tests/fixtures/base_budgeting.sql";

const interceptOnboardingShell = () => {
	cy.intercept("GET", "/api/onboarding/status", {
		onboarding_mode: "aspire",
		onboarding_status: "in_progress",
		migration_session_id: "sess-validation",
		should_onboard: true,
		aspire_migration_allow_partial_mapping: false,
	});
	cy.intercept("GET", "/api/onboarding/google-oauth/status", {
		connected: true,
		expires_at_s: null,
	});
};

describe("Aspire onboarding stepper validation", () => {
	beforeEach(() => {
		cy.resetDatabase();
		cy.seedDatabase(FIXTURE);
		interceptOnboardingShell();
	});

	it("keeps step 7 blocked until transfer exceptions are resolved", () => {
		cy.visit("/#/onboarding", {
			onBeforeLoad(win) {
				win.localStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						currentStep: 7,
						transfersData: {
							auto_pairs: [],
							exceptions: [
								{
									row_index: 11,
									transaction_date: "2025-01-10",
									account_name: "Checking",
									category_name: "Transfer",
									amount_minor: -10000,
									memo: "Transfer out",
								},
							],
							saved_resolutions: {},
						},
					}),
				);
			},
		});

		cy.contains("Step 7 of 11").should("be.visible");
		cy.contains("button", "Continue").click({ force: true });
		cy.contains(
			"Resolve every transfer exception before continuing. Use Link as Transfer or a system resolution.",
		).should("be.visible");
		cy.contains("Step 7 of 11").should("be.visible");
	});

	it("shows a footer validation error when step 9 modal is open", () => {
		cy.visit("/#/onboarding", {
			onBeforeLoad(win) {
				win.localStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						currentStep: 9,
						destinationModalName: "Retirement",
						decisionsData: {
							decisions: {
								Retirement: {
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
		cy.contains("button", "Continue").click({ force: true });
		cy.contains("Close destination setup before continuing.").should(
			"be.visible",
		);
		cy.contains("Step 9 of 11").should("be.visible");
	});
});
