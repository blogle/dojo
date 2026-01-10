<template>
  <div>
    <div class="investments-chart__frame">

      <p v-if="!points.length" class="u-muted investments-chart__empty">
        {{ loading ? "Loading history…" : "No chart data yet." }}
      </p>

      <svg
        v-else
        class="investments-chart__svg"
        :class="{ 'investments-chart__svg--loading': loading }"
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
            <stop offset="85%" :stop-color="themeColor" stop-opacity="0.4" />
            <stop offset="100%" :stop-color="themeColor" stop-opacity="0" />
          </linearGradient>
        </defs>

        <path :d="areaPath" :fill="`url(#${gradientId})`" />
        <path
          :d="linePath"
          :stroke="themeColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
          fill="none"
        />

        <rect
          v-if="dragActive"
          :x="dragRect.x"
          y="0"
          :width="dragRect.width"
          height="260"
          fill="rgba(0,0,0,0.06)"
        />

        <line
          v-if="dragActive"
          :x1="scaleX(dragStart)"
          y1="0"
          :x2="scaleX(dragStart)"
          y2="260"
          stroke="rgba(0,0,0,0.25)"
          stroke-width="1"
          stroke-dasharray="4 4"
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

        <g
          v-if="dragTooltip"
          class="investments-chart__tooltip"
          :transform="dragTooltipTransform"
        >
          <rect x="0" y="0" width="320" height="78" fill="#ffffff" stroke="#e0e0e0" />
          <text x="10" y="22">{{ dragTooltip.rangeLabel }}</text>
          <text x="10" y="44">{{ dragTooltip.valuesLabel }}</text>
          <text x="10" y="66">{{ dragTooltip.deltaLabel }}</text>
        </g>
       </svg>

       <p
         v-if="loading && points.length"
         class="u-muted investments-chart__loading"
         aria-live="polite"
       >
         Loading…
       </p>
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
	series: {
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
	increaseIsGood: {
		type: Boolean,
		default: true,
	},
	showPercentChange: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["change-interval"]);

const options = ["1D", "1W", "1M", "3M", "YTD", "1Y", "5Y", "Max"];
const gradientId = `inv-gradient-${Math.random().toString(16).slice(2)}`;

const W = 1000;
const H = 260;

const isDeltaGood = (delta) => {
	return props.increaseIsGood ? delta >= 0 : delta <= 0;
};

const points = computed(() => {
	const data = props.series ?? [];
	return [...data]
		.filter(
			(point) =>
				point &&
				typeof point.date === "string" &&
				Number.isFinite(point.value_minor),
		)
		.sort((a, b) => a.date.localeCompare(b.date))
		.map((point) => ({
			date: point.date,
			value: point.value_minor,
		}));
});

const minValue = computed(() => {
	if (!points.value.length) {
		return 0;
	}
	return Math.min(...points.value.map((p) => p.value));
});
const maxValue = computed(() => {
	if (!points.value.length) {
		return 0;
	}
	return Math.max(...points.value.map((p) => p.value));
});

const scaleX = (index) => {
	if (points.value.length <= 1) {
		return 0;
	}
	return (index / (points.value.length - 1)) * W;
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
	if (!points.value.length) {
		return "";
	}
	return points.value
		.map(
			(p, idx) => `${idx === 0 ? "M" : "L"}${scaleX(idx)} ${scaleY(p.value)}`,
		)
		.join(" ");
});

const areaPath = computed(() => {
	if (!points.value.length) {
		return "";
	}
	const line = linePath.value;
	const lastX = scaleX(points.value.length - 1);
	return `${line} L${lastX} ${H} L0 ${H} Z`;
});

const defaultTheme = computed(() => {
	if (points.value.length < 2) {
		return "var(--success)";
	}
	const start = points.value[0].value;
	const end = points.value[points.value.length - 1].value;
	return isDeltaGood(end - start) ? "var(--success)" : "var(--danger)";
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

	const startIdx = Math.min(dragStart.value, dragEnd.value);
	const endIdx = Math.max(dragStart.value, dragEnd.value);
	const startValue = points.value[startIdx]?.value;
	const endValue = points.value[endIdx]?.value;
	if (startValue === undefined || endValue === undefined) {
		return defaultTheme.value;
	}
	return isDeltaGood(endValue - startValue)
		? "var(--success)"
		: "var(--danger)";
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

	const startIdx = Math.min(dragStart.value, dragEnd.value);
	const endIdx = Math.max(dragStart.value, dragEnd.value);
	const startPoint = points.value[startIdx];
	const endPoint = points.value[endIdx];
	if (!startPoint || !endPoint) {
		return null;
	}

	const delta = endPoint.value - startPoint.value;
	const sign = delta >= 0 ? "+" : "";

	const deltaLabelBase = `${sign}${formatAmount(delta)}`;
	const pct =
		props.showPercentChange && startPoint.value !== 0
			? delta / startPoint.value
			: null;
	const pctLabel =
		pct === null ? "" : ` (${pct >= 0 ? "+" : ""}${(pct * 100).toFixed(2)}%)`;

	return {
		rangeLabel: `${startPoint.date} – ${endPoint.date}`,
		valuesLabel: `Start ${formatAmount(startPoint.value)} · End ${formatAmount(endPoint.value)}`,
		deltaLabel: `Δ ${deltaLabelBase}${pctLabel}`,
	};
});

const dragTooltipTransform = computed(() => {
	if (!dragActive.value) {
		return "translate(0,0)";
	}
	const rect = dragRect.value;
	const x = Math.min(Math.max(rect.x + rect.width / 2 - 160, 12), W - 332);
	return `translate(${x}, 12)`;
});

const toLocalIndex = (evt) => {
	const { left, width } = evt.currentTarget.getBoundingClientRect();
	const ratio = (evt.clientX - left) / width;
	return Math.max(
		0,
		Math.min(
			points.value.length - 1,
			Math.round(ratio * (points.value.length - 1)),
		),
	);
};

const onMove = (evt) => {
	const idx = toLocalIndex(evt);
	const point = points.value[idx];
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
