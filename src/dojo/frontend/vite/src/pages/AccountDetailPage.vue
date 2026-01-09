<template>
  <section
    class="route-page route-page--active investments-page account-detail-page"
    data-route="account-detail"
  >
    <header class="investments-header account-detail-page__header">
      <div class="account-detail-page__headline">
        <p class="page-label">{{ accountLabel }}</p>
        <p class="investments-header__value">{{ intervalEndValueLabel }}</p>
        <p
          v-if="intervalDeltaLabel"
          class="investments-header__perf"
          :class="intervalDeltaClass"
        >
          <span>{{ intervalDeltaLabel }}</span>
          <span v-if="intervalPctLabel">{{ intervalPctLabel }}</span>
        </p>
        <p v-if="accountSubtitle" class="u-muted u-small-note">
          {{ accountSubtitle }}
        </p>
      </div>

      <div class="account-detail-page__actions">
        <button
          v-if="primaryAction"
          type="button"
          class="button button--primary"
          @click="navigatePrimary"
          :disabled="!accountId"
        >
          {{ primaryAction.label }}
        </button>

        <button
          v-if="secondaryAction"
          type="button"
          class="button button--secondary"
          @click="secondaryAction.onClick"
          :disabled="secondaryAction.disabled"
        >
          {{ secondaryAction.label }}
        </button>
      </div>
    </header>

    <p v-if="pageError" class="form-panel__error" aria-live="polite">{{ pageError }}</p>
    <p v-else-if="pageLoading" class="u-muted">Loading account…</p>

    <template v-else-if="isInvestment">
      <section class="account-detail-page__hero-row">
        <div class="account-detail-page__hero-chart">
          <PortfolioChart
            :series="chartSeries"
            :interval="rangeLabel"
            :loading="chartLoading"
            :increaseIsGood="chartIncreaseIsGood"
            :showPercentChange="chartShowPercentChange"
            @change-interval="setRangeLabel"
          />
        </div>

        <div class="account-detail-page__hero-aside">
          <div class="investments-card">
            <p class="investments-card__title">Details</p>
            <dl class="investments-kv">
              <dt>NAV</dt>
              <dd>{{ investmentNavLabel }}</dd>
              <dt>Cost basis</dt>
              <dd>{{ investmentCostBasisLabel }}</dd>
              <dt>Deposits</dt>
              <dd :class="depositsClass">{{ investmentDepositsLabel }}</dd>
              <dt>% of portfolio</dt>
              <dd>{{ portfolioShareLabel }}</dd>
              <dt>Today's return</dt>
              <dd :class="todayReturnClass">{{ todayReturnLabel }}</dd>
              <dt>Total return</dt>
              <dd :class="totalReturnClass">{{ totalReturnLabel }}</dd>
              <dt>Account type</dt>
              <dd>{{ investmentAccountTypeLabel }}</dd>
            </dl>
          </div>

          <div v-if="!verifyHoldingsModalOpen" class="investments-card account-detail-page__cash-card">
            <p class="investments-card__title">Cash balance</p>
            <input
              class="investments-cash-input"
              data-testid="investment-cash-input"
              inputmode="decimal"
              :disabled="reconcilePending"
              v-model="cashDraft"
              @keydown.enter.prevent="saveCash"
              @blur="saveCash"
            />
            <p class="u-muted u-small-note account-detail-page__cash-help">
              Enter cash available in your brokerage. Saves on blur / Enter.
            </p>
          </div>
        </div>
      </section>

      <HoldingsTable
        v-if="!verifyHoldingsModalOpen"
        class="account-detail-page__holdings"
        data-testid="investment-holdings"
        :positions="portfolio?.positions || []"
        :pending="reconcilePending"
        @reconcile="handleReconcile"
      />
    </template>

    <div v-else class="investments-layout">
      <main>
        <div class="investments-card investments-chart">
          <PortfolioChart
            :series="chartSeries"
            :interval="rangeLabel"
            :loading="chartLoading"
            :increaseIsGood="chartIncreaseIsGood"
            :showPercentChange="chartShowPercentChange"
            @change-interval="setRangeLabel"
          />
        </div>

        <TransactionForm
          wrapperClass="account-detail-page__form"
          :accounts="accounts"
          :categories="categories"
          :allowedFlows="transactionFormAllowedFlows"
          :submitLabel="transactionSubmitLabel"
          :lockedAccountId="accountId"
          :lockedAccountName="accountName"
          :isSubmitting="isCreatingTransaction"
          :isLoadingReference="isLoadingReference"
          :referenceError="referenceError"
          @submit="handleCreateTransaction"
        />

        <div class="ledger-card">
          <TransactionTable
            :transactions="accountTransactions"
            :accounts="accounts"
            :categories="categories"
            :lockedAccountId="accountId"
            :lockedAccountName="accountName"
            :isLoading="isLoadingTransactions"
            :isLoadingReference="isLoadingReference"
            :referenceError="referenceError"
            :error="transactionsError"
            emptyMessage="No transactions found."
            loadingMessage="Loading transactions…"
            @update="handleUpdateTransaction"
            @delete="handleDeleteTransaction"
          />
        </div>
      </main>

      <aside>
        <div class="investments-card">
          <p class="investments-card__title">Details</p>

          <dl class="investments-kv">
            <dt>Account class</dt>
            <dd>{{ accountClassLabel }}</dd>
            <dt>Role</dt>
            <dd>{{ accountRoleLabel }}</dd>
            <dt>Institution</dt>
            <dd>{{ account?.institution_name || "—" }}</dd>
            <dt v-if="detailRows.length" style="grid-column: 1 / -1; margin-top: 0.75rem;">Configured</dt>
            <template v-for="row in detailRows" :key="row.label">
              <dt>{{ row.label }}</dt>
              <dd>{{ row.value }}</dd>
            </template>
          </dl>
        </div>
      </aside>
    </div>

    <ReconciliationModal
      :open="reconcileModalOpen"
      :account="account || null"
      @close="handleReconcileClose"
    />

    <div
      v-if="verifyHoldingsModalOpen"
      class="modal-overlay is-visible"
      style="display: flex;"
      @click.self="handleVerifyHoldingsClose"
    >
      <div class="modal account-detail-page__modal">
        <header class="modal__header">
          <div>
            <p class="stat-card__label">Verify holdings</p>
            <h2>{{ accountName || "Verify holdings" }}</h2>
            <p class="u-muted u-small-note">
              Reconcile ticker, quantity, cost basis, and cash balance.
            </p>
          </div>
          <button
            class="modal__close"
            type="button"
            aria-label="Close holdings verification"
            @click="handleVerifyHoldingsClose"
          >
            ×
          </button>
        </header>

        <div class="modal__body" style="overflow: auto;">
          <HoldingsTable
            class="investments-holdings"
            data-testid="investment-holdings"
            :positions="portfolio?.positions || []"
            :pending="reconcilePending"
            @reconcile="handleReconcile"
          />

          <div class="investments-card" style="margin-top: 1rem;">
            <p class="investments-card__title">Cash balance</p>
            <input
              class="investments-cash-input"
              data-testid="investment-cash-input"
              inputmode="decimal"
              :disabled="reconcilePending"
              v-model="cashDraft"
              @keydown.enter.prevent="saveCash"
              @blur="saveCash"
            />
            <p class="u-muted" style="margin-top: 0.5rem;">
              Enter cash available in your brokerage. Saves on blur / Enter.
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="valuationModalOpen"
      class="modal-overlay is-visible"
      style="display: flex;"
      @click.self="handleValuationClose"
    >
      <div class="modal account-detail-page__modal account-detail-page__modal--narrow">
        <header class="modal__header">
          <div>
            <p class="stat-card__label">Update valuation</p>
            <h2>{{ accountName || "Update valuation" }}</h2>
            <p class="u-muted u-small-note">
              Creates a non-cash balance adjustment (does not change Ready to assign).
            </p>
          </div>
          <button
            class="modal__close"
            type="button"
            aria-label="Close valuation"
            @click="handleValuationClose"
          >
            ×
          </button>
        </header>

        <div class="modal__body">
          <section class="modal-add">
            <form class="modal-form" @submit.prevent="submitValuation">
              <label>
                As of date
                <input type="date" v-model="valuationAsOf" required />
              </label>
              <label>
                Target value
                <input
                  type="number"
                  step="0.01"
                  inputmode="decimal"
                  placeholder="0.00"
                  v-model="valuationTarget"
                  required
                />
              </label>

              <p class="u-muted u-small-note">
                Current value: {{ valuationBaselineLabel }}
                <span v-if="valuationDeltaLabel"> · Delta: {{ valuationDeltaLabel }}</span>
              </p>

              <p
                v-if="valuationError || valuationBaselineError"
                class="form-panel__error"
                aria-live="polite"
              >
                {{ valuationError || valuationBaselineError }}
              </p>

              <div class="form-panel__actions form-panel__actions--split">
                <button
                  type="button"
                  class="button button--secondary"
                  :disabled="valuationSubmitting"
                  @click="handleValuationClose"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  class="button button--primary"
                  :disabled="valuationSubmitDisabled"
                >
                  {{ valuationSubmitting ? "Saving…" : "Save valuation" }}
                </button>
              </div>
            </form>
          </section>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { useMutation, useQuery } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import HoldingsTable from "../components/investments/HoldingsTable.vue";
