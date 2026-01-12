import { dollarsToMinor } from "../services/format.js";

export const isValidDateInput = (value) => {
	if (!value) {
		return false;
	}
	const parsed = Date.parse(`${value}T00:00:00`);
	return Number.isFinite(parsed);
};

export const dollarsInputToMinor = (value) => {
	if (value === null || value === undefined || value === "") {
		return null;
	}
	const parsed = Number.parseFloat(value);
	if (!Number.isFinite(parsed)) {
		return null;
	}
	return dollarsToMinor(parsed);
};

export const amountMinorToInlineFields = (amountMinor) => {
	const formatted = (Math.abs(amountMinor) / 100).toFixed(2);
	if (amountMinor < 0) {
		return { outflow: formatted, inflow: "" };
	}
	return { inflow: formatted, outflow: "" };
};

export const resolveInlineSignedAmountMinor = (inflowValue, outflowValue) => {
	const inflowMinor = dollarsInputToMinor(inflowValue);
	const outflowMinor = dollarsInputToMinor(outflowValue);
	const hasInflow = inflowMinor !== null && inflowMinor !== 0;
	const hasOutflow = outflowMinor !== null && outflowMinor !== 0;

	if (hasInflow && hasOutflow) {
		return { error: "Enter either an inflow or an outflow, not both." };
	}

	const pickedMinor = hasInflow
		? Math.abs(inflowMinor)
		: hasOutflow
			? Math.abs(outflowMinor)
			: null;

	if (!pickedMinor) {
		return { error: "Amount must be non-zero." };
	}

	const signedAmount = hasInflow ? pickedMinor : -pickedMinor;
	return { signedAmount };
};

export const resolveSignedAmountFromInput = (
	amountValue,
	allowedFlows = ["outflow", "inflow"],
) => {
	const flows = Array.isArray(allowedFlows) ? allowedFlows : [];
	const resolvedFlows = flows.filter(
		(flow) => flow === "outflow" || flow === "inflow",
	);
	const canOutflow = !resolvedFlows.length || resolvedFlows.includes("outflow");
	const canInflow = !resolvedFlows.length || resolvedFlows.includes("inflow");

	const raw =
		amountValue === null || amountValue === undefined
			? ""
			: String(amountValue);
	const trimmed = raw.trim();
	if (!trimmed) {
		return { error: "Enter a valid amount." };
	}

	let flowFromSign = null;
	let magnitudeText = trimmed;
	if (trimmed.startsWith("+")) {
		flowFromSign = "inflow";
		magnitudeText = trimmed.slice(1).trim();
	} else if (trimmed.startsWith("-")) {
		flowFromSign = "outflow";
		magnitudeText = trimmed.slice(1).trim();
	}

	const magnitudeMinor = dollarsInputToMinor(magnitudeText);
	if (magnitudeMinor === null) {
		return { error: "Enter a valid amount." };
	}
	const normalizedAmount = Math.abs(magnitudeMinor);
	if (normalizedAmount === 0) {
		return { error: "Amount must be non-zero." };
	}

	const defaultFlow =
		canOutflow && !canInflow
			? "outflow"
			: canInflow && !canOutflow
				? "inflow"
				: "outflow";
	const resolvedFlow = flowFromSign || defaultFlow;

	if (resolvedFlow === "outflow" && !canOutflow) {
		return { error: "Outflows are not allowed for this entry." };
	}
	if (resolvedFlow === "inflow" && !canInflow) {
		return { error: "Inflows are not allowed for this entry." };
	}

	return {
		flow: resolvedFlow,
		signedAmount:
			resolvedFlow === "inflow" ? normalizedAmount : -normalizedAmount,
	};
};

export const resolveSignedAmountFromFlow = (amountValue, flow) => {
	const amountMinor = dollarsInputToMinor(amountValue);
	if (amountMinor === null) {
		return { error: "Enter a valid amount." };
	}
	const normalizedAmount = Math.abs(amountMinor);
	if (normalizedAmount === 0) {
		return { error: "Amount must be non-zero." };
	}
	return {
		signedAmount: flow === "inflow" ? normalizedAmount : -normalizedAmount,
	};
};
