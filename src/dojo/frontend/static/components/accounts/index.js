import {
	accountGroupDefinitions,
	accountTypeMapping,
	selectors,
} from "../../constants.js";
import { api, postOpeningBalanceTransaction } from "../../services/api.js";
import { formatAmount } from "../../services/format.js";
import { store } from "../../store.js";

const formatRoleLabel = (role) =>
	role === "on_budget" ? "On-budget" : "Tracking";

const slugify = (value) => {
	const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
	const trimmed = normalized.replace(/^_+|_+$/g, "");
	return `${trimmed || "account"}_${Date.now().toString(36)}`;
};

let modalOverlay;
let modalElement;
let modalTitle;
let modalLabel;
let modalSubtitle;
let modalMetadata;
let modalBalance;
let refreshReferenceData = async () => {};
let refreshBudgetsData = async () => {};
let renderBudgetsPage = () => {};
let refreshTransactionsPage = async () => {};

const setModalView = (view) => {
	if (!modalOverlay) return;
	modalOverlay.dataset.view = view;
	if (modalElement) {
		modalElement.dataset.view = view;
	}
};

const toggleAccountModal = (show, view = "add") => {
	if (!modalOverlay) return;
	modalOverlay.classList.toggle("is-visible", show);
	modalOverlay.style.display = show ? "flex" : "none";
	modalOverlay.setAttribute("aria-hidden", show ? "false" : "true");
	setModalView(show ? view : modalOverlay.dataset.view || "add");
};

const groupAccounts = () => {
	const state = store.getState();
	return accountGroupDefinitions.map((group) => ({
		...group,
		accounts: state.accounts.filter(
			(account) => account.account_class === group.id,
		),
	}));
};

const getFilteredGroups = () => {
	const state = store.getState();
	const groups = groupAccounts();
	const scope =
		state.accountFilter === "all"
			? groups
			: groups.filter((group) =>
					state.accountFilter === "assets"
						? group.type === "asset"
						: group.type === "liability",
				);
	return scope.filter((group) => group.accounts.length > 0);
};

const renderAccountGroups = () => {
	const container = document.querySelector(selectors.accountGroups);
	if (!container) {
		return;
	}

	const groups = getFilteredGroups();
	if (!groups.length) {
		container.innerHTML = '<p class="u-muted">No accounts available.</p>';
		return;
	}

	container.innerHTML = groups
		.map((group) => {
			const cards = group.accounts
				.map(
					(account) => `
            <div class="account-card" data-account-id="${account.account_id}">
              <div class="account-card__header">
                <div class="account-card__title">
                  <span class="account-card__name">${account.name}</span>
                  <span class="account-card__role-icon" data-role="${account.account_role}" aria-label="${formatRoleLabel(
										account.account_role,
									)}"></span>
                </div>
                <span class="account-card__balance">${formatAmount(
									account.account_type === "liability"
										? -account.current_balance_minor
										: account.current_balance_minor,
								)}</span>
              </div>
              <div class="account-card__meta">
                <span>${account.account_class.replace(/_/g, " ")}</span>
                <span>${account.account_type === "asset" ? "Asset" : "Liability"}</span>
              </div>
            </div>
          `,
				)
				.join("");

			return `
        <article class="account-group">
          <header class="account-group__header">
            <div>
              <p class="account-group__title">${group.title}</p>
              <p class="u-muted u-small-note">${group.description}</p>
            </div>
            <span class="u-muted">${group.accounts.length} account${group.accounts.length === 1 ? "" : "s"}</span>
          </header>
          <div class="account-cards">
            ${cards || `<p class="u-muted">No accounts in this section yet.</p>`}
          </div>
        </article>
      `;
		})
		.join("");

	container.querySelectorAll(".account-card").forEach((card) => {
		card.addEventListener("click", () => {
			const accountId = card.getAttribute("data-account-id");
			const state = store.getState();
			const account = state.accounts.find(
				(acc) => acc.account_id === accountId,
			);
			if (account) {
				showAccountDetail(account);
			}
		});
	});
};

