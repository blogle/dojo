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
          <div v-if="modalView === 'add'">
              <span class="page-label">Account Onboarding</span>
              <h2 id="step-title">{{ wizardStepTitle }}</h2>
          </div>
          <div v-else>
            <p class="stat-card__label" data-modal-label>{{ modalTitleLabel }}</p>
            <h2 data-modal-title>{{ modalTitle }}</h2>
            <p class="u-muted u-small-note" data-modal-subtitle>{{ modalSubtitle }}</p>
          </div>
          
          <div v-if="modalView === 'add'" class="step-indicator" id="step-indicator">
              <div class="step-dot" :class="{ active: wizardStep >= 1 }"></div>
              <div class="step-dot" :class="{ active: wizardStep >= 2 }"></div>
              <div class="step-dot" :class="{ active: wizardStep >= 3 }"></div>
              <div class="step-dot" :class="{ active: wizardStep >= 4 }"></div>
          </div>
          <button v-else class="modal__close" type="button" aria-label="Close modal" data-close-modal @click="closeModal">×</button>
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
             <div class="form-panel__actions form-panel__actions--split">
               <button
                 type="button"
                 class="button button--secondary"
                 data-reconcile-button
                 @click.stop="openReconcileModal"
               >
                 Reconcile
               </button>
               <button
                 v-if="selectedAccount?.account_class === 'investment'"
                 type="button"
                 class="button button--primary"
                 data-view-portfolio-button
                 @click.stop="openInvestmentPortfolio"
               >
                 View portfolio
               </button>
             </div>

          </section>

          <!-- Add View (Wizard) -->
          <section v-if="modalView === 'add'" class="modal-add" data-modal-section="add">
            
            <datalist id="institutions">
                <option v-for="inst in institutionList" :key="inst" :value="inst"></option>
            </datalist>

            <!-- Step 1: Select Type -->
            <div v-if="wizardStep === 1" class="wizard-step active">
                <p class="u-muted" style="margin-bottom: 1.5rem;">Choose the category that best describes this asset or liability to determine how it affects your net worth and budget.</p>
                <div class="type-grid">
                     <div v-for="(schema, key) in WIZARD_SCHEMAS" :key="key" 
                          class="type-card" 
                          :class="{ selected: wizardType === key }"
                          @click="selectWizardType(key)">
                        <svg class="type-icon" viewBox="0 0 24 24" v-html="schema.icon"></svg>
                        <strong>{{ schema.label }}</strong>
                    </div>
                </div>
            </div>

            <!-- Step 2: Details -->
            <div v-if="wizardStep === 2" class="wizard-step active">
                 <div id="dynamic-fields">
                     <template v-if="currentSchema">
                         <div v-for="field in currentSchema.fields" :key="field.id">
                             <label v-if="field.type === 'checkbox'" class="checkbox-label">
                                 <input type="checkbox" v-model="wizardData[field.id]">
                                 <span>{{ field.label }}</span>
                             </label>
                             <label v-else>
                                 {{ field.label }}
                                 <select v-if="field.type === 'select'" v-model="wizardData[field.id]">
                                     <option value="" disabled selected>Select...</option>
                                     <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
                                 </select>
                                 <textarea v-else-if="field.type === 'textarea'" v-model="wizardData[field.id]" :rows="field.rows || 3" :placeholder="field.placeholder"></textarea>
                                 <input v-else 
                                        :type="field.type" 
                                        v-model="wizardData[field.id]" 
                                        :list="field.list" 
                                        :step="field.step" 
                                        :placeholder="field.placeholder">
                             </label>
                             <span v-if="field.helper" class="helper-text" :style="field.type === 'checkbox' ? 'margin-top: -1rem; margin-bottom: 1rem; margin-left: 0.5rem;' : ''">{{ field.helper }}</span>
                         </div>
                     </template>
                 </div>
            </div>

            <!-- Step 3: Balance -->
            <div v-if="wizardStep === 3" class="wizard-step active">
                 <label>
                    {{ currentSchema.balanceLabel }}
                    <input type="number" class="u-mono" step="0.01" placeholder="0.00" style="font-size: 1.5rem; padding: 1rem;" v-model="wizardData.balance">
                    <span v-if="currentSchema.balanceHelper" class="helper-text">{{ currentSchema.balanceHelper }}</span>
                </label>
                <label>
                    As of Date
                    <input type="date" v-model="wizardData.balance_date">
                </label>
            </div>

            <!-- Step 4: Review -->
            <div v-if="wizardStep === 4" class="wizard-step active">
                <p class="u-muted" style="margin-bottom: 1.5rem;">Review the configuration before creating the ledger entries.</p>
                <div class="summary-grid" id="review-summary">
                    <div class="summary-item">
                        <strong>Account Type</strong>
                        <span>{{ currentSchema.label }}</span>
                    </div>
                    <div v-for="field in currentSchema.fields" :key="field.id" class="summary-item">
                         <strong>{{ field.label }}</strong>
                         <span>{{ formatReviewValue(field, wizardData[field.id]) }}</span>
                    </div>
                    <div class="summary-item" style="grid-column: span 2; border-top: 1px solid var(--border); margin-top: 0.5rem; padding-top: 1rem;">
                        <strong>{{ currentSchema.balanceLabel }}</strong>
                        <span class="u-mono" style="font-size: 1.5rem;">{{ formatCurrency(wizardData.balance) }}</span>
                    </div>
                </div>
            </div>

            <!-- Step 5: Success (Optional separate view or close) -->
             <!-- We just close modal on success as per old flow, but user mockup had a success step. I'll implement it if needed, but 'closeModal' seems standard. -->

            <!-- FOOTER ACTIONS -->
            <div class="wizard-actions">
                <button type="button" class="button button--text" @click="changeStep(-1)" :disabled="wizardStep === 1 && !isCreating">Back</button>
                <button v-if="wizardStep < 4" type="button" class="button button--primary" @click="changeStep(1)" :disabled="!canProceed">Next</button>
                <button v-else type="button" class="button button--primary" @click="handleCreateAccount" :disabled="isCreating">
                    {{ isCreating ? "Creating..." : "Create Account" }}
                </button>
            </div>

          </section>
        </div>
      </div>
    </div>

    <ReconciliationModal
      :open="isReconciliationOpen"
      :account="selectedAccount"
      @close="closeReconciliationModal"
    />
  </section>
