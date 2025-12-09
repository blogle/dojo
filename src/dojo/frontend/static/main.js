import {
	initAccounts,
	refreshAccountsPage,
	updateAccountStats,
} from "./components/accounts/index.js";
import {
	initAllocations,
	loadAllocationsData,
	renderAllocationsPage,
} from "./components/allocations/index.js";
import {
	initBudgets,
	loadBudgetsData,
	renderBudgetsPage,
} from "./components/budgets/index.js";
import { loadReferenceData } from "./components/reference/index.js";
import { initRouter } from "./components/router/index.js";
import {
	initTransactions,
	refreshTransactions,
	updateHeaderStats,
} from "./components/transactions/index.js";
import { initTransfers } from "./components/transfers/index.js";

const bootstrap = async () => {
	const params = new URLSearchParams(window.location.search);
	if (params.get("embed") === "true") {
		document.body.classList.add("is-embedded");
	}

	const testDate = localStorage.getItem("DOJO_TEST_DATE");
	if (testDate) {
		const fixed = new Date(testDate).getTime();
		const OriginalDate = Date;
		// eslint-disable-next-line no-global-assign
		window.Date = class extends OriginalDate {
			constructor(...args) {
				if (args.length === 0) {
					return new OriginalDate(fixed);
				}
				return new OriginalDate(...args);
			}
			static now() {
				return fixed;
			}
		};
	}

	initAccounts({
		onReferenceRefresh: loadReferenceData,
		onBudgetsRefresh: loadBudgetsData,
		onBudgetsRender: renderBudgetsPage,
		onTransactionsRefresh: refreshTransactions,
	});

	initBudgets({
		onAllocationsRefresh: loadAllocationsData,
		onAllocationsRender: renderAllocationsPage,
		onAccountsRefresh: refreshAccountsPage,
		onReferenceRefresh: loadReferenceData,
		onHeaderStats: updateHeaderStats,
	});

	initAllocations({
		onBudgetsRefresh: loadBudgetsData,
		onBudgetsRender: renderBudgetsPage,
		onAccountsRefresh: refreshAccountsPage,
	});

	initTransactions({
		onBudgetsRefresh: loadBudgetsData,
		onAccountsRefresh: refreshAccountsPage,
		onBudgetsRender: renderBudgetsPage,
	});

	initTransfers({
		onTransactionsRefresh: refreshTransactions,
		onAccountsRefresh: refreshAccountsPage,
		onBudgetsRefresh: loadBudgetsData,
		onBudgetsRender: renderBudgetsPage,
	});

	initRouter({
		onBudgetsRefresh: loadBudgetsData,
		onBudgetsRender: renderBudgetsPage,
		onAllocationsRefresh: loadAllocationsData,
		onAllocationsRender: renderAllocationsPage,
		onTransactionsRefresh: refreshTransactions,
	});

	await loadReferenceData();

	try {
		await refreshTransactions();
	} catch (error) {
		console.error(error);
		const transactionsBody = document.querySelector("#transactions-body");
		if (transactionsBody) {
			transactionsBody.innerHTML = `
        <tr>
          <td colspan="6" class="u-muted" style="text-align: center; color: var(--danger);">
            Error: Could not load transaction data.
          </td>
        </tr>
      `;
		}
	}

	await refreshAccountsPage();
	await loadBudgetsData();
	renderBudgetsPage();
	await loadAllocationsData();
	renderAllocationsPage();
	updateAccountStats();
	updateHeaderStats();
};

document.addEventListener("DOMContentLoaded", bootstrap);
