<template>
  <section
    class="route-page route-page--active dashboard-page"
    id="dashboard-page"
    data-route="dashboard"
    data-testid="dashboard-page"
  >
    <div class="dashboard-layout">
      <div class="dashboard-column dashboard-column--stack">
        <article class="dashboard-card dashboard-card--net-worth" data-testid="dashboard-net-worth">
          <header class="dashboard-card__header">
            <p class="dashboard-card__label">Net worth</p>
          </header>
          <div class="net-worth-card__figures">
            <div>
              <h1 class="dashboard-card__headline">{{ headerValueLabel }}</h1>
              <p
                class="dashboard-card__change"
                :class="headerIsPositive ? 'dashboard-card__change--positive' : 'dashboard-card__change--negative'"
                data-testid="dashboard-net-worth-change"
              >
                {{ headerChangeLabel }} ({{ headerChangePercentLabel }})
              </p>
            </div>
            <p class="dashboard-card__as-of">Range: {{ selectedInterval }}</p>
          </div>

          <div class="net-worth-chart">
            <div
              class="net-worth-chart__surface"
              ref="chartRef"
              data-testid="dashboard-net-worth-chart"
              @pointerdown="handlePointerDown"
              @pointermove="handlePointerMove"
              @pointerup="handlePointerUp"
              @pointerleave="handlePointerLeave"
            >
              <svg
                class="net-worth-chart__svg"
                :viewBox="`0 0 ${viewWidth} ${viewHeight}`"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="netWorthGradientPositive" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stop-color="var(--success)" stop-opacity="0.4" />
                    <stop offset="70%" stop-color="var(--success)" stop-opacity="0.1" />
                    <stop offset="100%" stop-color="var(--bg)" stop-opacity="0" />
                  </linearGradient>
                  <linearGradient id="netWorthGradientNegative" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stop-color="var(--danger)" stop-opacity="0.4" />
                    <stop offset="70%" stop-color="var(--danger)" stop-opacity="0.1" />
                    <stop offset="100%" stop-color="var(--bg)" stop-opacity="0" />
                  </linearGradient>
                </defs>

                <path
                  v-if="linePath"
                  :d="areaPath"
                  class="net-worth-chart__area"
                  :style="{
                    fill: `url(#${chartStateIsPositive ? 'netWorthGradientPositive' : 'netWorthGradientNegative'})`,
                  }"
                />
                <path
                  v-if="linePath"
                  :d="linePath"
                  class="net-worth-chart__line"
                  :style="{ stroke: chartStateIsPositive ? 'var(--success)' : 'var(--danger)' }"
                />

                <line
                  v-if="dragStartData"
                  :x1="dragStartData.x"
                  y1="0"
                  :x2="dragStartData.x"
                  :y2="viewHeight"
                  class="net-worth-chart__drag-line"
                />

                <rect
                  v-if="dragStartData && hoverData"
                  :x="Math.min(dragStartData.x, hoverX)"
                  y="0"
                  :width="Math.abs(hoverX - dragStartData.x)"
                  :height="viewHeight"
                  class="net-worth-chart__drag-area"
                />

                <line
                  v-if="hoverData"
                  :x1="hoverX"
                  y1="0"
                  :x2="hoverX"
                  :y2="viewHeight"
                  class="net-worth-chart__cursor"
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

              <div v-if="hoverData" class="net-worth-chart__tooltip" :style="tooltipStyle">
                <template v-if="dragStartData">
                  <span class="net-worth-chart__tooltip-range">
                    {{ formatDateShort(dragStartData.date) }} – {{ formatDateShort(hoverData.date) }}
                  </span>
                  <div class="net-worth-chart__tooltip-rows">
                    <div class="net-worth-chart__tooltip-row">
                      <span class="u-muted">Start</span>
                      <span>{{ formatMinor(dragStartData.value_minor) }}</span>
                    </div>
                    <div class="net-worth-chart__tooltip-row">
                      <span class="u-muted">End</span>
                      <span>{{ formatMinor(hoverData.value_minor) }}</span>
                    </div>
                  </div>
                  <div
                    class="net-worth-chart__tooltip-delta"
                    :class="tooltipChangeMinor >= 0 ? 'dashboard-card__change--positive' : 'dashboard-card__change--negative'"
                  >
                    <strong>{{ formatSignedMinor(tooltipChangeMinor) }}</strong>
                    <span>({{ tooltipPercentLabel }}%)</span>
                  </div>
                </template>
                <template v-else>
                  <span class="net-worth-chart__tooltip-range">{{ formatDate(hoverData.date) }}</span>
                  <strong class="net-worth-chart__tooltip-value">{{ formatMinor(hoverData.value_minor) }}</strong>
                </template>
              </div>

              <div v-if="isLoadingHistory" class="net-worth-chart__loading u-muted">Loading net worth…</div>
              <div v-else-if="historyError" class="net-worth-chart__loading form-panel__error">{{ historyError }}</div>
            </div>
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
          <RouterLink to="/accounts" class="dashboard-card__footer-link">Details</RouterLink>
        </article>

        <article class="dashboard-card dashboard-card--list" data-testid="dashboard-accounts">
          <header class="dashboard-card__header">
            <div>
              <p class="dashboard-card__label">Account summary</p>
              <p class="dashboard-card__as-of">as of {{ accountSummaryDate }}</p>
            </div>
          </header>

          <p v-if="isLoadingAccounts" class="u-muted">Loading accounts…</p>
          <p v-else-if="accountsError" class="form-panel__error">{{ accountsError }}</p>
          <div v-else class="dashboard-list">
            <div
              v-for="acct in topAccounts"
              :key="acct.account_id"
              class="dashboard-row"
            >
              <div>
                <div class="dashboard-row__name">{{ acct.name }}</div>
                <div class="dashboard-row__meta u-muted">{{ acct.account_class.replace(/_/g, ' ') }}</div>
              </div>
              <div
                class="dashboard-row__value"
                :class="acct.current_balance_minor < 0 ? 'dashboard-row__value--negative' : 'dashboard-row__value--positive'"
              >
                {{ formatMinor(acct.current_balance_minor || 0) }}
              </div>
            </div>
          </div>
          <RouterLink to="/accounts" class="dashboard-card__footer-link">All assets &amp; liabilities</RouterLink>
        </article>

        <article class="dashboard-card dashboard-card--list" data-testid="dashboard-investments">
          <header class="dashboard-card__header">
            <div>
              <p class="dashboard-card__label">Investment summary</p>
              <p class="dashboard-card__as-of">Tracked accounts</p>
            </div>
          </header>

          <p v-if="isLoadingAccounts" class="u-muted">Loading investments…</p>
          <p v-else-if="investmentAccounts.length === 0" class="u-muted">No investment accounts yet.</p>
          <div v-else class="dashboard-list">
            <div
              v-for="acct in investmentAccounts"
              :key="acct.account_id"
              class="dashboard-row"
            >
              <div>
                <div class="dashboard-row__name">{{ acct.name }}</div>
                <div class="dashboard-row__meta u-muted">{{ acct.account_role === "tracking" ? "Tracking" : "On budget" }}</div>
              </div>
              <div class="dashboard-row__value dashboard-row__value--positive">
                {{ formatMinor(acct.current_balance_minor || 0) }}
              </div>
            </div>
          </div>
          <RouterLink to="/accounts" class="dashboard-card__footer-link">All investments</RouterLink>
        </article>
      </div>

      <div class="dashboard-column dashboard-column--center">
        <article class="dashboard-card dashboard-card--watchlist" data-testid="dashboard-budget-watchlist">
          <header class="dashboard-card__header">
            <p class="dashboard-card__label">Budget watch list</p>
          </header>

          <p v-if="isLoadingBudgets" class="u-muted">Loading budgets…</p>
          <p v-else-if="budgetsError" class="form-panel__error">{{ budgetsError }}</p>
          <div v-else class="budget-watchlist">
            <div
              v-for="cat in watchlistCategories"
              :key="cat.category_id"
              class="budget-watchlist__item"
            >
              <div class="budget-watchlist__row">
                <div>
                  <p class="budget-watchlist__name">{{ cat.name }}</p>
                  <p
                    class="budget-watchlist__status"
                    :class="budgetStatusClass(cat)"
                  >
                    {{ budgetStatusLabel(cat) }}
                  </p>
                </div>
                <span class="budget-watchlist__available">{{ formatMinor(Math.max(cat.available_minor || 0, 0)) }}</span>
              </div>
              <div class="budget-watchlist__bar">
                <div
                  class="budget-watchlist__fill"
                  :class="{ 'budget-watchlist__fill--danger': cat.available_minor < 0 }"
                  :style="{ width: `${watchlistProgress(cat)}%` }"
                ></div>
              </div>
              <div class="budget-watchlist__scale">
                <span>0</span>
                <span>{{ formatMinor(watchlistTarget(cat)) }}</span>
              </div>
            </div>
          </div>
          <RouterLink to="/budgets" class="dashboard-card__footer-link">All budgets</RouterLink>
        </article>
      </div>

      <div class="dashboard-column dashboard-column--stack">
        <article class="dashboard-card dashboard-card--bills">
          <header class="dashboard-card__header">
            <p class="dashboard-card__label">Bills &amp; goals</p>
          </header>

          <p v-if="isLoadingBudgets" class="u-muted">Loading bills…</p>
          <p v-else-if="budgetsError" class="form-panel__error">{{ budgetsError }}</p>
          <template v-else>
            <div
              v-for="section in billSections"
              :key="section.id"
              class="bills-card__section"
            >
              <h3 class="bills-card__title">{{ section.title }}</h3>
              <div v-if="section.items.length === 0" class="bills-card__empty u-muted">Nothing scheduled.</div>
              <div v-else class="bills-list">
                <div
                  v-for="item in section.items"
                  :key="item.id"
                  class="bills-row"
                >
                  <div class="bills-row__label">
                    <span>{{ item.name }}</span>
                    <small>due on {{ item.dueLabel }}</small>
                  </div>
                  <div class="bills-row__value">
                    <strong>{{ item.amountLabel }}</strong>
                    <span class="status-pill" :class="`status-pill--${item.status.variant}`">
                      <span class="status-pill__dot"></span>
                      {{ item.status.label }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </article>
      </div>
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
		const x = data.length === 1 ? 0 : (i / (data.length - 1)) * viewWidth;
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
	const maxIndex = Math.max(dataPoints.value.length - 1, 0);
	const index =
		maxIndex === 0 ? 0 : Math.round((scaledX / viewWidth) * maxIndex);
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
		.slice(0, 4);
});