import PortfolioChart from "../components/investments/PortfolioChart.vue";
import TransactionForm from "../components/TransactionForm.vue";
import TransactionTable from "../components/TransactionTable.vue";
import ReconciliationModal from "../components/ReconciliationModal.vue";
import { api } from "../services/api.js";
import {
	dollarsToMinor,
	formatAmount,
	minorToDollars,
	todayISO,
} from "../services/format.js";
import { useChartRange } from "../utils/chartRange.js";
import {
	dollarsInputToMinor,
	isValidDateInput,
} from "../utils/transactions.js";

const route = useRoute();
const router = useRouter();

const accountId = computed(() => {
	const raw = route.params.accountId;
	if (!raw) {
		return "";
	}
	return Array.isArray(raw) ? raw[0] : String(raw);
});

const { rangeLabel, range, setRangeLabel } = useChartRange({ route, router });

const routeRecordPath = computed(() => {
	const last = route.matched[route.matched.length - 1];
	return last?.path || "";
});

const routeMode = computed(() => {
	if (routeRecordPath.value.endsWith("/reconcile")) {
		return "reconcile";
	}
	if (routeRecordPath.value.endsWith("/verify-holdings")) {
		return "verify-holdings";
	}
	if (routeRecordPath.value.endsWith("/valuation")) {
		return "valuation";
	}
	return null;
});