const updateAccountStats = () => {
	const state = store.getState();
	const assetsEl = document.querySelector(selectors.assetsTotal);
	const liabilitiesEl = document.querySelector(selectors.liabilitiesTotal);
	const netWorthEl = document.querySelector(selectors.netWorth);
	const readyEl = document.querySelector(selectors.readyToAssign);

	if (state.netWorth) {
		if (assetsEl) {
			assetsEl.textContent = formatAmount(state.netWorth.assets_minor);
		}
		if (liabilitiesEl) {
			liabilitiesEl.textContent = formatAmount(
				-state.netWorth.liabilities_minor,
			);
		}
		if (netWorthEl) {
			netWorthEl.textContent = formatAmount(state.netWorth.net_worth_minor);
		}
	}

	if (readyEl) {
		if (state.readyToAssign) {
			readyEl.textContent = formatAmount(
				state.readyToAssign.ready_to_assign_minor,
			);
		} else {
			readyEl.textContent = "—";
		}
	}
};

const showAccountDetail = (account) => {
	if (!account || !modalLabel || !modalTitle || !modalSubtitle) {
		return;
	}
	modalLabel.textContent = "Account detail";
	modalTitle.textContent = account.name;
	modalSubtitle.textContent = `ID • ${account.account_id}`;
	if (modalBalance) {
		modalBalance.textContent = formatAmount(account.current_balance_minor);
	}
	if (modalMetadata) {
		modalMetadata.innerHTML = `
      <li><strong>Type</strong><span>${account.account_type === "asset" ? "Asset" : "Liability"}</span></li>
      <li><strong>Class</strong><span>${account.account_class.replace(/_/g, " ")}</span></li>
      <li><strong>Role</strong><span>${formatRoleLabel(account.account_role)}</span></li>
    `;
	}
	toggleAccountModal(true, "detail");
};

const showAddAccountModal = () => {
	if (!modalLabel || !modalTitle || !modalSubtitle) {
		return;
	}
	modalLabel.textContent = "Add account";
	modalTitle.textContent = "Follow the guided steps";
	modalSubtitle.textContent = "Create a new asset or liability";
	toggleAccountModal(true, "add");
};

const handleAddAccount = async () => {
	const nameInput = document.querySelector(selectors.modalNameInput);
	const balanceInput = document.querySelector(selectors.modalBalanceInput);
	const typeSelect = document.querySelector(selectors.modalTypeSelect);

	if (!nameInput || !balanceInput || !typeSelect) return;

	const name = nameInput.value.trim();
	if (!name) {
		alert("Please provide an account name.");
		return;
	}

	const mapping = accountTypeMapping[typeSelect.value];
	if (!mapping) {
		alert("Please choose a valid account type.");
		return;
	}

	const parsedBalance = Number.parseFloat(balanceInput.value) || 0;
	const balanceMinor = Math.round(parsedBalance * 100);
	const accountId = slugify(name);

	const payload = {
		account_id: accountId,
		name,
		account_type: mapping.account_type,
		account_class: mapping.account_class,
		account_role: mapping.account_role,
		current_balance_minor: 0,
		currency: "USD",
	};

	try {
		const createdAccount = await api.accounts.create(payload);

		if (balanceMinor !== 0) {
			try {
				await postOpeningBalanceTransaction(createdAccount, balanceMinor);
			} catch (innerError) {
				console.error(innerError);
				alert(
					"Account created, but we couldn't record the opening balance transaction. You can retry from the ledger later.",
				);
			}
		}

		nameInput.value = "";
		balanceInput.value = "";
		toggleAccountModal(false);
		try {
			await Promise.all([
				refreshAccountsPage(),
				refreshReferenceData(),
				refreshBudgetsData(),
			]);
			renderBudgetsPage();
			await refreshTransactionsPage();
		} catch (refreshError) {
			console.error(
				"Account created but failed to refresh UI state",
				refreshError,
			);
		}
	} catch (error) {
		console.error(error);
		alert(error.message || "Failed to create account.");
	}
};

