<template>
  <section class="route-page route-page--active accounts-page" id="accounts-page" data-route="accounts">
    <header class="accounts-page__header">
      <div class="accounts-page__nav">
        <p class="page-label">Assets &amp; Liabilities</p>
        <nav class="accounts-page__filter" aria-label="Accounts navigation">
          <button
            type="button"
            class="accounts-page__filter-button"
            :class="{ 'accounts-page__filter-button--active': filter === 'all' }"
            @click="filter = 'all'"
            data-account-section="all"
          >
            All
          </button>
          <button
            type="button"
            class="accounts-page__filter-button"
            :class="{ 'accounts-page__filter-button--active': filter === 'assets' }"
            @click="filter = 'assets'"
            data-account-section="assets"
          >
            Assets
          </button>
          <button
            type="button"
            class="accounts-page__filter-button"
            :class="{ 'accounts-page__filter-button--active': filter === 'liabilities' }"
            @click="filter = 'liabilities'"
            data-account-section="liabilities"
          >
            Liabilities
          </button>
        </nav>
      </div>
      <button class="button button--primary" data-add-account-button @click="openAddModal">
        + Add account
      </button>
    </header>

    <div class="accounts-page__stats">
      <article class="stat-card">
        <span class="stat-card__label">Total assets</span>
        <span id="assets-total" class="stat-card__value">{{ assetsTotal }}</span>
        <span class="u-muted u-small-note">Includes cash, investments, property.</span>
      </article>
      <article class="stat-card">
        <span class="stat-card__label">Total liabilities</span>
        <span id="liabilities-total" class="stat-card__value">{{ liabilitiesTotal }}</span>
        <span class="u-muted u-small-note">Mortgages, loans &amp; lines of credit.</span>
      </article>
      <article class="stat-card">
        <span class="stat-card__label">Net worth</span>
        <span id="net-worth" class="stat-card__value">{{ netWorthTotal }}</span>
        <span class="u-muted u-small-note">Assets minus liabilities.</span>
      </article>
      <article class="stat-card">
        <span class="stat-card__label">Ready to assign</span>
        <span id="ready-to-assign" class="stat-card__value">{{ readyToAssignTotal }}</span>
        <span class="u-muted u-small-note">Unallocated cash available to budget.</span>
      </article>
    </div>

    <div class="accounts-groups" id="account-groups">
      <p v-if="isLoading" class="u-muted">Loading accounts...</p>
      <p v-else-if="!filteredGroups.length" class="u-muted">No accounts available.</p>
      <article v-else v-for="group in filteredGroups" :key="group.id" class="account-group">
        <header class="account-group__header">
          <div>
            <p class="account-group__title">{{ group.title }}</p>
            <p class="u-muted u-small-note">{{ group.description }}</p>
          </div>
          <span class="u-muted">{{ group.accounts.length }} account{{ group.accounts.length === 1 ? "" : "s" }}</span>
        </header>
        <div class="account-cards">
          <div
            v-for="account in group.accounts"
            :key="account.account_id"
            class="account-card"
            :data-account-id="account.account_id"
            @click="openDetailModal(account)"
          >
            <div class="account-card__header">
              <div class="account-card__title">
                <span class="account-card__name">{{ account.name }}</span>
                <span
                  class="account-card__role-icon"
                  :data-role="account.account_role"
                  :aria-label="formatRoleLabel(account.account_role)"
                ></span>
              </div>
              <span class="account-card__balance">{{ formatAccountBalance(account) }}</span>
            </div>
            <div class="account-card__meta">
              <span>{{ account.account_class.replace(/_/g, " ") }}</span>
              <span>{{ account.account_type === "asset" ? "Asset" : "Liability" }}</span>
            </div>
          </div>
        </div>
      </article>
    </div>

    <!-- Modal Overlay -->
    <div
      v-if="isModalOpen"
      class="modal-overlay is-visible"
      id="account-modal"
      aria-hidden="false"
      :data-view="modalView"
      style="display: flex;"
      @click.self="closeModal"
    >
      <div class="modal" :data-view="modalView">
        <header class="modal__header">
          <div>
            <p class="stat-card__label" data-modal-label>{{ modalTitleLabel }}</p>
            <h2 data-modal-title>{{ modalTitle }}</h2>
            <p class="u-muted u-small-note" data-modal-subtitle>{{ modalSubtitle }}</p>
          </div>
          <button class="modal__close" type="button" aria-label="Close modal" data-close-modal @click="closeModal">×</button>
        </header>
        <div class="modal__body">
          <!-- Detail View -->
          <section v-if="modalView === 'detail'" class="modal-detail" data-modal-section="detail">
            <div class="modal-detail__balance" data-modal-balance>
              {{ selectedAccount ? formatAmount(selectedAccount.current_balance_minor) : "—" }}
            </div>
            <ul class="modal-detail__metadata" data-modal-metadata>
              <template v-if="selectedAccount">
                <li><strong>Type</strong><span>{{ selectedAccount.account_type === "asset" ? "Asset" : "Liability" }}</span></li>
                <li><strong>Class</strong><span>{{ selectedAccount.account_class.replace(/_/g, " ") }}</span></li>
                <li><strong>Role</strong><span>{{ formatRoleLabel(selectedAccount.account_role) }}</span></li>
              </template>
            </ul>
            <div class="role-legend">
              <span class="role-legend__item">
                <span class="role-icon" data-role="on_budget" aria-hidden="true"></span>
                <span>On-budget</span>
              </span>
              <span class="role-legend__item">
                <span class="role-icon" data-role="tracking" aria-hidden="true"></span>
                <span>Tracking</span>
              </span>
            </div>
          </section>

          <!-- Add View -->
          <section v-if="modalView === 'add'" class="modal-add" data-modal-section="add">
            <p class="u-muted u-small-note" data-modal-type-hint>{{ addTypeHint }}</p>
            <ol class="modal-steps">
              <li><strong>Step 1:</strong> Choose the account type (checking, credit, investment, etc.).</li>
              <li><strong>Step 2:</strong> Enter the institution name and the account nickname.</li>
              <li><strong>Step 3:</strong> Record the current balance and reconcile with statements.</li>
            </ol>
            <form class="modal-form" @submit.prevent="handleAddAccount">
              <label>
                Account type
                <select name="type" v-model="addForm.type">
                  <option value="checking">Checking</option>
                  <option value="credit">Credit Card</option>
                  <option value="brokerage">Brokerage</option>
                  <option value="loan">Loan / Mortgage</option>
                  <option value="asset">Other Asset</option>
                </select>
              </label>
              <label>
                Account name
                <input name="name" type="text" placeholder="e.g. Main Checking" v-model="addForm.name" required />
              </label>
              <label>
                Balance
                <input name="balance" type="number" step="0.01" placeholder="0.00" v-model="addForm.balance" />
              </label>
              <label>
                Notes
                <textarea name="notes" rows="3" placeholder="Optional context (e.g. interest rate, minimum payment)" v-model="addForm.notes"></textarea>
              </label>
              <button type="submit" class="button button--primary" data-add-account-submit :disabled="isCreating">
                {{ isCreating ? "Creating..." : "Review & create" }}
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, reactive, ref } from "vue";
import {
	accountGroupDefinitions,
	accountTypeMapping,
} from "../../../static/constants.js";
import {
	api,
	postOpeningBalanceTransaction,
} from "../../../static/services/api.js";
import { formatAmount } from "../../../static/services/format.js";