const investmentAccounts = computed(() => {
	const accounts = accountsQuery.data.value ?? [];
	return accounts
		.filter((acct) => acct.account_class === "investment")
		.sort(
			(a, b) => (b.current_balance_minor || 0) - (a.current_balance_minor || 0),
		)
		.slice(0, 4);
});

const accountSummaryDate = computed(() => {
	const now = new Date();
	const mm = `${now.getMonth() + 1}`.padStart(2, "0");
	const dd = `${now.getDate()}`.padStart(2, "0");
	return `${mm}/${dd}`;
});

const isLoadingBudgets = computed(
	() => budgetsQuery.isPending.value || budgetsQuery.isFetching.value,
);
const budgetsError = computed(() => budgetsQuery.error.value?.message || "");

const watchlistCategories = computed(() => {
	const categories = budgetsQuery.data.value ?? [];
	return categories
		.filter((cat) => !systemCategoryIds.has(cat.category_id))
		.sort((a, b) => (a.available_minor || 0) - (b.available_minor || 0))
		.slice(0, 8);
});

const watchlistTarget = (category) =>
	category.goal_amount_minor || category.allocated_minor || 0;

const watchlistProgress = (category) => {
	const target = watchlistTarget(category);
	const available = category.available_minor || 0;
	if (target <= 0) {
		return available > 0 ? 100 : 0;
	}
	const pct = (available / target) * 100;
	return Math.max(0, Math.min(100, pct));
};