const baseQuery = computed(() => {
	const next = { ...route.query };
	delete next.statementMonth;
	delete next.asOf;
	return next;
});

const navigateToBase = () => {
	if (!accountId.value) {
		return;
	}
	router.replace({
		path: `/accounts/${accountId.value}`,
		query: baseQuery.value,
	});
};

const referenceQuery = useQuery({
	queryKey: ["reference-data"],
	queryFn: api.reference.load,
	refetchOnWindowFocus: false,
});

const accountQuery = useQuery({
	queryKey: computed(() => ["accounts", accountId.value]),
	queryFn: () => api.accounts.get(accountId.value),
	enabled: computed(() => Boolean(accountId.value)),
	refetchOnWindowFocus: false,
});

const account = computed(() => accountQuery.data.value);

const isInvestment = computed(
	() => account.value?.account_class === "investment",
);
const isTangible = computed(() => account.value?.account_class === "tangible");
const isLiability = computed(() => account.value?.account_type === "liability");

const isLedgerAccount = computed(() => {
	const cls = account.value?.account_class;
	return (
		cls === "cash" || cls === "credit" || cls === "accessible" || cls === "loan"
	);
});

const reconcileModalOpen = computed(
	() =>
		routeMode.value === "reconcile" && isLedgerAccount.value && !!account.value,
);
const verifyHoldingsModalOpen = computed(
	() =>
		routeMode.value === "verify-holdings" &&
		isInvestment.value &&
		!!account.value,
);
const valuationModalOpen = computed(
	() => routeMode.value === "valuation" && isTangible.value && !!account.value,
);

const handleReconcileClose = () => navigateToBase();
const handleVerifyHoldingsClose = () => navigateToBase();
const handleValuationClose = () => navigateToBase();

watch(
	() => [routeMode.value, account.value?.account_class, accountId.value],
	() => {
		if (!routeMode.value || !accountId.value || !account.value?.account_class) {
			return;
		}
		if (routeMode.value === "reconcile" && !isLedgerAccount.value) {
			navigateToBase();
			return;
		}
		if (routeMode.value === "verify-holdings" && !isInvestment.value) {
			navigateToBase();
			return;
		}
		if (routeMode.value === "valuation" && !isTangible.value) {
			navigateToBase();
		}
	},
	{ immediate: true },
);

const transactionFormAllowedFlows = computed(() =>
	isLiability.value ? ["outflow"] : ["outflow", "inflow"],
);

const transactionSubmitLabel = computed(() =>
	isLiability.value ? "Add charge/fee" : "Save transaction",
);

const accounts = computed(() => referenceQuery.data.value?.accounts ?? []);
const categories = computed(() => referenceQuery.data.value?.categories ?? []);

const referenceError = computed(
	() => referenceQuery.error.value?.message || "",
);
const accountError = computed(() => accountQuery.error.value?.message || "");

const isLoadingReference = computed(
	() => referenceQuery.isPending.value || referenceQuery.isFetching.value,
);

const accountLoading = computed(
	() => accountQuery.isPending.value || accountQuery.isFetching.value,
);

const pageLoading = computed(
	() => isLoadingReference.value || accountLoading.value,
);

const titleCase = (value) => {
	if (!value) {
		return "";
	}
	return String(value)
		.split("_")
		.map((part) => (part ? `${part[0].toUpperCase()}${part.slice(1)}` : ""))
		.join(" ");
};

const accountName = computed(() => account.value?.name || "");

const accountLabel = computed(() => {
	const base = accountName.value || accountId.value;
	if (!base) {
		return "";
	}
	return String(base).toUpperCase();
});

