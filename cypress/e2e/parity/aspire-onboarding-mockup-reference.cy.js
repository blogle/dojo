/// <reference types="cypress" />

const parityDescribe = Cypress.env("ONBOARDING_PARITY")
	? describe
	: describe.skip;

const MOCK_STORAGE_KEY = "dojo_aspire_onboarding_mockup_v3";
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

const mockBaseUrl = Cypress.env("MOCKUP_BASE_URL") || "http://127.0.0.1:8788";
const mockupUrl = `${mockBaseUrl}/aspire_onboarding_mockup.html`;

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
		cy.contains("h2", "Budget Categories");
		return;
	}
	if (shotKey === "step-07") {
		cy.contains("h2", "Transfer Exceptions");
		return;
	}
	if (shotKey === "step-07-action-bar") {
		cy.contains("2 Transactions Selected");
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

const baseTransferRows = [
	{
		id: 101,
		date: "2025-10-12",
		category: "Uncategorized",
		account: "Checking",
		amount: -500,
		memo: "Transfer to unknown",
		originalCategory: "Uncategorized",
		originalMemo: "Transfer to unknown",
		selected: false,
		resolved: false,
		editing: false,
		resolutionType: "",
		linkedGroupId: null,
	},
	{
		id: 102,
		date: "2025-10-12",
		category: "Uncategorized",
		account: "Savings",
		amount: 500,
		memo: "Deposit from Checking",
		originalCategory: "Uncategorized",
		originalMemo: "Deposit from Checking",
		selected: false,
		resolved: false,
		editing: false,
		resolutionType: "",
		linkedGroupId: null,
	},
	{
		id: 103,
		date: "2025-11-01",
		category: "Emergency Fund",
		account: "Checking",
		amount: -20,
		memo: "Monthly contribution",
		originalCategory: "Uncategorized",
		originalMemo: "Adjustment",
		selected: false,
		resolved: true,
		editing: false,
		resolutionType: "edited",
		linkedGroupId: null,
	},
];

const baseMappings = [
	{
		id: "m1",
		budgetAccount: "Checking",
		netWorthAccount: "Checking",
		reason: "Name match",
		strategy: "merge",
	},
];

const baseNetWorthCategories = [
	{
		id: "nw1",
		name: "Brokerage",
		lastBalance: 25000,
		destinations: [
			{
				id: "d1",
				name: "Vanguard Brokerage",
				type: "Investment",
				classKey: "investment",
				balance: 25000,
				positionsCount: 2,
			},
		],
	},
];

const mockStateForShot = (step, shotKey) => {
	const transferRows = JSON.parse(JSON.stringify(baseTransferRows));
	if (shotKey === "step-07-action-bar") {
		transferRows[0].selected = true;
		transferRows[1].selected = true;
	}

	return {
		currentStep: step,
		sheetUrl: "https://docs.google.com/spreadsheets/d/mockup-sheet",
		transferRows,
		mappings: JSON.parse(JSON.stringify(baseMappings)),
		nwCategories: JSON.parse(JSON.stringify(baseNetWorthCategories)),
	};
};

parityDescribe("Aspire mockup reference capture", () => {
	beforeEach(() => {
		cy.viewport(1440, 1024);
	});

	SHOT_KEYS.forEach((shotKey) => {
		const step =
			shotKey === "step-07-action-bar"
				? 7
				: shotKey === "step-09-account-modal"
					? 9
					: Number(shotKey.split("-")[1]);

		it(`captures ${shotKey}`, () => {
			cy.visit(mockupUrl, {
				onBeforeLoad(win) {
					win.localStorage.setItem(
						MOCK_STORAGE_KEY,
						JSON.stringify(mockStateForShot(step, shotKey)),
					);
				},
			});

			if (shotKey === "step-07-action-bar") {
				cy.get("input[type='checkbox']").eq(0).check({ force: true });
				cy.get("input[type='checkbox']").eq(1).check({ force: true });
			}

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
