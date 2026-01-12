<template>
  <section
    class="route-page route-page--active dashboard-page"
    id="dashboard-page"
    data-route="dashboard"
    data-testid="dashboard-page"
  >
    <header class="dashboard-page__header">
      <div class="dashboard-page__net-worth">
        <span class="dashboard-page__label">NET WORTH</span>
        <h1 class="dashboard-page__value" data-testid="dashboard-net-worth-value">
          {{ headerValueLabel }}
        </h1>
        <p
          class="dashboard-page__change"
          :class="headerIsPositive ? 'dashboard-page__change--positive' : 'dashboard-page__change--negative'"
          data-testid="dashboard-net-worth-change"
        >
          {{ headerChangeLabel }} ({{ headerChangePercentLabel }})
        </p>
      </div>
    </header>

    <div
      class="dashboard-chart"
      ref="chartRef"
      data-testid="dashboard-net-worth-chart"
      @pointerdown="handlePointerDown"
      @pointermove="handlePointerMove"
      @pointerup="handlePointerUp"
      @pointerleave="handlePointerLeave"
    >
      <svg
        class="dashboard-chart__svg"
        :viewBox="`0 0 ${viewWidth} ${viewHeight}`"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="dashboardGradientPositive" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="var(--success)" stop-opacity="0.4" />
            <stop offset="70%" stop-color="var(--success)" stop-opacity="0.1" />
            <stop offset="100%" stop-color="var(--bg)" stop-opacity="0" />
          </linearGradient>
          <linearGradient id="dashboardGradientNegative" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="var(--danger)" stop-opacity="0.4" />
            <stop offset="70%" stop-color="var(--danger)" stop-opacity="0.1" />
            <stop offset="100%" stop-color="var(--bg)" stop-opacity="0" />
          </linearGradient>
        </defs>

        <path
          v-if="linePath"
          :d="areaPath"
          class="dashboard-chart__area"
          :style="{
            fill: `url(#${chartStateIsPositive ? 'dashboardGradientPositive' : 'dashboardGradientNegative'})`,
          }"
        />
        <path
          v-if="linePath"
          :d="linePath"
          class="dashboard-chart__line"
          :style="{ stroke: chartStateIsPositive ? 'var(--success)' : 'var(--danger)' }"
        />

        <line
          v-if="dragStartData"
          :x1="dragStartData.x"
          y1="0"
          :x2="dragStartData.x"
          :y2="viewHeight"
          class="dashboard-chart__drag-line"
        />

        <rect
          v-if="dragStartData && hoverData"
          :x="Math.min(dragStartData.x, hoverX)"
          y="0"
          :width="Math.abs(hoverX - dragStartData.x)"
          :height="viewHeight"
          class="dashboard-chart__drag-area"
        />

        <line
          v-if="hoverData"
          :x1="hoverX"
          y1="0"
          :x2="hoverX"
          :y2="viewHeight"
          class="dashboard-chart__cursor"
        />

        <circle
          v-if="hoverData"
          :cx="hoverX"
          :cy="hoverY"
          r="6"
          fill="var(--surface)"
          :stroke="chartStateIsPositive ? 'var(--success)' : 'var(--danger)'"
          stroke-width="3"
        />
      </svg>

      <div v-if="hoverData" class="dashboard-chart__tooltip" :style="tooltipStyle">
        <template v-if="dragStartData">
          <span class="dashboard-chart__tooltip-range">
            {{ formatDateShort(dragStartData.date) }} – {{ formatDateShort(hoverData.date) }}
          </span>
          <div class="dashboard-chart__tooltip-rows">
            <div class="dashboard-chart__tooltip-row">
              <span class="u-muted">Start</span>
              <span>{{ formatMinor(dragStartData.value_minor) }}</span>
            </div>
            <div class="dashboard-chart__tooltip-row">
              <span class="u-muted">End</span>
              <span>{{ formatMinor(hoverData.value_minor) }}</span>
            </div>
          </div>
          <div
            class="dashboard-chart__tooltip-delta"
            :class="tooltipChangeMinor >= 0 ? 'dashboard-page__change--positive' : 'dashboard-page__change--negative'"
          >
            <strong>{{ formatSignedMinor(tooltipChangeMinor) }}</strong>
            <span>({{ tooltipPercentLabel }}%)</span>
          </div>
        </template>

        <template v-else>
          <span class="dashboard-chart__tooltip-range">{{ formatDate(hoverData.date) }}</span>
          <div class="dashboard-chart__tooltip-delta">
            <strong>{{ formatMinor(hoverData.value_minor) }}</strong>
          </div>
        </template>
      </div>

      <div v-if="isLoadingHistory" class="dashboard-chart__loading u-muted">Loading net worth…</div>
      <div v-else-if="historyError" class="dashboard-chart__loading form-panel__error">{{ historyError }}</div>
    </div>

    <nav class="dashboard-intervals" aria-label="Net worth interval" data-testid="dashboard-intervals">
      <button
        v-for="interval in intervals"
        :key="interval"
        type="button"
        class="dashboard-intervals__button"
        :class="{ 'dashboard-intervals__button--active': selectedInterval === interval }"
        @click="changeInterval(interval)"
        :data-testid="`dashboard-interval-${interval}`"
      >
        {{ interval }}
      </button>
    </nav>

    <div class="dashboard-grid">
      <article class="dashboard-panel" data-testid="dashboard-accounts">
        <header class="dashboard-panel__header">
          <h2 class="dashboard-panel__title">Accounts</h2>
          <RouterLink to="/accounts" class="button button--tertiary">View all</RouterLink>
        </header>

        <p v-if="isLoadingAccounts" class="u-muted">Loading accounts…</p>
        <p v-else-if="accountsError" class="form-panel__error">{{ accountsError }}</p>
        <div v-else class="dashboard-account-list">
          <RouterLink
            v-for="acct in topAccounts"
            :key="acct.account_id"
            :to="`/accounts/${acct.account_id}`"
            class="dashboard-account-row"
            :data-account-id="acct.account_id"
          >
            <div>
              <div class="dashboard-account-row__name">{{ acct.name }}</div>
              <div class="dashboard-account-row__meta u-muted">{{ acct.account_class.replace(/_/g, ' ') }}</div>
            </div>
            <div class="dashboard-account-row__balance">{{ formatMinor(acct.current_balance_minor || 0) }}</div>
          </RouterLink>
        </div>
      </article>

      <article class="dashboard-panel" data-testid="dashboard-budget-watchlist">
        <header class="dashboard-panel__header">
          <h2 class="dashboard-panel__title">Budget Watchlist</h2>
          <RouterLink to="/budgets" class="button button--tertiary">Edit list</RouterLink>
        </header>

        <p v-if="isLoadingBudgets" class="u-muted">Loading budgets…</p>
        <p v-else-if="budgetsError" class="form-panel__error">{{ budgetsError }}</p>
        <div v-else class="dashboard-budget-list">
          <div
            v-for="cat in watchlistCategories"
            :key="cat.category_id"
            class="dashboard-budget-item"
            :class="{ 'dashboard-budget-item--empty': isWatchlistEmpty(cat) }"
          >
            <div class="dashboard-budget-item__header">
              <span>{{ cat.name }}</span>
            </div>
            <div class="dashboard-budget-item__track">
              <div
                class="dashboard-budget-item__fill"
                :style="{ width: `${watchlistProgress(cat)}%` }"
              ></div>
            </div>
            <div class="dashboard-budget-item__footer">
              <template v-if="isWatchlistEmpty(cat)">
                <span class="dashboard-budget-item__warning">Unfunded / Overspent</span>
              </template>
              <template v-else>
                <strong>{{ formatMinor(cat.available_minor) }}</strong>
                <span class="u-muted">of {{ formatMinor(cat.allocated_minor) }} budgeted</span>
              </template>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { useQuery } from "@tanstack/vue-query";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { systemCategoryIds } from "../constants.js";