const accountClassLabel = computed(() =>
	titleCase(account.value?.account_class),
);
const accountRoleLabel = computed(() => titleCase(account.value?.account_role));

const accountSubtitle = computed(() => {
	if (!account.value) {
		return "";
	}
	const cls = titleCase(account.value.account_class);
	const inst = account.value.institution_name
		? ` · ${account.value.institution_name}`
		: "";
	return `${cls}${inst}`;
});

const headlineValueMinor = computed(() => {
	if (isInvestment.value) {
		return portfolio.value?.nav_minor ?? null;
	}
	const raw = account.value?.current_balance_minor;
	if (raw === null || raw === undefined) {
		return null;
	}
	return isLiability.value ? -raw : raw;
});

const headlineValueLabel = computed(() => {
	if (headlineValueMinor.value === null) {
		return "—";
	}
	return formatAmount(headlineValueMinor.value);
});

const primaryAction = computed(() => {
	const cls = account.value?.account_class;
	if (!cls || !accountId.value) {
		return null;
	}
	if (cls === "investment") {
		return { label: "Verify holdings", mode: "verify-holdings" };
	}
	if (cls === "tangible") {
		return { label: "Update valuation", mode: "valuation" };
	}
	return { label: "Reconcile statement", mode: "reconcile" };
});

const navigatePrimary = () => {
	if (!primaryAction.value || !accountId.value) {
		return;
	}
	router.push({
		path: `/accounts/${accountId.value}/${primaryAction.value.mode}`,
		query: route.query,
	});
};

const handleRecordPayment = () => {
	if (!accountId.value) {
		return;
	}
	router.push({
		path: "/transfers",
		query: {
			destination_account_id: accountId.value,
		},
	});
};

const secondaryAction = computed(() => {
	if (!accountId.value) {
		return null;
	}
	if (isInvestment.value) {
		return {
			label: marketUpdatePending.value ? "Updating…" : "Update prices",
			disabled: marketUpdatePending.value,
			onClick: handleMarketUpdate,
		};
	}
	if (isLiability.value) {
		return {
			label: "Record payment",
			disabled: false,
			onClick: handleRecordPayment,
		};
	}
	return null;
});

const portfolioQuery = useQuery({
	queryKey: computed(() => ["investment-account", accountId.value]),
	queryFn: () => api.investments.getAccount(accountId.value),
	enabled: computed(() => Boolean(accountId.value) && isInvestment.value),
	refetchOnWindowFocus: false,
});

const investmentHistoryQuery = useQuery({
	queryKey: computed(() => [
		"investment-history",
		accountId.value,
		range.value.startDate,
		range.value.endDate,
	]),
	queryFn: () =>
		api.investments.getHistory(
			accountId.value,
			range.value.startDate,
			range.value.endDate,
		),
	enabled: computed(() => Boolean(accountId.value) && isInvestment.value),
	placeholderData: (previous) => previous,
	refetchOnWindowFocus: false,
});

const portfolio = computed(() => portfolioQuery.data.value);

const investmentNavLabel = computed(() => {
	if (!portfolio.value) {
		return "—";
	}
	return formatAmount(portfolio.value.nav_minor);
});

const investmentCostBasisLabel = computed(() => {
	if (!portfolio.value) {
		return "—";
	}
	return formatAmount(portfolio.value.ledger_cash_minor);
});

const investmentChartSeries = computed(() =>
	(investmentHistoryQuery.data.value || []).map((point) => ({
		date: point.market_date,
		value_minor: point.nav_minor,
	})),
);

const formatSignedMoney = (minor) => {
	if (minor === null || minor === undefined) {
		return "—";
	}
	const sign = minor > 0 ? "+" : "";
	return `${sign}${formatAmount(minor)}`;
};

const formatSignedRatioPct = (ratio) => {
	if (ratio === null || ratio === undefined) {
		return "";
	}
	const numeric = Number(ratio);
	if (!Number.isFinite(numeric)) {
		return "";
	}
	const pct = numeric * 100;
	const sign = pct > 0 ? "+" : "";
	return `${sign}${pct.toFixed(2)}%`;
};

const sortedInvestmentHistoryPoints = computed(() => {
	const data = investmentHistoryQuery.data.value || [];
	return [...data].sort((a, b) =>
		String(a.market_date).localeCompare(String(b.market_date)),
	);
});

const investmentDepositsMinor = computed(() => {
	if (!sortedInvestmentHistoryPoints.value.length) {
		return null;
	}
	return sortedInvestmentHistoryPoints.value.reduce(
		(sum, point) => sum + (point.cash_flow_minor || 0),
		0,
	);
});

const investmentDepositsLabel = computed(() =>
	formatSignedMoney(investmentDepositsMinor.value),
);

const depositsClass = computed(() => {
	const value = investmentDepositsMinor.value;
	if (value === null || value === undefined) {
		return "";
	}
	return value >= 0
		? "investments-header__perf--up"
		: "investments-header__perf--down";
});

