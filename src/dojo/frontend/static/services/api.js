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
	const client = typeof window !== "undefined" ? window.dojoQueryClient : null;
	if (!client?.invalidateQueries) {
		return;
	}
	try {
		await Promise.all(
			queryKeys.map((queryKey) => client.invalidateQueries({ queryKey: [queryKey] })),
		);
	} catch (error) {
		console.warn("queryClient invalidation failed", error);
	}
};

const invalidateLedgerQueries = () =>
	invalidateQueries([
		"transactions",
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
	netWorth: {
		current: async () => fetchJSON("/api/net-worth/current"),
	},
	readyToAssign: {
		current: async (month) =>
			month
				? fetchJSON(`/api/budget/ready-to-assign?month=${month}`)
				: fetchJSON("/api/budget/ready-to-assign"),
	},
	reference: {
		load: async () => fetchJSON("/api/reference-data"),
	},
	budgets: {
		categories: async (month) =>
			fetchJSON(`/api/budget-categories?month=${month}`),
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