import { api } from "../services/api.js";
import { currentMonthStartISO, formatAmount } from "../services/format.js";

const viewWidth = 1000;
const viewHeight = 360;

const intervals = ["1D", "1W", "1M", "3M", "YTD", "1Y", "5Y", "Max"];
const selectedInterval = ref("1M");

const chartRef = ref(null);
const chartPixelWidth = ref(0);

const historyQuery = useQuery({
	queryKey: computed(() => ["netWorth", "history", selectedInterval.value]),
	queryFn: () => api.netWorth.history(selectedInterval.value),
	refetchOnWindowFocus: false,
});

const accountsQuery = useQuery({
	queryKey: ["accounts"],
	queryFn: api.accounts.list,
	refetchOnWindowFocus: false,
});

const monthStart = currentMonthStartISO();
const budgetsQuery = useQuery({
	queryKey: ["budget-categories", monthStart],
	queryFn: () => api.budgets.categories(monthStart),
	refetchOnWindowFocus: false,
});

const isLoadingHistory = computed(
	() => historyQuery.isPending.value || historyQuery.isFetching.value,
);
const historyError = computed(() => historyQuery.error.value?.message || "");

const series = computed(() => {
	const data = historyQuery.data.value ?? [];
	return data.map((point) => ({
		date: point.date,
		value_minor: point.value_minor,
	}));
});