const queryClient = useQueryClient();
const filter = ref("all");
const isModalOpen = ref(false);
const modalView = ref("add"); // 'add' | 'detail'
const selectedAccount = ref(null);

const addForm = reactive({
	type: "checking",
	name: "",
	balance: "",
	notes: "",
});

// Queries
const accountsQuery = useQuery({
	queryKey: ["accounts"],
	queryFn: api.accounts.list,
});

const netWorthQuery = useQuery({
	queryKey: ["netWorth"],
	queryFn: api.netWorth.current,
});

const readyToAssignQuery = useQuery({
	queryKey: ["readyToAssign"],
	queryFn: () => api.readyToAssign.current(),
});

const isLoading = computed(
	() => accountsQuery.isPending.value || accountsQuery.isFetching.value,
);

// Stats
const assetsTotal = computed(() => {
	const val = netWorthQuery.data.value?.assets_minor;
	return val !== undefined ? formatAmount(val) : "—";
});

const liabilitiesTotal = computed(() => {
	const val = netWorthQuery.data.value?.liabilities_minor;
	return val !== undefined ? formatAmount(-val) : "—"; // Liabilities are usually positive in NW object but displayed as negative or positive depending on context. Legacy code: -state.netWorth.liabilities_minor
});

const netWorthTotal = computed(() => {
	const val = netWorthQuery.data.value?.net_worth_minor;
	return val !== undefined ? formatAmount(val) : "—";
});

