<template>
  <div>
    <div class="investments-chart__frame">
      <div v-if="summary" class="investments-chart__summary" aria-label="Chart summary">
        <p class="investments-chart__summary-value">{{ summary.valueLabel }}</p>
        <p class="investments-chart__summary-delta" :class="summary.deltaClass">
          <span>{{ summary.deltaLabel }}</span>
          <span v-if="summary.pctLabel">{{ summary.pctLabel }}</span>
        </p>
      </div>

      <p v-if="loading" class="u-muted investments-chart__empty">Loading history…</p>
      <p v-else-if="!points.length" class="u-muted investments-chart__empty">No chart data yet.</p>

      <svg
        v-else
        class="investments-chart__svg"
        viewBox="0 0 1000 260"
        preserveAspectRatio="none"
        @mousemove="onMove"
        @mouseleave="onLeave"
        @mousedown="onDown"
        @mouseup="onUp"
      >
        <defs>
          <linearGradient :id="gradientId" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" :stop-color="themeColor" stop-opacity="0.4" />
            <stop offset="55%" :stop-color="themeColor" stop-opacity="0.1" />
            <stop offset="100%" :stop-color="themeColor" stop-opacity="0" />
          </linearGradient>
        </defs>

        <path :d="areaPath" :fill="`url(#${gradientId})`" />
        <path :d="linePath" :stroke="themeColor" stroke-width="3" fill="none" />

        <rect
          v-if="dragActive"
          :x="dragRect.x"
          y="0"
          :width="dragRect.width"
          height="260"
          fill="rgba(0,0,0,0.06)"
        />

        <line
          v-if="cursor"
          :x1="cursor.x"
          y1="0"
          :x2="cursor.x"
          y2="260"
          stroke="rgba(0,0,0,0.2)"
          stroke-width="1"
        />
        <circle
          v-if="cursor"
          :cx="cursor.x"
          :cy="cursor.y"
          r="5"
          :fill="themeColor"
          stroke="#fff"
          stroke-width="2"
        />

        <g
          v-if="cursor && !dragging"
          class="investments-chart__tooltip"
          :transform="tooltipTransform"
        >
          <rect x="0" y="0" width="200" height="60" fill="#ffffff" stroke="#e0e0e0" />
          <text x="10" y="22">{{ cursor.labelDate }}</text>
          <text x="10" y="44">{{ cursor.labelValue }}</text>
        </g>

        <g v-if="dragTooltip" class="investments-chart__tooltip" :transform="dragTooltipTransform">
          <rect x="0" y="0" width="240" height="60" fill="#ffffff" stroke="#e0e0e0" />
          <text x="10" y="22">Range</text>
          <text x="10" y="44">{{ dragTooltip }}</text>
        </g>
      </svg>
    </div>

    <div class="investments-chart__tabs" role="tablist" aria-label="Time range">
      <button
        v-for="opt in options"
        :key="opt"
        type="button"
        class="investments-chart__tab"
        :class="{ 'investments-chart__tab--active': opt === interval }"
        @click="$emit('change-interval', opt)"
      >
        {{ opt }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { formatAmount } from "../../services/format.js";

const props = defineProps({
	points: {
		type: Array,
		required: true,
	},
	interval: {
		type: String,
		required: true,
	},
	loading: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["change-interval"]);

const options = ["1D", "1W", "1M", "3M", "YTD", "1Y", "Max"];
const gradientId = `inv-gradient-${Math.random().toString(16).slice(2)}`;

const W = 1000;
const H = 260;

const series = computed(() =>
	props.points.map((p) => ({
		date: p.market_date,
		value: p.nav_minor,
	})),
);

const summary = computed(() => {
	if (!series.value.length) {
		return null;
	}
	const start = series.value[0]?.value;
	const end = series.value[series.value.length - 1]?.value;
	if (start === undefined || end === undefined) {
		return null;
	}
	const delta = end - start;
	const sign = delta >= 0 ? "+" : "";
	const pct = start !== 0 ? delta / start : null;
	return {
		valueLabel: formatAmount(end),
		deltaClass:
			delta >= 0
				? "investments-chart__delta--up"
				: "investments-chart__delta--down",
		deltaLabel: `${sign}${formatAmount(delta)}`,
		pctLabel: pct === null ? "" : `(${sign}${(pct * 100).toFixed(2)}%)`,
	};
});

const minValue = computed(() => Math.min(...series.value.map((p) => p.value)));
const maxValue = computed(() => Math.max(...series.value.map((p) => p.value)));

const scaleX = (index) => {
	if (series.value.length <= 1) {
		return 0;
	}
	return (index / (series.value.length - 1)) * W;
};

const scaleY = (value) => {
	const min = minValue.value;
	const max = maxValue.value;
	if (max === min) {
		return H / 2;
	}
	const t = (value - min) / (max - min);
	return H - t * (H - 12) - 6;
};

const linePath = computed(() => {
	if (!series.value.length) {
		return "";
	}
	return series.value
		.map(
			(p, idx) => `${idx === 0 ? "M" : "L"}${scaleX(idx)} ${scaleY(p.value)}`,
		)
		.join(" ");
});

const areaPath = computed(() => {
	if (!series.value.length) {
		return "";
	}
	const line = linePath.value;
	const lastX = scaleX(series.value.length - 1);
	return `${line} L${lastX} ${H} L0 ${H} Z`;
});

const defaultTheme = computed(() => {
	if (series.value.length < 2) {
		return "var(--success)";
	}
	const start = series.value[0].value;
	const end = series.value[series.value.length - 1].value;
	return end >= start ? "var(--success)" : "var(--danger)";
});

const cursor = ref(null);
const dragStart = ref(null);
const dragEnd = ref(null);
const dragging = ref(false);

const dragActive = computed(
	() => dragStart.value !== null && dragEnd.value !== null,
);

const dragRect = computed(() => {
	if (!dragActive.value) {
		return { x: 0, width: 0 };
	}
	const startX = scaleX(dragStart.value);
	const endX = scaleX(dragEnd.value);
	return {
		x: Math.min(startX, endX),
		width: Math.abs(endX - startX),
	};
});

const selectionTheme = computed(() => {
	if (!dragActive.value) {
		return defaultTheme.value;
	}
	const a = series.value[dragStart.value]?.value;
	const b = series.value[dragEnd.value]?.value;
	if (a === undefined || b === undefined) {
		return defaultTheme.value;
	}
	return b >= a ? "var(--success)" : "var(--danger)";
});

const themeColor = computed(() => selectionTheme.value);

const tooltipTransform = computed(() => {
	if (!cursor.value) {
		return "translate(0,0)";
	}
	const x = Math.min(Math.max(cursor.value.x + 12, 12), W - 212);
	const y = Math.min(Math.max(cursor.value.y - 70, 8), H - 70);
	return `translate(${x}, ${y})`;
});

const dragTooltip = computed(() => {
	if (!dragActive.value) {
		return null;
	}
	const a = series.value[dragStart.value]?.value;
	const b = series.value[dragEnd.value]?.value;
	if (a === undefined || b === undefined) {
		return null;
	}
	const delta = b - a;
	const sign = delta >= 0 ? "+" : "";
	if (a === 0) {
		return `${sign}${formatAmount(delta)}`;
	}
	const pct = delta / a;
	return `${sign}${formatAmount(delta)} (${sign}${(pct * 100).toFixed(2)}%)`;
});

const dragTooltipTransform = computed(() => {
	if (!dragActive.value) {
		return "translate(0,0)";
	}
	const rect = dragRect.value;
	const x = Math.min(Math.max(rect.x + rect.width / 2 - 120, 12), W - 252);
	return `translate(${x}, 12)`;
});

const toLocalIndex = (evt) => {
	const { left, width } = evt.currentTarget.getBoundingClientRect();
	const ratio = (evt.clientX - left) / width;
	return Math.max(
		0,
		Math.min(
			series.value.length - 1,
			Math.round(ratio * (series.value.length - 1)),
		),
	);
};

const onMove = (evt) => {
	const idx = toLocalIndex(evt);
	const point = series.value[idx];
	if (!point) {
		return;
	}
	const x = scaleX(idx);
	const y = scaleY(point.value);
	cursor.value = {
		idx,
		x,
		y,
		labelDate: point.date,
		labelValue: formatAmount(point.value),
	};

	if (dragging.value) {
		dragEnd.value = idx;
	}
};

const onLeave = () => {
	cursor.value = null;
	dragging.value = false;
	dragStart.value = null;
	dragEnd.value = null;
};

const onDown = (evt) => {
	dragStart.value = toLocalIndex(evt);
	dragEnd.value = dragStart.value;
	dragging.value = true;
};

const onUp = () => {
	dragging.value = false;
};
</script>