const latestInvestmentPoint = computed(() => {
	const points = sortedInvestmentHistoryPoints.value;
	return points.length ? points[points.length - 1] : null;
});

const todayReturnMinor = computed(() => {
	if (!latestInvestmentPoint.value) {
		return null;
	}
	return latestInvestmentPoint.value.return_minor;
});

const todayReturnPct = computed(() => {
	if (!latestInvestmentPoint.value) {
		return null;
	}
	const base =
		latestInvestmentPoint.value.nav_minor -
		latestInvestmentPoint.value.return_minor;
	if (base === 0) {
		return null;
	}
	return latestInvestmentPoint.value.return_minor / base;
});

const todayReturnLabel = computed(() => {
	if (todayReturnMinor.value === null) {
		return "—";
	}
	const pctLabel =
		todayReturnPct.value === null
			? ""
			: ` (${formatSignedRatioPct(todayReturnPct.value)})`;
	return `${formatSignedMoney(todayReturnMinor.value)}${pctLabel}`;
});

const todayReturnClass = computed(() => {
	if (todayReturnMinor.value === null) {
		return "";
	}
	return todayReturnMinor.value >= 0
		? "investments-header__perf--up"
		: "investments-header__perf--down";
});

const totalReturnLabel = computed(() => {
	const minor = portfolio.value?.total_return_minor;
	if (minor === undefined || minor === null) {
		return "—";
	}
	const pct = portfolio.value?.total_return_pct;
	const pctLabel =
		pct === undefined || pct === null ? "" : ` (${formatSignedRatioPct(pct)})`;
	return `${formatSignedMoney(minor)}${pctLabel}`;
});

const investmentAccountTypeLabel = computed(() => {
	const details = account.value?.details;
	const raw = details?.tax_classification;
	if (raw) {
		return titleCase(raw);
	}
	return "—";
});

const netWorthQuery = useQuery({
	queryKey: ["netWorth"],
	queryFn: api.netWorth.current,
	enabled: computed(() => isInvestment.value),
	refetchOnWindowFocus: false,
});

const portfolioShareRatio = computed(() => {
	const totalHoldingsMinor = netWorthQuery.data.value?.positions_minor;
	const holdingsMinor = portfolio.value?.holdings_value_minor;
	if (
		!totalHoldingsMinor ||
		holdingsMinor === undefined ||
		holdingsMinor === null
	) {
		return null;
	}
	return holdingsMinor / totalHoldingsMinor;
});

const portfolioShareLabel = computed(() => {
	if (portfolioShareRatio.value === null) {
		return "—";
	}
	return `${(portfolioShareRatio.value * 100).toFixed(2)}%`;
});

const accountHistoryQuery = useQuery({
	queryKey: computed(() => [
		"accounts",
		accountId.value,
		"history",
		range.value.startDate,
		range.value.endDate,
		"all",
	]),
	queryFn: () =>
		api.accounts.getHistory(
			accountId.value,
			range.value.startDate,
			range.value.endDate,
			"all",
		),
	enabled: computed(
		() =>
			Boolean(accountId.value) &&
			Boolean(account.value?.account_class) &&
			!isInvestment.value,
	),
	placeholderData: (previous) => previous,
	refetchOnWindowFocus: false,
});

const accountTransactionsQuery = useQuery({
	queryKey: computed(() => [
		"accounts",
		accountId.value,
		"transactions",
		range.value.startDate,
		range.value.endDate,
		500,
		"all",
	]),
	queryFn: () =>
		api.accounts.getTransactions(accountId.value, {
			start_date: range.value.startDate,
			end_date: range.value.endDate,
			limit: 500,
			status: "all",
		}),
	enabled: computed(
		() =>
			Boolean(accountId.value) &&
			Boolean(account.value?.account_class) &&
			!isInvestment.value,
	),
	placeholderData: (previous) => previous,
	refetchOnWindowFocus: false,
});

const accountChartSeries = computed(() =>
	(accountHistoryQuery.data.value || []).map((point) => ({
		date: point.as_of_date,
		value_minor: isLiability.value ? -point.balance_minor : point.balance_minor,
	})),
);

const chartSeries = computed(() =>
	isInvestment.value ? investmentChartSeries.value : accountChartSeries.value,
);

const chartLoading = computed(() => {
	if (isInvestment.value) {
		return (
			investmentHistoryQuery.isPending.value ||
			investmentHistoryQuery.isFetching.value
		);
	}
	return (
		accountHistoryQuery.isPending.value || accountHistoryQuery.isFetching.value
	);
});

const chartIncreaseIsGood = computed(() => {
	if (isInvestment.value) {
		return true;
	}
	return !isLiability.value;
});

const chartShowPercentChange = computed(() => isInvestment.value);