</template>

<script setup>
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { accountGroupDefinitions, accountTypeMapping } from "../constants.js";
import ReconciliationModal from "../components/ReconciliationModal.vue";
import { api, postOpeningBalanceTransaction } from "../services/api.js";
import { formatAmount } from "../services/format.js";
import { todayISO } from "../services/format.js";

const queryClient = useQueryClient();
const router = useRouter();
const filter = ref("all");
const isModalOpen = ref(false);
const modalView = ref("add"); // 'add' | 'detail'
const selectedAccount = ref(null);
const isReconciliationOpen = ref(false);

// Wizard State
const wizardStep = ref(1);
const wizardType = ref(null);
const wizardData = reactive({});

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

const WIZARD_SCHEMAS = {
	cash: {
		label: "Cash & Checking",
		icon: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.31-8.86c-1.77-.45-2.34-.94-2.34-1.67 0-.84.79-1.43 2.1-1.43 1.38 0 1.9.66 1.94 1.64h1.71c-.05-1.34-.87-2.57-2.49-2.97V5H10.9v1.69c-1.51.32-2.72 1.3-2.72 2.81 0 1.79 1.49 2.69 3.66 3.21 1.95.46 2.34 1.15 2.34 1.86 0 .92-.81 1.67-2.11 1.67-1.47 0-2.13-.61-2.21-1.63h-1.73c.06 1.69.93 2.54 2.74 2.97V20h1.97v-1.7c1.51-.32 2.71-1.29 2.71-2.81 0-1.92-1.43-2.8-3.55-3.35z"/>',
		title: "Cash & Checking Details",
		balanceLabel: "Current Ledger Balance",
		account_class: "cash",
		account_type: "asset",
		account_role: "on_budget",
		fields: [
			{
				id: "institution_name",
				label: "Institution",
				type: "text",
				list: "institutions",
				placeholder: "Select or type...",
			},
			{
				id: "account_name",
				label: "Account Nickname",
				type: "text",
				placeholder: "e.g. Primary Checking",
			},
			{
				id: "interest_rate_apy",
				label: "Interest Rate (APY %)",
				type: "number",
				step: "0.01",
				placeholder: "0.00",
			},
		],
	},
	credit: {
		label: "Credit Card",
		icon: '<path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>',
		title: "Credit Card Details",
		balanceLabel: "Current Amount Owed",
		balanceHelper:
			"Enter as a positive number. The system will track it as a liability.",
		account_class: "credit",
		account_type: "liability",
		account_role: "on_budget",
		fields: [
			{
				id: "institution_name",
				label: "Institution",
				type: "text",
				list: "institutions",
				placeholder: "Select or type...",
			},
			{
				id: "account_name",
				label: "Card Nickname",
				type: "text",
				placeholder: "e.g. Gold Card",
			},
			{
				id: "card_type",
				label: "Network",
				type: "select",
				options: ["Visa", "Mastercard", "American Express", "Discover"],
			},
			{ id: "apr", label: "Purchase APR (%)", type: "number", step: "0.01" },
			{
				id: "cash_advance_apr",
				label: "Cash Advance APR (%)",
				type: "number",
				step: "0.01",
			},
		],
	},
	accessible: {
		label: "Savings / CD",
		icon: '<path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>',
		title: "Accessible Asset Details",
		balanceLabel: "Current Balance",
		account_class: "accessible",
		account_type: "asset",
		account_role: "tracking",
		fields: [
			{
				id: "institution_name",
				label: "Institution",
				type: "text",
				list: "institutions",
				placeholder: "Select or type...",
			},
			{ id: "account_name", label: "Account Nickname", type: "text" },
			{ id: "term_end_date", label: "Maturity Date (Optional)", type: "date" },
			{
				id: "interest_rate_apy",
				label: "APY (%)",
				type: "number",
				step: "0.01",
			},
			{
				id: "early_withdrawal_penalty",
				label: "Early Withdrawal Penalty",
				type: "checkbox",
				helper: "Check if this account charges fees for early access.",
			},
		],
	},
	investment: {
		label: "Investment",
		icon: '<path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/>',
		title: "Investment Account Details",
		balanceLabel: "Uninvested Cash Balance",
		balanceHelper:
			"Holdings (Stocks/ETFs) are tracked separately via the Positions table.",
		account_class: "investment",
		account_type: "asset",
		account_role: "tracking",
		fields: [
			{
				id: "institution_name",
				label: "Institution",
				type: "text",
				list: "institutions",
				placeholder: "Select or type...",
			},
			{ id: "account_name", label: "Account Nickname", type: "text" },
			{
				id: "tax_classification",
				label: "Tax Classification",
				type: "select",
				options: [
					"Taxable Brokerage",
					"Traditional IRA",
					"Roth IRA",
					"401k",
					"403b",
					"529",
				],
			},
			{
				id: "is_self_directed",
				label: "Self-Directed",
				type: "checkbox",
				helper: "Check if you manage trades manually.",
			},
			{
				id: "risk_free_sweep_rate",
				label: "Sweep Fund Rate (%)",
				type: "number",
				step: "0.01",
			},
		],
	},
	loan: {
		label: "Loan / Mortgage",
		icon: '<path d="M17 7h-4v2h4c1.65 0 3 1.35 3 3s-1.35 3-3 3h-4v2h4c2.76 0 5-2.24 5-5s-2.24-5-5-5zm-6 8H7c-1.65 0-3-1.35-3-3s1.35-3 3-3h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-2zm-3-4h8v2H8z"/>',
		title: "Loan Details",
		balanceLabel: "Current Outstanding Balance",
		account_class: "loan",
		account_type: "liability",
		account_role: "tracking",
		fields: [
			{
				id: "institution_name",
				label: "Institution",
				type: "text",
				list: "institutions",
				placeholder: "Select or type...",
			},
			{
				id: "loan_name",
				label: "Loan Nickname",
				type: "text",
				placeholder: "e.g. Student Loan A",
			},
			{
				id: "initial_principal_minor",
				label: "Original Principal",
				type: "number",
				step: "0.01",
			}, // Logic to x100
			{
				id: "interest_rate_apy",
				label: "Interest Rate (%)",
				type: "number",
				step: "0.01",
			},
			{
				id: "mortgage_escrow_details",
				label: "Escrow Notes",
				type: "text",
				placeholder: "Optional tax/insurance details",
			},
		],
	},
	tangible: {
		label: "Tangible Asset",
		icon: '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>',
		title: "Asset Details",
		balanceLabel: "Current Fair Value",
		balanceHelper: "Estimated market value.",
		account_class: "tangible",
		account_type: "asset",
		account_role: "tracking",
		fields: [
			{
				id: "asset_name",
				label: "Asset Name",
				type: "text",
				placeholder: "e.g. 2018 Honda Civic",
			},
			{
				id: "acquisition_cost_minor",
				label: "Original Cost Basis",
				type: "number",
				step: "0.01",
			}, // Logic to x100
		],
	},
};

