import { computed, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import { todayISO } from "../services/format.js";

export const RANGE_OPTIONS = ["1D", "1W", "1M", "3M", "YTD", "1Y", "Max"];
export const DEFAULT_RANGE_LABEL = "1M";

export const sanitizeRangeLabel = (
	value,
	defaultLabel = DEFAULT_RANGE_LABEL,
) => {
	if (typeof value !== "string") {
		return defaultLabel;
	}
	if (RANGE_OPTIONS.includes(value)) {
		return value;
	}
	return defaultLabel;
};

const dateToISO = (value) => {
	return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};

export const resolveRangeFromLabel = (label) => {
	const end = new Date();
	const start = new Date(end);

	if (label === "1D") {
		start.setDate(end.getDate() - 1);
	} else if (label === "1W") {
		start.setDate(end.getDate() - 7);
	} else if (label === "1M") {
		start.setMonth(end.getMonth() - 1);
	} else if (label === "3M") {
		start.setMonth(end.getMonth() - 3);
	} else if (label === "YTD") {
		start.setMonth(0);
		start.setDate(1);
	} else if (label === "1Y") {
		start.setFullYear(end.getFullYear() - 1);
	} else if (label === "Max") {
		start.setFullYear(end.getFullYear() - 5);
	}

	return {
		startDate: dateToISO(start),
		endDate: todayISO(),
	};
};

export const useChartRange = (options = {}) => {
	const route = options.route ?? useRoute();
	const router = options.router ?? useRouter();
	const defaultLabel = options.defaultLabel ?? DEFAULT_RANGE_LABEL;

	const rangeLabel = computed(() =>
		sanitizeRangeLabel(route.query.range, defaultLabel),
	);

	watchEffect(() => {
		const raw = route.query.range;
		if (typeof raw === "string" && raw === rangeLabel.value) {
			return;
		}
		router.replace({ query: { ...route.query, range: rangeLabel.value } });
	});

	const setRangeLabel = (label) => {
		router.replace({
			query: {
				...route.query,
				range: sanitizeRangeLabel(label, defaultLabel),
			},
		});
	};

	const range = computed(() => resolveRangeFromLabel(rangeLabel.value));

	return {
		rangeLabel,
		range,
		setRangeLabel,
	};
};