const sortedChartSeries = computed(() => {
	const data = chartSeries.value ?? [];
	return [...data]
		.filter(
			(point) =>
				point &&
				typeof point.date === "string" &&
				Number.isFinite(point.value_minor),
		)
		.sort((a, b) => a.date.localeCompare(b.date));
});

const intervalStartValueMinor = computed(() => {
	if (sortedChartSeries.value.length < 2) {
		return null;
	}
	return sortedChartSeries.value[0]?.value_minor ?? null;
});

const intervalEndValueMinor = computed(() => {
	const last = sortedChartSeries.value[sortedChartSeries.value.length - 1];
	return last ? last.value_minor : null;
});

const intervalDeltaMinor = computed(() => {
	if (sortedChartSeries.value.length < 2) {
		return null;
	}
	if (
		intervalStartValueMinor.value === null ||
		intervalEndValueMinor.value === null
	) {
		return null;
	}
	return intervalEndValueMinor.value - intervalStartValueMinor.value;
});

const intervalPct = computed(() => {
	if (!chartShowPercentChange.value) {
		return null;
	}
	if (
		intervalStartValueMinor.value === null ||
		intervalDeltaMinor.value === null
	) {
		return null;
	}
	if (intervalStartValueMinor.value === 0) {
		return null;
	}
	return intervalDeltaMinor.value / intervalStartValueMinor.value;
});

const intervalEndValueLabel = computed(() => {
	if (intervalEndValueMinor.value === null) {
		return headlineValueLabel.value;
	}
	return formatAmount(intervalEndValueMinor.value);
});

const intervalDeltaLabel = computed(() => {
	if (intervalDeltaMinor.value === null) {
		return "";
	}
	const delta = intervalDeltaMinor.value;
	const sign = delta > 0 ? "+" : "";
	return `${sign}${formatAmount(delta)}`;
});

const intervalPctLabel = computed(() => {
	if (intervalPct.value === null) {
		return "";
	}
	return `(${intervalPct.value >= 0 ? "+" : ""}${(intervalPct.value * 100).toFixed(2)}%)`;
});

const intervalDeltaClass = computed(() => {
	if (intervalDeltaMinor.value === null) {
		return "";
	}
	const delta = intervalDeltaMinor.value;
	const good = chartIncreaseIsGood.value ? delta >= 0 : delta <= 0;
	return good
		? "investments-header__perf--up"
		: "investments-header__perf--down";
});

const accountTransactions = computed(
	() => accountTransactionsQuery.data.value ?? [],
);

const transactionsError = computed(
	() => accountTransactionsQuery.error.value?.message || "",
);

const isLoadingTransactions = computed(
	() =>
		accountTransactionsQuery.isPending.value ||
		accountTransactionsQuery.isFetching.value,
);

const pageError = computed(() => accountError.value || referenceError.value);

const totalReturnClass = computed(() => {
	const delta = portfolio.value?.total_return_minor;
	if (delta === undefined || delta === null) {
		return "";
	}
	return delta >= 0
		? "investments-header__perf--up"
		: "investments-header__perf--down";
});

const cashDraft = ref("0.00");
watch(
	() => portfolio.value?.uninvested_cash_minor,
	(value) => {
		if (value === undefined) {
			return;
		}
		cashDraft.value = minorToDollars(value);
	},
	{ immediate: true },
);

const reconcilePending = ref(false);
const marketUpdatePending = ref(false);

const handleReconcile = async ({ uninvested_cash_minor, positions }) => {
	if (!portfolio.value) {
		return;
	}

	const resolvedCashMinor =
		uninvested_cash_minor ??
		portfolio.value.uninvested_cash_minor ??
		dollarsToMinor(cashDraft.value);

	reconcilePending.value = true;
	try {
		await api.investments.reconcile(accountId.value, {
			uninvested_cash_minor: resolvedCashMinor,
			positions,
		});
		await portfolioQuery.refetch();
		await investmentHistoryQuery.refetch();
	} finally {
		reconcilePending.value = false;
	}
};

const saveCash = async () => {
	if (reconcilePending.value || !portfolio.value) {
		return;
	}
	const desired = dollarsToMinor(cashDraft.value);
	const positions = (portfolio.value.positions || []).map((p) => ({
		ticker: p.ticker,
		quantity: p.quantity,
		avg_cost_minor: p.avg_cost_minor,
	}));

	await handleReconcile({ uninvested_cash_minor: desired, positions });
};

const handleMarketUpdate = async () => {
	marketUpdatePending.value = true;
	try {
		await api.investments.triggerMarketUpdate();
		await portfolioQuery.refetch();
		await investmentHistoryQuery.refetch();
	} finally {
		marketUpdatePending.value = false;
	}
};

const createTransactionMutation = useMutation({
	mutationFn: (payload) => api.transactions.create(payload),
});