const budgetStatusLabel = (category) => {
	const available = category.available_minor || 0;
	if (available < 0) {
		return `${formatMinor(Math.abs(available))} over budget`;
	}
	return `${formatMinor(available)} available`;
};

const budgetStatusClass = (category) => {
	if ((category.available_minor || 0) < 0) {
		return "budget-watchlist__status--danger";
	}
	if (watchlistTarget(category) === 0) {
		return "budget-watchlist__status--muted";
	}
	return "budget-watchlist__status--positive";
};

const formatDueDate = (date) =>
	date.toLocaleDateString(undefined, {
		month: "long",
		day: "numeric",
	});

const getBillAmountMinor = (category) => {
	const target = category.goal_amount_minor || 0;
	const allocated = category.allocated_minor || 0;
	const available = Math.abs(category.available_minor || 0);
	if (target > 0) return target;
	if (allocated > 0) return allocated;
	return available;
};

const describeBillStatus = (category) => {
	const target = getBillAmountMinor(category);
	const available = category.available_minor || 0;
	if (target <= 0) {
		return {
			label: available > 0 ? `${formatMinor(available)} saved` : "Planning",
			variant: "muted",
		};
	}
	if (available >= target) {
		return { label: "Fully funded", variant: "success" };
	}
	const shortfall = target - Math.max(available, 0);
	return {
		label: `${formatMinor(shortfall)} to go`,
		variant: "warning",
	};
};

