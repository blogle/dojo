const structuredCopy = (value) => (typeof structuredClone === "function" ? structuredClone(value) : JSON.parse(JSON.stringify(value)));

export const createInitialState = () => ({
  transactions: [],
  accountFilter: "all",
  accounts: [],
  netWorth: null,
  readyToAssign: null,
  reference: {
    accounts: [],
    categories: [],
  },
  budgets: {
    categories: [],
    rawCategories: [],
    groups: [],
    readyToAssignMinor: 0,
    activityMinor: 0,
    availableMinor: 0,
    allocatedMinor: 0,
    monthLabel: "",
    monthStartISO: null,
  },
  allocations: {
    entries: [],
    inflowMinor: 0,
    readyMinor: 0,
    monthLabel: "",
    monthStartISO: null,
  },
  forms: {
    transaction: { flow: "outflow", submitting: false },
    allocation: { submitting: false, error: null, pendingToCategory: null },
    transfer: { submitting: false, error: null },
    transactionEdit: { submitting: false, conceptId: null, transactionId: null },
  },
  pendingCategoryEdit: null,
  pendingGroupEdit: null,
  activeBudgetDetail: null,
  editingTransactionId: null,
});

export const createStore = (initialState) => {
  let currentState = structuredCopy(initialState);
  const listeners = new Set();

  const getState = () => currentState;

  const setState = (updater) => {
    const nextState = typeof updater === "function" ? updater(currentState) : updater;
    if (!nextState || nextState === currentState) {
      return currentState;
    }
    currentState = structuredCopy(nextState);
    listeners.forEach((listener) => listener(currentState));
    return currentState;
  };

  const patchState = (partial) =>
    setState((prev) => ({
      ...prev,
      ...partial,
    }));

  const subscribe = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  return { getState, setState, patchState, subscribe };
};