const updateTransactionMutation = useMutation({
	mutationFn: ({ concept_id: conceptId, ...payload }) =>
		api.transactions.update(conceptId, payload),
});

const deleteTransactionMutation = useMutation({
	mutationFn: (conceptId) => api.transactions.delete(conceptId),
});

const isCreatingTransaction = computed(
	() => createTransactionMutation.isPending.value,
);

const handleCreateTransaction = async (payload, resolve, reject) => {
	try {
		await createTransactionMutation.mutateAsync(payload);
		resolve();
	} catch (error) {
		reject(error);
	}
};

const handleUpdateTransaction = async (payload, resolve, reject) => {
	try {
		await updateTransactionMutation.mutateAsync(payload);
		resolve();
	} catch (error) {
		reject(error);
	}
};

const handleDeleteTransaction = async (tx, resolve, reject) => {
	try {
		await deleteTransactionMutation.mutateAsync(tx.concept_id);
		resolve();
	} catch (error) {
		reject(error);
	}
};

const valuationAsOf = ref(todayISO());
const valuationTarget = ref("");
const valuationError = ref("");

watch(
	() => valuationModalOpen.value,
	(isOpen) => {
		if (!isOpen) {
			valuationError.value = "";
			return;
		}

		valuationError.value = "";
		valuationTarget.value = "";

		const asOf = route.query?.asOf;
		const fallback = todayISO();
		if (typeof asOf === "string" && isValidDateInput(asOf)) {
			valuationAsOf.value = asOf;
		} else {
			valuationAsOf.value = fallback;
		}
	},
	{ immediate: true },
);

const valuationBaselineQuery = useQuery({
	queryKey: computed(() => [
		"accounts",
		accountId.value,
		"history",
		valuationAsOf.value,
		valuationAsOf.value,
		"all",
	]),
	queryFn: () =>
		api.accounts.getHistory(
			accountId.value,
			valuationAsOf.value,
			valuationAsOf.value,
			"all",
		),
	enabled: computed(
		() =>
			valuationModalOpen.value &&
			!!accountId.value &&
			isTangible.value &&
			isValidDateInput(valuationAsOf.value),
	),
	refetchOnWindowFocus: false,
});

const valuationBaselineError = computed(
	() => valuationBaselineQuery.error.value?.message || "",
);

const valuationBaselineMinor = computed(() => {
	const points = valuationBaselineQuery.data.value || [];
	const first = points[0];
	if (!first || typeof first.balance_minor !== "number") {
		return null;
	}
	return first.balance_minor;
});

watch(
	() => valuationBaselineMinor.value,
	(value) => {
		if (!valuationModalOpen.value) {
			return;
		}
		if (value === null || value === undefined) {
			return;
		}
		if (valuationTarget.value) {
			return;
		}
		valuationTarget.value = minorToDollars(value);
	},
	{ immediate: true },
);

const valuationTargetMinor = computed(() =>
	dollarsInputToMinor(valuationTarget.value),
);

const valuationDeltaMinor = computed(() => {
	if (valuationBaselineMinor.value === null) {
		return null;
	}
	if (valuationTargetMinor.value === null) {
		return null;
	}
	return valuationTargetMinor.value - valuationBaselineMinor.value;
});

const valuationBaselineLabel = computed(() => {
	if (valuationBaselineMinor.value === null) {
		return "—";
	}
	return formatAmount(valuationBaselineMinor.value);
});

const valuationDeltaLabel = computed(() => {
	if (valuationDeltaMinor.value === null) {
		return "";
	}
	const delta = valuationDeltaMinor.value;
	const sign = delta >= 0 ? "+" : "";
	return `${sign}${formatAmount(delta)}`;
});

const valuationMutation = useMutation({
	mutationFn: (payload) => api.transactions.create(payload),
});

const valuationSubmitting = computed(() => valuationMutation.isPending.value);

const valuationSubmitDisabled = computed(() => {
	if (valuationSubmitting.value) {
		return true;
	}
	if (!valuationModalOpen.value) {
		return true;
	}
	if (!accountId.value || !isTangible.value) {
		return true;
	}
	if (!isValidDateInput(valuationAsOf.value)) {
		return true;
	}
	if (valuationTargetMinor.value === null || valuationTargetMinor.value < 0) {
		return true;
	}
	if (valuationBaselineMinor.value === null) {
		return true;
	}
	return valuationDeltaMinor.value === 0;
});