const currentSchema = computed(() =>
	wizardType.value ? WIZARD_SCHEMAS[wizardType.value] : null,
);

const wizardStepTitle = computed(() => {
	switch (wizardStep.value) {
		case 1:
			return "Select Account Type";
		case 2:
			return currentSchema.value?.title || "Account Details";
		case 3:
			return "Opening Balance";
		case 4:
			return "Review Configuration";
		default:
			return "";
	}
});

const canProceed = computed(() => {
	if (wizardStep.value === 1) return !!wizardType.value;
	if (wizardStep.value === 2) {
		// Basic validation: Check required fields.
		// For simplicity, assume all displayed text fields are required if they are for 'name'
		if (wizardType.value === "loan" && !wizardData.loan_name) return false;
		if (wizardType.value === "tangible" && !wizardData.asset_name) return false;
		if (
			wizardType.value !== "loan" &&
			wizardType.value !== "tangible" &&
			!wizardData.account_name
		)
			return false;
		return true;
	}
	if (wizardStep.value === 3) {
		// Balance is optional but date is required if balance is entered?
		// Or default to today.
		return !!wizardData.balance_date;
	}
	return true;
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

const openAddModal = () => {
	modalView.value = "add";
	selectedAccount.value = null;
	wizardStep.value = 1;
	wizardType.value = null;
	// Reset wizardData
	for (const key in wizardData) delete wizardData[key];
	wizardData.balance = "";
	wizardData.balance_date = todayISO();
	isModalOpen.value = true;
};

const openDetailModal = (account) => {
	modalView.value = "detail";
	selectedAccount.value = account;
	isModalOpen.value = true;
};

const openInvestmentPortfolio = () => {
	if (!selectedAccount.value) {
		return;
	}
	const accountId = selectedAccount.value.account_id;
	closeModal();
	router.push(`/investments/${accountId}`);
};

const openReconcileModal = () => {
	if (!selectedAccount.value) {
		return;
	}
	isModalOpen.value = false;
	isReconciliationOpen.value = true;
};

const closeReconciliationModal = () => {
	isReconciliationOpen.value = false;
};

const closeModal = () => {
	isModalOpen.value = false;
};

const selectWizardType = (key) => {
	wizardType.value = key;
};

const changeStep = (delta) => {
	wizardStep.value += delta;
};

const formatReviewValue = (field, value) => {
	if (typeof value === "boolean") return value ? "Yes" : "No";
	if (field.id.includes("minor")) {
		return value ? formatCurrency(value) : "—";
	}
	return value || "—";
};

const formatCurrency = (val) => {
	if (!val) return "$0.00";
	return Number(val).toLocaleString("en-US", {
		style: "currency",
		currency: "USD",
	});
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
		closeModal();
	},
});

