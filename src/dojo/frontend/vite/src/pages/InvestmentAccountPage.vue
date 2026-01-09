<template>
  <section class="route-page route-page--active investments-page" data-route="investments">
    <header class="investments-header">
      <div>
        <h1 class="page-label investments-header__title" v-if="accountName">{{ accountName }}</h1>
      </div>

      <div class="investments-header__actions">
        <button
          type="button"
          class="button button--secondary"
          data-testid="investment-market-update"
          :disabled="marketUpdatePending"
          @click="handleMarketUpdate"
        >
          {{ marketUpdatePending ? "Updating…" : "Update prices" }}
        </button>
      </div>
    </header>

    <div class="investments-layout">
      <main>
        <div class="investments-chart investments-card">
          <PortfolioChart
            data-testid="investment-chart"
            :series="chartSeries"
            :interval="rangeLabel"
            :loading="historyLoading"
            :showPercentChange="true"
            @change-interval="setRangeLabel"
          />
        </div>

        <HoldingsTable
          class="investments-holdings"
          data-testid="investment-holdings"
          :positions="portfolio?.positions || []"
          :pending="reconcilePending"
          @reconcile="handleReconcile"
        />
      </main>

      <aside>
        <div class="investments-card">
          <p class="investments-card__title">Details</p>
          <dl class="investments-kv">
            <dt>NAV</dt>
            <dd>{{ formatAmount(portfolio?.nav_minor) }}</dd>
            <dt>Holdings</dt>
            <dd>{{ formatAmount(portfolio?.holdings_value_minor) }}</dd>
            <dt>Cash</dt>
            <dd>{{ formatAmount(portfolio?.uninvested_cash_minor) }}</dd>
            <dt>Cost basis</dt>
            <dd>{{ formatAmount(portfolio?.ledger_cash_minor) }}</dd>
            <dt>Total return</dt>
            <dd :class="totalReturnClass">
              {{ formatAmount(portfolio?.total_return_minor) }}
            </dd>
            <dt>Account type</dt>
            <dd>Investment</dd>
          </dl>
        </div>

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
      </aside>
    </div>
  </section>
</template>

<script setup>
import { useQuery } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import HoldingsTable from "../components/investments/HoldingsTable.vue";
import PortfolioChart from "../components/investments/PortfolioChart.vue";
import { api } from "../services/api.js";
import {
	dollarsToMinor,
	formatAmount,
	minorToDollars,
} from "../services/format.js";
import { useChartRange } from "../utils/chartRange.js";

const route = useRoute();
const accountId = computed(() => route.params.accountId);

const { rangeLabel, range, setRangeLabel } = useChartRange();

const accountsQuery = useQuery({
	queryKey: ["accounts"],
	queryFn: api.accounts.list,
});

const portfolioQuery = useQuery({
	queryKey: computed(() => ["investment-account", accountId.value]),
	queryFn: () => api.investments.getAccount(accountId.value),
	enabled: computed(() => Boolean(accountId.value)),
});

const historyQuery = useQuery({
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
	enabled: computed(() => Boolean(accountId.value)),
});

const portfolio = computed(() => portfolioQuery.data.value);

const chartSeries = computed(() =>
	(historyQuery.data.value || []).map((point) => ({
		date: point.market_date,
		value_minor: point.nav_minor,
	})),
);

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

const accountName = computed(() => {
	const accounts = accountsQuery.data.value || [];
	const record = accounts.find((acct) => acct.account_id === accountId.value);
	const label = record?.name || portfolio.value?.account_id;
	if (!label) {
		return "";
	}
	return String(label).toUpperCase();
});

const totalReturnClass = computed(() => {
	const delta = portfolio.value?.total_return_minor;
	if (delta === undefined || delta === null) {
		return "";
	}
	return delta >= 0
		? "investments-header__perf--up"
		: "investments-header__perf--down";
});

const historyLoading = computed(
	() => historyQuery.isPending.value || historyQuery.isFetching.value,
);

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
		await historyQuery.refetch();
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
		await historyQuery.refetch();
	} finally {
		marketUpdatePending.value = false;
	}
};
</script>