const submitValuation = async () => {
	valuationError.value = "";
	if (!accountId.value) {
		return;
	}
	if (!isValidDateInput(valuationAsOf.value)) {
		valuationError.value = "Enter a valid as-of date (YYYY-MM-DD).";
		return;
	}
	if (valuationTargetMinor.value === null) {
		valuationError.value = "Enter a valid valuation amount.";
		return;
	}
	if (valuationTargetMinor.value < 0) {
		valuationError.value = "Valuation must be non-negative.";
		return;
	}
	if (valuationBaselineMinor.value === null) {
		valuationError.value = "Unable to load the current value for that date.";
		return;
	}
	if (valuationDeltaMinor.value === null || valuationDeltaMinor.value === 0) {
		valuationError.value =
			"Valuation matches current value; no adjustment needed.";
		return;
	}

	try {
		await valuationMutation.mutateAsync({
			transaction_date: valuationAsOf.value,
			account_id: accountId.value,
			category_id: "balance_adjustment",
			amount_minor: valuationDeltaMinor.value,
			memo: "Valuation update",
			status: "cleared",
		});
		navigateToBase();
	} catch (error) {
		valuationError.value = error?.message || "Failed to update valuation.";
	}
};

const formatPercent = (value) => {
	if (value === null || value === undefined) {
		return "—";
	}
	const numeric = Number(value);
	if (!Number.isFinite(numeric)) {
		return "—";
	}
	return `${numeric.toFixed(2)}%`;
};

const detailRows = computed(() => {
	const details = account.value?.details;
	if (!details) {
		return [];
	}

	const rows = [];

	if (
		details.interest_rate_apy !== undefined &&
		details.interest_rate_apy !== null
	) {
		rows.push({
			label: "Interest (APY)",
			value: formatPercent(details.interest_rate_apy),
		});
	}
	if (details.apr !== undefined && details.apr !== null) {
		rows.push({ label: "APR", value: formatPercent(details.apr) });
	}
	if (
		details.cash_advance_apr !== undefined &&
		details.cash_advance_apr !== null
	) {
		rows.push({
			label: "Cash advance APR",
			value: formatPercent(details.cash_advance_apr),
		});
	}
	if (details.card_type) {
		rows.push({ label: "Network", value: String(details.card_type) });
	}
	if (details.term_end_date) {
		rows.push({ label: "Term end", value: String(details.term_end_date) });
	}
	if (
		details.early_withdrawal_penalty !== undefined &&
		details.early_withdrawal_penalty !== null
	) {
		rows.push({
			label: "Early withdrawal penalty",
			value: details.early_withdrawal_penalty ? "Yes" : "No",
		});
	}
	if (
		details.initial_principal_minor !== undefined &&
		details.initial_principal_minor !== null
	) {
		rows.push({
			label: "Original principal",
			value: formatAmount(details.initial_principal_minor),
		});
	}
	if (details.mortgage_escrow_details) {
		rows.push({
			label: "Escrow notes",
			value: String(details.mortgage_escrow_details),
		});
	}
	if (details.asset_name) {
		rows.push({ label: "Asset", value: String(details.asset_name) });
	}
	if (
		details.acquisition_cost_minor !== undefined &&
		details.acquisition_cost_minor !== null
	) {
		rows.push({
			label: "Cost basis",
			value: formatAmount(details.acquisition_cost_minor),
		});
	}
	if (details.tax_classification) {
		rows.push({
			label: "Tax classification",
			value: String(details.tax_classification),
		});
	}
	if (
		details.is_self_directed !== undefined &&
		details.is_self_directed !== null
	) {
		rows.push({
			label: "Self-directed",
			value: details.is_self_directed ? "Yes" : "No",
		});
	}
	if (
		details.risk_free_sweep_rate !== undefined &&
		details.risk_free_sweep_rate !== null
	) {
		rows.push({
			label: "Sweep fund rate",
			value: formatPercent(details.risk_free_sweep_rate),
		});
	}

	return rows;
});
</script>

<style scoped>
.account-detail-page__header {
  align-items: flex-start;
}

.account-detail-page__headline {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.account-detail-page__headline .page-label {
  margin: 0;
}

.account-detail-page__headline .investments-header__value {
  margin: 0;
}

.account-detail-page__headline .investments-header__perf {
  margin: 0;
}

.account-detail-page__actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.account-detail-page__hero-row {
  width: 100vw;
  margin-left: calc(50% - 50vw);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 1.5rem;
  align-items: start;
  margin-top: 1.25rem;
  padding-right: 2rem;
}

.account-detail-page__hero-aside {
  display: flex;
  flex-direction: column;
}

.account-detail-page__cash-card {
  margin-top: 1rem;
}

.account-detail-page__cash-help {
  margin-top: 0.5rem;
}

.account-detail-page__holdings {
  margin-top: 1.25rem;
}

@media (max-width: 960px) {
  .account-detail-page__hero-row {
    grid-template-columns: 1fr;
    padding-right: 0;
  }
}

@media (max-width: 720px) {
  .account-detail-page__header {
    flex-direction: column;
    align-items: flex-start;
  }

  .account-detail-page__actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .account-detail-page__hero-row {
    margin-top: 1rem;
  }
}
</style>