const headerValueLabel = computed(() => {
	if (!series.value.length) return "—";
	return formatAmount(series.value[series.value.length - 1].value_minor);
});

const headerChangeMinor = computed(() => {
	if (series.value.length < 2) return 0;
	return (
		series.value[series.value.length - 1].value_minor -
		series.value[0].value_minor
	);
});

const headerIsPositive = computed(() => headerChangeMinor.value >= 0);

const headerChangeLabel = computed(() =>
	formatSignedMinor(headerChangeMinor.value),
);

const headerChangePercentLabel = computed(() => {
	if (series.value.length < 2) return "0.00%";
	const start = series.value[0].value_minor;
	const change = headerChangeMinor.value;
	if (start === 0) return "0.00%";
	const pct = (change / Math.abs(start)) * 100;
	return `${pct.toFixed(2)}%`;
});

const formatMinor = (minor) => formatAmount(minor || 0);
const formatSignedMinor = (minor) =>
	(minor >= 0 ? "+" : "") + formatMinor(minor);

const formatDate = (isoStr) => {
	const d = new Date(isoStr);
	return d.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
		year: "numeric",
	});
};

const formatDateShort = (isoStr) => {
	const d = new Date(isoStr);
	return d.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
	});
};

const dataPoints = computed(() => {
	const data = series.value;
	if (!data.length) return [];

	const values = data.map((d) => d.value_minor);
	const minVal = Math.min(...values);
	const maxVal = Math.max(...values);
	const range = maxVal - minVal || 1;
	const padding = range * 0.15;

	return data.map((d, i) => {
		const x = (i / (data.length - 1)) * viewWidth;
		const y =
			viewHeight -
			((d.value_minor - (minVal - padding)) / (range + padding * 2)) *
				viewHeight;
		return { x, y, ...d };
	});
});