const billSections = computed(() => {
	const categories = budgetsQuery.data.value ?? [];
	const today = new Date();
	const thisMonth = new Date(today.getFullYear(), today.getMonth(), 1);
	const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, 1);
	const earlyNextCutoff = new Date(nextMonth.getFullYear(), nextMonth.getMonth(), 10);

	const sections = {
		current: [],
		next: [],
		annual: [],
	};

	categories.forEach((cat) => {
		if (!cat.goal_target_date) return;
		const due = new Date(cat.goal_target_date);
		const info = {
			id: cat.category_id,
			name: cat.name,
			dueLabel: formatDueDate(due),
			amountLabel: formatMinor(getBillAmountMinor(cat)),
			status: describeBillStatus(cat),
			dueDate: due,
		};

		const dueMonthStart = new Date(due.getFullYear(), due.getMonth(), 1);
		if (
			dueMonthStart.getFullYear() === thisMonth.getFullYear() &&
			dueMonthStart.getMonth() === thisMonth.getMonth()
		) {
			sections.current.push(info);
			return;
		}

		if (
			dueMonthStart.getFullYear() === nextMonth.getFullYear() &&
			dueMonthStart.getMonth() === nextMonth.getMonth() &&
			due <= earlyNextCutoff
		) {
			sections.next.push(info);
			return;
		}

		if (cat.goal_frequency === "yearly" || due > earlyNextCutoff) {
			sections.annual.push(info);
		}
	});

	const sortByDue = (items) =>
		items.sort((a, b) => a.dueDate.getTime() - b.dueDate.getTime());

	return [
		{ id: "current", title: "Bills this month", items: sortByDue(sections.current) },
		{
			id: "next",
			title: "Bills due early next month",
			items: sortByDue(sections.next),
		},
		{ id: "annual", title: "Annual bills", items: sortByDue(sections.annual) },
	];
});
</script>

<style scoped>
.dashboard-page {
  padding-bottom: 4rem;
}

.dashboard-layout {
  display: grid;
  gap: 20px;
  margin-top: 1.5rem;
}

@media (min-width: 1200px) {
  .dashboard-layout {
    grid-template-columns: 397px minmax(0, 1fr) 397px;
    align-items: start;
  }
}

.dashboard-column--stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-card {
  background: var(--surface);
  border: var(--border-thick);
  padding: 20px;
}

.dashboard-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.dashboard-card__label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0;
}

.dashboard-card__as-of {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  color: var(--muted);
}

