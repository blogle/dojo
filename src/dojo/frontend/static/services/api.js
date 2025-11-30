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

export const api = {
  transactions: {
    list: async (limit = 100) => fetchJSON(`/api/transactions?limit=${limit}`),
    create: async (payload) =>
      fetchJSON("/api/transactions", { method: "POST", headers: defaultHeaders, body: JSON.stringify(payload) }),
    update: async (conceptId, payload) =>
      fetchJSON(`/api/transactions/${conceptId}`, { method: "PUT", headers: defaultHeaders, body: JSON.stringify(payload) }),
  },
  transfers: {
    create: async (payload) =>
      fetchJSON("/api/transfers", { method: "POST", headers: defaultHeaders, body: JSON.stringify(payload) }),
  },
  accounts: {
    list: async () => fetchJSON("/api/accounts"),
    create: async (payload) =>
      fetchJSON("/api/accounts", { method: "POST", headers: defaultHeaders, body: JSON.stringify(payload) }),
  },
  netWorth: {
    current: async () => fetchJSON("/api/net-worth/current"),
  },
  readyToAssign: {
    current: async (month) =>
      month ? fetchJSON(`/api/budget/ready-to-assign?month=${month}`) : fetchJSON("/api/budget/ready-to-assign"),
  },
  reference: {
    load: async () => fetchJSON("/api/reference-data"),
  },
  budgets: {
    categories: async (month) => fetchJSON(`/api/budget-categories?month=${month}`),
    groups: async () => fetchJSON("/api/budget-category-groups"),
    createCategory: async (payload) =>
      fetchJSON("/api/budget-categories", { method: "POST", headers: defaultHeaders, body: JSON.stringify(payload) }),
    updateCategory: async (categoryId, payload) =>
      fetchJSON(`/api/budget-categories/${categoryId}`, { method: "PUT", headers: defaultHeaders, body: JSON.stringify(payload) }),
    createGroup: async (payload) =>
      fetchJSON("/api/budget-category-groups", { method: "POST", headers: defaultHeaders, body: JSON.stringify(payload) }),
    updateGroup: async (groupId, payload) =>
      fetchJSON(`/api/budget-category-groups/${groupId}`, { method: "PUT", headers: defaultHeaders, body: JSON.stringify(payload) }),
    allocations: async (month) => fetchJSON(`/api/budget/allocations?month=${month}`),
    createAllocation: async (payload) =>
      fetchJSON("/api/budget/allocations", { method: "POST", headers: defaultHeaders, body: JSON.stringify(payload) }),
    updateAllocation: async (conceptId, payload) =>
      fetchJSON(`/api/budget/allocations/${conceptId}`, { method: "PUT", headers: defaultHeaders, body: JSON.stringify(payload) }),
  },
};

export const postOpeningBalanceTransaction = async (account, openingBalanceMinor) => {
  if (!account || !openingBalanceMinor) {
    return;
  }
  const signedAmount = account.account_type === "liability" ? -openingBalanceMinor : openingBalanceMinor;
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