const refreshAccountsPage = async () => {
	try {
		const accounts = await api.accounts.list();
		store.setState((prev) => ({
			...prev,
			accounts: (accounts || []).filter((acct) => acct.is_active),
		}));
	} catch (error) {
		console.error("Failed to fetch accounts", error);
	}
	try {
		const netWorth = await api.netWorth.current();
		store.setState((prev) => ({
			...prev,
			netWorth,
		}));
	} catch (error) {
		console.warn("Net worth endpoint unavailable", error);
	}
	try {
		const readyToAssign = await api.readyToAssign.current();
		store.setState((prev) => ({
			...prev,
			readyToAssign,
		}));
	} catch (error) {
		console.error("Failed to fetch Ready to Assign", error);
	}
	updateAccountStats();
	renderAccountGroups();
};

const initAccountFilter = () => {
	const sectionLinks = document.querySelectorAll(selectors.accountSectionLink);
	const updateSectionActive = (active) => {
		sectionLinks.forEach((link) => {
			const section = link.getAttribute("data-account-section");
			link.classList.toggle(
				"accounts-page__filter-button--active",
				section === active,
			);
		});
	};

	updateSectionActive(store.getState().accountFilter);

	sectionLinks.forEach((link) => {
		link.addEventListener("click", () => {
			const section = link.getAttribute("data-account-section");
			store.setState((prev) => ({ ...prev, accountFilter: section }));
			updateSectionActive(section);
			renderAccountGroups();
		});
	});
};

export const initAccounts = ({
	onAccountCreated,
	onReferenceRefresh,
	onBudgetsRefresh,
	onBudgetsRender,
	onTransactionsRefresh,
} = {}) => {
	refreshReferenceData = onReferenceRefresh || (async () => {});
	refreshBudgetsData = onBudgetsRefresh || (async () => {});
	renderBudgetsPage = onBudgetsRender || (() => {});
	refreshTransactionsPage = onTransactionsRefresh || (async () => {});
	modalOverlay = document.querySelector(selectors.accountModal);
	modalElement = modalOverlay?.querySelector(".modal");
	modalTitle = document.querySelector(selectors.accountModalTitle);
	modalLabel = document.querySelector(selectors.accountModalLabel);
	modalSubtitle = document.querySelector(selectors.accountModalSubtitle);
	modalMetadata = document.querySelector(selectors.accountModalMetadata);
	modalBalance = document.querySelector(selectors.accountModalBalance);

	initAccountFilter();

	const addAccountBtn = document.querySelector(selectors.addAccountButton);
	addAccountBtn?.addEventListener("click", () => showAddAccountModal());

	const modalClose = document.querySelector(selectors.modalClose);
	modalClose?.addEventListener("click", () => toggleAccountModal(false));

	if (modalOverlay) {
		modalOverlay.addEventListener("click", (event) => {
			if (event.target === modalOverlay) {
				toggleAccountModal(false);
			}
		});
	}

	const modalSubmit = document.querySelector(selectors.modalAddButton);
	modalSubmit?.addEventListener("click", async () => {
		await handleAddAccount();
		if (onAccountCreated) {
			onAccountCreated();
		}
	});

	const addFormType = document.querySelector(selectors.modalTypeSelect);
	if (addFormType) {
		addFormType.addEventListener("change", () => {
			const mapping = accountTypeMapping[addFormType.value];
			const subtitle = document.querySelector("[data-modal-type-hint]");
			if (subtitle) {
				subtitle.textContent = mapping
					? `${mapping.account_class.replace(/_/g, " ")} · ${mapping.account_role === "on_budget" ? "On-budget" : "Tracking"}`
					: "";
			}
		});
	}
};

export { renderAccountGroups, refreshAccountsPage, updateAccountStats };