const readyToAssignTotal = computed(() => {
	const val = readyToAssignQuery.data.value?.ready_to_assign_minor;
	return val !== undefined ? formatAmount(val) : "—";
});

// Accounts Grouping
const accounts = computed(() =>
	(accountsQuery.data.value || []).filter((acct) => acct.is_active),
);

const filteredGroups = computed(() => {
	const groups = accountGroupDefinitions.map((group) => ({
		...group,
		accounts: accounts.value.filter(
			(account) => account.account_class === group.id,
		),
	}));

	const scope =
		filter.value === "all"
			? groups
			: groups.filter((group) =>
					filter.value === "assets"
						? group.type === "asset"
						: group.type === "liability",
				);

	return scope.filter((group) => group.accounts.length > 0);
});

// Formatting
const formatRoleLabel = (role) =>
	role === "on_budget" ? "On-budget" : "Tracking";

const formatAccountBalance = (account) => {
	const amount =
		account.account_type === "liability"
			? -account.current_balance_minor
			: account.current_balance_minor;
	return formatAmount(amount);
};

// Modal Logic
const modalTitleLabel = computed(() =>
	modalView.value === "add" ? "Add account" : "Account detail",
);
const modalTitle = computed(() =>
	modalView.value === "add"
		? "Follow the guided steps"
		: selectedAccount.value?.name,
);
const modalSubtitle = computed(() =>
	modalView.value === "add"
		? "Create a new asset or liability"
		: `ID • ${selectedAccount.value?.account_id}`,
);
const addTypeHint = computed(() => {
	const mapping = accountTypeMapping[addForm.type];
	return mapping
		? `${mapping.account_class.replace(/_/g, " ")} · ${mapping.account_role === "on_budget" ? "On-budget" : "Tracking"}`
		: "";
});

const openAddModal = () => {
	modalView.value = "add";
	selectedAccount.value = null;
	addForm.type = "checking";
	addForm.name = "";
	addForm.balance = "";
	addForm.notes = "";
	isModalOpen.value = true;
};

const openDetailModal = (account) => {
	modalView.value = "detail";
	selectedAccount.value = account;
	isModalOpen.value = true;
};

const closeModal = () => {
	isModalOpen.value = false;
};

// Create Account Logic
const slugify = (value) => {
	const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
	const trimmed = normalized.replace(/^_+|_+$/g, "");
	return `${trimmed || "account"}_${Date.now().toString(36)}`;
};

const createAccountMutation = useMutation({
	mutationFn: async (payload) => {
		const createdAccount = await api.accounts.create(payload.accountData);
		if (payload.balanceMinor !== 0) {
			await postOpeningBalanceTransaction(createdAccount, payload.balanceMinor);
		}
		return createdAccount;
	},
	onSuccess: () => {
		queryClient.invalidateQueries({ queryKey: ["accounts"] });
		queryClient.invalidateQueries({ queryKey: ["netWorth"] });
		queryClient.invalidateQueries({ queryKey: ["readyToAssign"] });
		queryClient.invalidateQueries({ queryKey: ["reference-data"] });
		// Legacy support: also invalidate via window.dojoQueryClient if needed, but the api wrapper does that.
		closeModal();
	},
});

const isCreating = computed(() => createAccountMutation.isPending.value);

const handleAddAccount = async () => {
	if (!addForm.name) {
		alert("Please provide an account name.");
		return;
	}
	const mapping = accountTypeMapping[addForm.type];
	if (!mapping) {
		alert("Please choose a valid account type.");
		return;
	}

	const parsedBalance = Number.parseFloat(addForm.balance) || 0;
	const balanceMinor = Math.round(parsedBalance * 100);
	const accountId = slugify(addForm.name);

	const payload = {
		account_id: accountId,
		name: addForm.name,
		account_type: mapping.account_type,
		account_class: mapping.account_class,
		account_role: mapping.account_role,
		current_balance_minor: 0,
		currency: "USD",
	};

	try {
		await createAccountMutation.mutateAsync({
			accountData: payload,
			balanceMinor,
		});
	} catch (error) {
		console.error(error);
		alert(error.message || "Failed to create account.");
	}
};
</script>