.dashboard-card__headline {
  font-size: 2.25rem;
  font-weight: 700;
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.dashboard-card__change {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  margin: 0.35rem 0 0;
}

.dashboard-card__change--positive {
  color: var(--success);
}

.dashboard-card__change--negative {
  color: var(--danger);
}

.dashboard-card__footer-link {
  display: inline-flex;
  margin-top: 1rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  text-transform: uppercase;
  text-decoration: underline;
  color: var(--text);
}

.net-worth-card__figures {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-top: 0.5rem;
}

.net-worth-chart {
  margin-top: 1rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
}

.net-worth-chart__surface {
  position: relative;
  height: 220px;
  cursor: crosshair;
  user-select: none;
  -webkit-user-select: none;
}

.net-worth-chart__svg {
  width: 100%;
  height: 100%;
  display: block;
}

.net-worth-chart__line {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.net-worth-chart__area {
  opacity: 0.6;
}

.net-worth-chart__cursor {
  stroke: var(--muted);
  stroke-dasharray: 4;
  stroke-width: 1;
}

.net-worth-chart__drag-line {
  stroke: var(--text);
  stroke-width: 1;
  opacity: 0.4;
}

.net-worth-chart__drag-area {
  fill: var(--text);
  opacity: 0.05;
}

.net-worth-chart__tooltip {
  position: absolute;
  top: 16px;
  background: var(--surface);
  border: var(--border-thick);
  padding: 0.75rem;
  min-width: 180px;
  pointer-events: none;
  transform: translateX(-50%);
  box-shadow: var(--shadow-hard);
  font-size: 0.85rem;
}

.net-worth-chart__tooltip-range {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--muted);
  text-transform: uppercase;
  display: block;
  margin-bottom: 0.35rem;
}

.net-worth-chart__tooltip-rows {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.35rem;
}

.net-worth-chart__tooltip-row {
  display: flex;
  justify-content: space-between;
}

.net-worth-chart__tooltip-delta {
  border-top: 1px solid var(--border);
  padding-top: 0.35rem;
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
}

.net-worth-chart__tooltip-value {
  font-family: var(--font-mono);
  font-size: 1rem;
}

.net-worth-chart__loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(253, 251, 247, 0.85);
}

.dashboard-intervals {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.dashboard-intervals__button {
  background: none;
  border: 1px solid transparent;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.3rem 0.6rem;
  color: var(--muted);
  border-radius: 4px;
  cursor: pointer;
}

.dashboard-intervals__button--active {
  background: var(--text);
  color: var(--bg);
}

.dashboard-list {
  display: flex;
  flex-direction: column;
}

.dashboard-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}

.dashboard-row:last-child {
  border-bottom: none;
}

.dashboard-row__name {
  font-weight: 600;
}

.dashboard-row__meta {
  text-transform: uppercase;
  font-size: 0.7rem;
}

.dashboard-row__value {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.dashboard-row__value--positive {
  color: var(--text);
}

.dashboard-row__value--negative {
  color: var(--danger);
}

.budget-watchlist__item + .budget-watchlist__item {
  margin-top: 1.25rem;
}

.budget-watchlist__row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.budget-watchlist__name {
  font-weight: 600;
  margin: 0;
}

.budget-watchlist__status {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  margin: 0.25rem 0 0;
}

.budget-watchlist__status--danger {
  color: var(--danger);
}

.budget-watchlist__status--positive {
  color: var(--success);
}

.budget-watchlist__status--muted {
  color: var(--muted);
}

.budget-watchlist__available {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.budget-watchlist__bar {
  height: 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin: 0.5rem 0;
  background: var(--stone-50);
  overflow: hidden;
}

.budget-watchlist__fill {
  height: 100%;
  background: var(--success);
  transition: width 0.2s ease;
}

.budget-watchlist__fill--danger {
  background: var(--danger);
}

.budget-watchlist__scale {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--muted);
}

.bills-card__section + .bills-card__section {
  margin-top: 1.5rem;
}

.bills-card__title {
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  margin: 0 0 0.5rem;
}

.bills-card__empty {
  font-size: 0.85rem;
  padding: 0.5rem 0;
}

.bills-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.bills-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.5rem 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}

.bills-row:last-child {
  border-bottom: none;
}

.bills-row__label span {
  font-weight: 600;
}

.bills-row__label small {
  display: block;
  color: var(--muted);
}

.bills-row__value {
  text-align: right;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  align-items: flex-end;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  text-transform: uppercase;
}

.status-pill__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  display: inline-block;
}

.status-pill--success {
  color: var(--success);
}

.status-pill--warning {
  color: var(--danger);
}

.status-pill--muted {
  color: var(--muted);
}
</style>