const isCreating = computed(() => createAccountMutation.isPending.value);

const handleCreateAccount = async () => {
	const schema = currentSchema.value;
	// Determine name based on type
	const name =
		wizardData.account_name || wizardData.loan_name || wizardData.asset_name;

	if (!name) {
		alert("Please provide an account name.");
		return;
	}

	const parsedBalance = Number.parseFloat(wizardData.balance) || 0;
	const balanceMinor = Math.round(parsedBalance * 100);
	const accountId = slugify(name);

	// Prepare payload
	const payload = {
		account_id: accountId,
		name: name,
		account_type: schema.account_type,
		account_class: schema.account_class,
		account_role: schema.account_role,
		current_balance_minor: 0,
		currency: "USD",
		institution_name: wizardData.institution_name,
		// Extra fields
		interest_rate_apy: wizardData.interest_rate_apy
			? Number(wizardData.interest_rate_apy)
			: null,
		card_type: wizardData.card_type,
		apr: wizardData.apr ? Number(wizardData.apr) : null,
		cash_advance_apr: wizardData.cash_advance_apr
			? Number(wizardData.cash_advance_apr)
			: null,
		term_end_date: wizardData.term_end_date || null,
		early_withdrawal_penalty: !!wizardData.early_withdrawal_penalty,
		risk_free_sweep_rate: wizardData.risk_free_sweep_rate
			? Number(wizardData.risk_free_sweep_rate)
			: null,
		is_self_directed: !!wizardData.is_self_directed,
		tax_classification: wizardData.tax_classification,
		initial_principal_minor: wizardData.initial_principal_minor
			? Math.round(Number(wizardData.initial_principal_minor) * 100)
			: null,
		mortgage_escrow_details: wizardData.mortgage_escrow_details,
		asset_name: wizardData.asset_name,
		acquisition_cost_minor: wizardData.acquisition_cost_minor
			? Math.round(Number(wizardData.acquisition_cost_minor) * 100)
			: null,
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