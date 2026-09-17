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
        <span class="u-muted u-small-note">Cash + property (investments priced separately).</span>
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
            @click="openAccount(account)"
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

    <AccountWizardModal
      :open="isModalOpen"
      :pending="isCreating"
      :error-message="createErrorMessage"
      :institution-options="institutionList"
      @close="closeModal"
      @submit="handleWizardSubmit"
    />
  </section>
</template>

<script setup>
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import AccountWizardModal from "../components/accounts/AccountWizardModal.vue";
import { accountGroupDefinitions } from "../constants.js";
import { api, postOpeningBalanceTransaction } from "../services/api.js";
import { formatAmount } from "../services/format.js";

const queryClient = useQueryClient();
const router = useRouter();
const filter = ref("all");
const isModalOpen = ref(false);

const institutionList = [
	"Chase",
	"Bank of America",
	"Wells Fargo",
	"Citigroup",
	"American Express",
	"Vanguard",
	"Fidelity",
	"Charles Schwab",
	"Capital One",
	"Discover",
	"USAA",
	"Navy Federal Credit Union",
	"PNC Bank",
	"TD Bank",
	"Goldman Sachs",
	"Morgan Stanley",
	"Interactive Brokers",
	"E*TRADE",
	"Robinhood",
	"Coinbase",
	"SoFi",
	"Ally Bank",
];

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

const assetsTotal = computed(() => {
	const value = netWorthQuery.data.value?.assets_minor;
	return value !== undefined ? formatAmount(value) : "—";
});

const liabilitiesTotal = computed(() => {
	const value = netWorthQuery.data.value?.liabilities_minor;
	return value !== undefined ? formatAmount(-value) : "—";
});

const netWorthTotal = computed(() => {
	const value = netWorthQuery.data.value?.net_worth_minor;
	return value !== undefined ? formatAmount(value) : "—";
});

const readyToAssignTotal = computed(() => {
	const value = readyToAssignQuery.data.value?.ready_to_assign_minor;
	return value !== undefined ? formatAmount(value) : "—";
});

const accounts = computed(() =>
	(accountsQuery.data.value || []).filter((account) => account.is_active),
);

const filteredGroups = computed(() => {
	const groups = accountGroupDefinitions.map((group) => ({
		...group,
		accounts: accounts.value.filter(
			(account) => account.account_class === group.id,
		),
	}));

	const scopedGroups =
		filter.value === "all"
			? groups
			: groups.filter((group) =>
					filter.value === "assets"
						? group.type === "asset"
						: group.type === "liability",
				);

	return scopedGroups.filter((group) => group.accounts.length > 0);
});

const formatRoleLabel = (role) =>
	role === "on_budget" ? "On-budget" : "Tracking";

const formatAccountBalance = (account) => {
	const amount =
		account.account_type === "liability"
			? -account.current_balance_minor
			: account.current_balance_minor;
	return formatAmount(amount);
};

const slugify = (value) => {
	const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
	const trimmed = normalized.replace(/^_+|_+$/g, "");
	return `${trimmed || "account"}_${Date.now().toString(36)}`;
};

const createAccountMutation = useMutation({
	mutationFn: async ({ accountData, startingState }) => {
		const createdAccount = await api.accounts.create(accountData);

		if (startingState?.opening_balance_minor) {
			await postOpeningBalanceTransaction(
				createdAccount,
				startingState.opening_balance_minor,
				startingState.as_of_date,
			);
		}

		if (startingState?.reconcile_portfolio) {
			await api.investments.reconcile(
				createdAccount.account_id,
				startingState.reconcile_portfolio,
			);
		}

		return createdAccount;
	},
	onSuccess: () => {
		queryClient.invalidateQueries({ queryKey: ["accounts"] });
		queryClient.invalidateQueries({ queryKey: ["netWorth"] });
		queryClient.invalidateQueries({ queryKey: ["readyToAssign"] });
		queryClient.invalidateQueries({ queryKey: ["reference-data"] });
		closeModal();
	},
});

const isCreating = computed(() => createAccountMutation.isPending.value);
const createErrorMessage = computed(
	() => createAccountMutation.error.value?.message || "",
);

const openAddModal = () => {
	createAccountMutation.reset();
	isModalOpen.value = true;
};

const closeModal = () => {
	createAccountMutation.reset();
	isModalOpen.value = false;
};

const openAccount = (account) => {
	router.push(`/accounts/${account.account_id}`);
};

const handleWizardSubmit = async ({ accountData, startingState }) => {
	await createAccountMutation.mutateAsync({
		accountData: {
			...accountData,
			account_id: slugify(accountData.name),
		},
		startingState,
	});
};
</script>
