import queryClient from "../queryClient.js";
import { todayISO } from "./format.js";

const parseError = async (response) => {
	const text = await response.text();
	if (!text) {
		return null;
	}
	try {
		const payload = JSON.parse(text);
		return payload.detail || payload.error || text;
	} catch {
		return text;
	}
};

export const fetchJSON = async (url, options = {}) => {
	const response = await fetch(url, options);
	if (!response.ok) {
		const message = await parseError(response);
		const fallback = `Request failed: ${response.status}`;
		throw new Error(message || fallback);
	}
	if (response.status === 204) {
		return null;
	}
	const text = await response.text();
	if (!text) {
		return null;
	}
	return JSON.parse(text);
};

const defaultHeaders = { "Content-Type": "application/json" };

const invalidateQueries = async (queryKeys = []) => {
	if (!queryClient?.invalidateQueries) {
		return;
	}
	try {
		await Promise.all(
			queryKeys.map((queryKey) => {
				const normalized = Array.isArray(queryKey) ? queryKey : [queryKey];
				return queryClient.invalidateQueries({ queryKey: normalized });
			}),
		);
	} catch (error) {
		console.warn("queryClient invalidation failed", error);
	}
};

const invalidateLedgerQueries = () =>
	invalidateQueries([
		"transactions",
		"reconciliation-worksheet",
		"budget-allocations",
		"ready-to-assign",
		"accounts",
		"budget-categories",
	]);

export const api = {
	transactions: {
		list: async (limit = 100) => fetchJSON(`/api/transactions?limit=${limit}`),
		create: async (payload) => {
			const result = await fetchJSON("/api/transactions", {
				method: "POST",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		update: async (conceptId, payload) => {
			const result = await fetchJSON(`/api/transactions/${conceptId}`, {
				method: "PUT",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		delete: async (conceptId) => {
			await fetchJSON(`/api/transactions/${conceptId}`, {
				method: "DELETE",
			});
			await invalidateLedgerQueries();
		},
	},
	transfers: {
		create: async (payload) => {
			const result = await fetchJSON("/api/transfers", {
				method: "POST",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
	},
	accounts: {
		list: async () => fetchJSON("/api/accounts"),
		get: async (accountId) => fetchJSON(`/api/accounts/${accountId}`),
		getTransactions: async (accountId, params = {}) => {
			const query = new URLSearchParams();
			if (params.start_date) query.set("start_date", params.start_date);
			if (params.end_date) query.set("end_date", params.end_date);
			if (params.limit) query.set("limit", String(params.limit));
			if (params.status) query.set("status", params.status);
			const suffix = query.toString();
			return fetchJSON(
				`/api/accounts/${accountId}/transactions${suffix ? `?${suffix}` : ""}`,
			);
		},
		getHistory: async (accountId, startDate, endDate, status = "all") =>
			fetchJSON(
				`/api/accounts/${accountId}/history?start_date=${startDate}&end_date=${endDate}&status=${status}`,
			),
		create: async (payload) => {
			const result = await fetchJSON("/api/accounts", {
				method: "POST",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
	},
	reconciliations: {
		getLatest: async (accountId) =>
			fetchJSON(`/api/accounts/${accountId}/reconciliations/latest`),
		getWorksheet: async (accountId) =>
			fetchJSON(`/api/accounts/${accountId}/reconciliations/worksheet`),
		create: async (accountId, payload) => {
			const result = await fetchJSON(
				`/api/accounts/${accountId}/reconciliations`,
				{
					method: "POST",
					headers: defaultHeaders,
					body: JSON.stringify(payload),
				},
			);
			await invalidateLedgerQueries();
			return result;
		},
	},
	netWorth: {
		current: async () => fetchJSON("/api/net-worth/current"),
		history: async (interval) =>
			fetchJSON(
				`/api/net-worth/history?interval=${encodeURIComponent(interval)}`,
			),
	},
	investments: {
		getAccount: async (accountId) =>
			fetchJSON(`/api/investments/accounts/${accountId}`),
		getHistory: async (accountId, startDate, endDate) =>
			fetchJSON(
				`/api/investments/accounts/${accountId}/history?start_date=${startDate}&end_date=${endDate}`,
			),
		reconcile: async (accountId, payload) => {
			const result = await fetchJSON(
				`/api/investments/accounts/${accountId}/reconcile`,
				{
					method: "POST",
					headers: defaultHeaders,
					body: JSON.stringify(payload),
				},
			);
			await invalidateQueries([
				["investment-account", accountId],
				"netWorth",
				"accounts",
			]);
			return result;
		},
		triggerMarketUpdate: async () => {
			const result = await fetchJSON("/api/jobs/market-update", {
				method: "POST",
			});
			await invalidateQueries([
				"netWorth",
				"accounts",
				"investment-account",
				"investment-history",
			]);
			return result;
		},
	},
	readyToAssign: {
		current: async (month) =>
			month
				? fetchJSON(`/api/budget/ready-to-assign?month=${month}`)
				: fetchJSON("/api/budget/ready-to-assign"),
	},
	reference: {
		load: async ({ includePaymentCategories = false } = {}) => {
			const qs = includePaymentCategories
				? "?include_payment_categories=true"
				: "";
			return fetchJSON(`/api/reference-data${qs}`);
		},
	},
	budgets: {
		categories: async (month) =>
			fetchJSON(`/api/budget-categories?month=${month}`),
		allocationCategories: async (month) =>
			fetchJSON(`/api/budget/allocation-categories?month=${month}`),
		groups: async () => fetchJSON("/api/budget-category-groups"),
		createCategory: async (payload) => {
			const result = await fetchJSON("/api/budget-categories", {
				method: "POST",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		updateCategory: async (categoryId, payload) => {
			const result = await fetchJSON(`/api/budget-categories/${categoryId}`, {
				method: "PUT",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		createGroup: async (payload) => {
			const result = await fetchJSON("/api/budget-category-groups", {
				method: "POST",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		updateGroup: async (groupId, payload) => {
			const result = await fetchJSON(`/api/budget-category-groups/${groupId}`, {
				method: "PUT",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		allocations: async (month) =>
			month
				? fetchJSON(`/api/budget/allocations?month=${month}`)
				: fetchJSON("/api/budget/allocations"),
		createAllocation: async (payload) => {
			const result = await fetchJSON("/api/budget/allocations", {
				method: "POST",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		updateAllocation: async (conceptId, payload) => {
			const result = await fetchJSON(`/api/budget/allocations/${conceptId}`, {
				method: "PUT",
				headers: defaultHeaders,
				body: JSON.stringify(payload),
			});
			await invalidateLedgerQueries();
			return result;
		},
		deleteAllocation: async (conceptId) => {
			await fetchJSON(`/api/budget/allocations/${conceptId}`, {
				method: "DELETE",
			});
			await invalidateLedgerQueries();
		},
	},
};

export const postOpeningBalanceTransaction = async (
	account,
	openingBalanceMinor,
) => {
	if (!account || !openingBalanceMinor) {
		return;
	}
	const signedAmount =
		account.account_type === "liability"
			? -openingBalanceMinor
			: openingBalanceMinor;
	if (signedAmount === 0) {
		return;
	}
	await api.transactions.create({
		transaction_date: todayISO(),
		account_id: account.account_id,
		category_id: "opening_balance",
		amount_minor: signedAmount,
		memo: "Opening balance",
		status: "cleared",
	});
};