const linePath = computed(() => {
	const pts = dataPoints.value;
	if (!pts.length) return "";
	return pts
		.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)},${p.y.toFixed(2)}`)
		.join(" ");
});

const areaPath = computed(() => {
	if (!linePath.value) return "";
	return `${linePath.value} L ${viewWidth},${viewHeight} L 0,${viewHeight} Z`;
});

const hoverData = ref(null);
const hoverX = ref(0);
const hoverY = ref(0);

const dragStartData = ref(null);
const isDragging = ref(false);

const chartStateIsPositive = computed(() => {
	if (dragStartData.value && hoverData.value) {
		return hoverData.value.value_minor - dragStartData.value.value_minor >= 0;
	}
	return headerIsPositive.value;
});

const tooltipChangeMinor = computed(() => {
	if (!dragStartData.value || !hoverData.value) return 0;
	return hoverData.value.value_minor - dragStartData.value.value_minor;
});

const tooltipPercentLabel = computed(() => {
	if (!dragStartData.value || !hoverData.value) return "0.00";
	const start = dragStartData.value.value_minor;
	if (start === 0) return "0.00";
	const change = tooltipChangeMinor.value;
	return ((change / Math.abs(start)) * 100).toFixed(2);
});

const tooltipStyle = computed(() => {
	if (!chartPixelWidth.value) return {};
	const left = (hoverX.value / viewWidth) * chartPixelWidth.value;
	const ratio = hoverX.value / viewWidth;
	if (ratio > 0.85) {
		return { left: `${left}px`, transform: "translateX(-100%)" };
	}
	if (ratio < 0.15) {
		return { left: `${left}px`, transform: "translateX(0)" };
	}
	return { left: `${left}px`, transform: "translateX(-50%)" };
});

let pendingMove = null;
let rafId = null;

const updateHoverFromEvent = (evt) => {
	const el = chartRef.value;
	if (!el || !dataPoints.value.length) return;
	const rect = el.getBoundingClientRect();
	const rawX = evt.clientX - rect.left;
	if (rawX < 0 || rawX > rect.width) return;

	const scaledX = (rawX / rect.width) * viewWidth;
	const index = Math.round(
		(scaledX / viewWidth) * (dataPoints.value.length - 1),
	);
	const point = dataPoints.value[index];
	if (!point) return;

	hoverX.value = point.x;
	hoverY.value = point.y;
	hoverData.value = { date: point.date, value_minor: point.value_minor };
};

const scheduleHoverUpdate = (evt) => {
	pendingMove = evt;
	if (rafId) return;
	rafId = window.requestAnimationFrame(() => {
		rafId = null;
		if (pendingMove) {
			updateHoverFromEvent(pendingMove);
			pendingMove = null;
		}
	});
};

const handlePointerDown = (evt) => {
	if (!dataPoints.value.length) return;
	isDragging.value = true;
	updateHoverFromEvent(evt);
	if (hoverData.value) {
		dragStartData.value = {
			date: hoverData.value.date,
			value_minor: hoverData.value.value_minor,
			x: hoverX.value,
			y: hoverY.value,
		};
	}
	chartRef.value?.setPointerCapture?.(evt.pointerId);
};

const handlePointerMove = (evt) => {
	scheduleHoverUpdate(evt);
};

const handlePointerUp = (evt) => {
	isDragging.value = false;
	dragStartData.value = null;
	chartRef.value?.releasePointerCapture?.(evt.pointerId);
};

const handlePointerLeave = () => {
	if (!isDragging.value) {
		hoverData.value = null;
	}
};

const measureChart = () => {
	const el = chartRef.value;
	if (!el) return;
	chartPixelWidth.value = el.getBoundingClientRect().width;
};

let resizeObserver;

onMounted(() => {
	measureChart();
	resizeObserver = new ResizeObserver(() => measureChart());
	if (chartRef.value) {
		resizeObserver.observe(chartRef.value);
	}
	window.addEventListener("resize", measureChart);
});

onBeforeUnmount(() => {
	window.removeEventListener("resize", measureChart);
	resizeObserver?.disconnect?.();
	if (rafId) {
		window.cancelAnimationFrame(rafId);
	}
});

const changeInterval = (interval) => {
	selectedInterval.value = interval;
	hoverData.value = null;
	dragStartData.value = null;
};

const isLoadingAccounts = computed(
	() => accountsQuery.isPending.value || accountsQuery.isFetching.value,
);
const accountsError = computed(() => accountsQuery.error.value?.message || "");
const topAccounts = computed(() => {
	const accounts = accountsQuery.data.value ?? [];
	return [...accounts]
		.sort(
			(a, b) => (b.current_balance_minor || 0) - (a.current_balance_minor || 0),
		)
		.slice(0, 8);
});

const isLoadingBudgets = computed(
	() => budgetsQuery.isPending.value || budgetsQuery.isFetching.value,
);
const budgetsError = computed(() => budgetsQuery.error.value?.message || "");

const watchlistCategories = computed(() => {
	const categories = budgetsQuery.data.value ?? [];
	return categories
		.filter((cat) => !systemCategoryIds.has(cat.category_id))
		.slice(0, 6);
});

const isWatchlistEmpty = (category) =>
	(category.allocated_minor || 0) === 0 || (category.available_minor || 0) <= 0;

const watchlistProgress = (category) => {
	const allocated = category.allocated_minor || 0;
	const available = category.available_minor || 0;
	if (allocated <= 0) return 0;
	const pct = (available / allocated) * 100;
	return Math.max(0, Math.min(100, pct));
};
</script>

<style scoped>
.dashboard-page__header {
  margin-bottom: 1rem;
  text-align: left;
}

.dashboard-page__label {
  font-family: var(--font-mono);
  color: var(--muted);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dashboard-page__value {
  font-size: 3rem;
  font-weight: 700;
  line-height: 1;
  margin: 0.5rem 0;
  font-variant-numeric: tabular-nums;
}

.dashboard-page__change {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
  margin: 0;
}

.dashboard-page__change--positive {
  color: var(--success);
}

.dashboard-page__change--negative {
  color: var(--danger);
}

.dashboard-chart {
  position: relative;
  width: 100vw;
  margin-left: 50%;
  transform: translateX(-50%);
  height: 360px;
  overflow: hidden;
  cursor: crosshair;
  user-select: none;
  -webkit-user-select: none;
  border-bottom: 1px solid var(--border);
}

.dashboard-chart__svg {
  width: 100%;
  height: 100%;
  display: block;
}

.dashboard-chart__line {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.dashboard-chart__area {
  opacity: 0.6;
}

.dashboard-chart__cursor {
  stroke: var(--muted);
  stroke-width: 1;
  stroke-dasharray: 4;
}

.dashboard-chart__drag-line {
  stroke: var(--text);
  stroke-width: 1;
  opacity: 0.5;
}

.dashboard-chart__drag-area {
  fill: var(--text);
  opacity: 0.03;
}

.dashboard-chart__tooltip {
  position: absolute;
  top: 20px;
  background: var(--surface);
  border: var(--border-thick);
  padding: 0.75rem 1rem;
  pointer-events: none;
  z-index: 10;
  box-shadow: var(--shadow-hard);
  min-width: 200px;
}

.dashboard-chart__tooltip-range {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 0.5rem;
  display: block;
}

.dashboard-chart__tooltip-rows {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.dashboard-chart__tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.dashboard-chart__tooltip-delta {
  border-top: 1px solid var(--border);
  padding-top: 0.5rem;
  font-family: var(--font-mono);
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.dashboard-chart__loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(253, 252, 251, 0.85);
}

.dashboard-intervals {
  display: flex;
  justify-content: flex-start;
  gap: 0.5rem;
  margin: 1rem 0 2rem;
  flex-wrap: wrap;
}

.dashboard-intervals__button {
  background: none;
  border: 1px solid transparent;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  padding: 0.35rem 0.75rem;
  cursor: pointer;
  color: var(--muted);
  border-radius: 4px;
  transition: all 0.2s ease;
}

.dashboard-intervals__button:hover {
  color: var(--text);
  background-color: var(--stone-50);
  border-color: var(--border);
}

.dashboard-intervals__button--active {
  background-color: var(--text);
  color: var(--bg);
}

.dashboard-intervals__button--active:hover {
  background-color: var(--text);
  color: var(--bg);
  border-color: var(--text);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 3fr 2fr;
  }
}

.dashboard-panel {
  background: var(--surface);
  border: var(--border-thick);
  padding: 1.5rem;
}

.dashboard-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.75rem;
}

.dashboard-panel__title {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

.dashboard-account-list {
  display: flex;
  flex-direction: column;
}

.dashboard-account-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 0;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
  color: inherit;
}

.dashboard-account-row:hover {
  background-color: var(--stone-50);
  padding-left: 0.5rem;
  padding-right: 0.5rem;
  margin-left: -0.5rem;
  margin-right: -0.5rem;
}

.dashboard-account-row:last-child {
  border-bottom: none;
}

.dashboard-account-row__name {
  font-weight: 600;
}

.dashboard-account-row__meta {
  font-size: 0.8rem;
  text-transform: uppercase;
}

.dashboard-account-row__balance {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 1.1rem;
}

.dashboard-budget-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.dashboard-budget-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dashboard-budget-item__header {
  font-size: 0.95rem;
  font-weight: 600;
}

.dashboard-budget-item__track {
  height: 10px;
  background-color: var(--stone-50);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.dashboard-budget-item__fill {
  height: 100%;
  background-color: var(--primary);
  border-radius: 4px;
  transition: width 0.2s ease;
}

.dashboard-budget-item__footer {
  display: flex;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.dashboard-budget-item--empty .dashboard-budget-item__track {
  border-color: var(--danger);
  background-color: #fff5f5;
}

.dashboard-budget-item--empty .dashboard-budget-item__fill {
  width: 0 !important;
}

.dashboard-budget-item__warning {
  color: var(--danger);
  font-weight: 600;
}
</style>
