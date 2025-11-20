const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const selectors = {
  monthSpend: "#month-spend",
  monthBudgeted: "#month-budgeted",
  transactionsBody: "#transactions-body",
  assetsTotal: "#assets-total",
  liabilitiesTotal: "#liabilities-total",
  netWorth: "#net-worth",
  readyToAssign: "#ready-to-assign",
  accountGroups: "#account-groups",
  addAccountButton: "[data-add-account-button]",
  accountModal: "#account-modal",
  accountModalLabel: "[data-modal-label]",
  accountModalTitle: "[data-modal-title]",
  accountModalSubtitle: "[data-modal-subtitle]",
  accountModalMetadata: "[data-modal-metadata]",
  accountModalBalance: "[data-modal-balance]",
  modalClose: "[data-close-modal]",
  accountSectionLink: "[data-account-section]",
  modalAddButton: "[data-add-account-submit]",
  modalTypeSelect: "[name=type]",
  modalNameInput: "[name=name]",
  modalBalanceInput: "[name=balance]",
  transactionForm: "#transaction-form",
  transactionSubmit: "[data-transaction-submit]",
  transactionError: "[data-testid='transaction-error']",
  transactionAccountSelect: "[data-transaction-account]",
  transactionCategorySelect: "[data-transaction-category]",
  transactionFlowInputs: "[data-transaction-flow]",
  transferForm: "#transfer-form",
  transferSubmit: "[data-transfer-submit]",
  transferError: "[data-testid='transfer-error']",
  transferSourceSelect: "[data-transfer-source]",
  transferDestinationSelect: "[data-transfer-destination]",
  transferCategorySelect: "[data-transfer-category]",
  allocationForm: "[data-testid='allocation-form']",
  allocationSubmit: "[data-allocation-submit]",
  allocationError: "[data-testid='allocation-error']",
  allocationFromSelect: "[data-allocation-from]",
  allocationToSelect: "[data-allocation-to]",
  allocationDateInput: "[data-allocation-date]",
  allocationsBody: "#allocations-body",
  allocationInflowValue: "#allocations-inflow-value",
  allocationReadyValue: "#allocations-ready-value",
  allocationMonthLabel: "#allocations-month-label",
  budgetsGrid: "[data-budgets-grid]",
  budgetsReadyValue: "#budgets-ready-value",
  budgetsActivityValue: "#budgets-activity-value",
  budgetsAvailableValue: "#budgets-available-value",
  budgetsMonthLabel: "#budgets-month-label",
  categoryModal: "#category-modal",
  categoryModalTitle: "[data-category-modal-title]",
  categoryModalHint: "[data-category-modal-hint]",
  categoryNameInput: "[data-category-name]",
  categorySlugInput: "[data-category-slug]",
  categoryError: "[data-category-error]",
  categoryForm: "[data-category-form]",
  categorySubmit: "[data-category-submit]",
  categoryModalClose: "[data-close-category-modal]",
  categoryGroupSelect: "[data-category-group]",
  groupModal: "#group-modal",
  groupModalTitle: "[data-group-modal-title]",
  groupForm: "[data-group-form]",
  groupSubmit: "[data-group-submit]",
  groupError: "[data-group-error]",
  groupModalClose: "[data-close-group-modal]",
  budgetDetailModal: "#budget-detail-modal",
  budgetDetailTitle: "[data-budget-detail-title]",
  budgetDetailClose: "[data-close-budget-detail-modal]",
  budgetDetailLeftover: "[data-detail-leftover]",
  budgetDetailBudgeted: "[data-detail-budgeted]",
  budgetDetailActivity: "[data-detail-activity]",
  budgetDetailAvailable: "[data-detail-available]",
  budgetDetailQuickActions: "[data-quick-actions]",
  budgetDetailEdit: "[data-detail-edit]",
  groupDetailModal: "#group-detail-modal",
  groupDetailTitle: "[data-group-detail-title]",
  groupDetailClose: "[data-close-group-detail-modal]",
  groupDetailLeftover: "[data-group-detail-leftover]",
  groupDetailBudgeted: "[data-group-detail-budgeted]",
  groupDetailActivity: "[data-group-detail-activity]",
  groupDetailAvailable: "[data-group-detail-available]",
  groupDetailQuickActions: "[data-group-quick-actions]",
  groupDetailEdit: "[data-group-detail-edit]",
  toastStack: "#toast-stack",
};

const accountGroupDefinitions = [
  {
    id: "cash",
    title: "Cash & Checking",
    type: "asset",
    description: "Everyday banking and liquid cash.",
  },
  {
    id: "accessible",
    title: "Accessible Assets",
    type: "asset",
    description: "Short-term deposits and cash equivalents.",
  },
  {
    id: "investment",
    title: "Investments",
    type: "asset",
    description: "Brokerage, retirement, and long-term holdings.",
  },
  {
    id: "credit",
    title: "Credit & Borrowing",
    type: "liability",
    description: "Credit cards, lines of credit, and short-duration loans.",
  },
  {
    id: "loan",
    title: "Loans & Mortgages",
    type: "liability",
    description: "Mortgages, auto loans, and other long-term debt.",
  },
  {
    id: "tangible",
    title: "Tangibles",
    type: "asset",
    description: "Appraised property, vehicles, and collectables.",
  },
];

const accountTypeMapping = {
  checking: { account_type: "asset", account_class: "cash", account_role: "on_budget" },
  credit: { account_type: "liability", account_class: "credit", account_role: "on_budget" },
  brokerage: { account_type: "asset", account_class: "investment", account_role: "tracking" },
  loan: { account_type: "liability", account_class: "loan", account_role: "tracking" },
  asset: { account_type: "asset", account_class: "tangible", account_role: "tracking" },
};

const state = {
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
};

let transactionsBodyEl = null;
let categorySlugDirty = false;
let detachInlineEscHandler = null;

const statusToggleIcons = `
  <svg class="status-icon status-icon--check" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6 12.5 L10 16.5 L18 8" />
  </svg>
  <svg class="status-icon status-icon--pending" viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="6.5" />
  </svg>
`;

const fetchJSON = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    let message = `Request failed: ${response.status}`;
    try {
      const payload = JSON.parse(text);
      message = payload.detail || payload.error || message;
    } catch {
      if (text) {
        message = text;
      }
    }
    throw new Error(message);
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

const formatAmount = (minor) => currencyFormatter.format(minor / 100);

const minorToDollars = (minor) => (minor / 100).toFixed(2);

// Amount inputs always accept dollars; cents remain an internal storage detail.
const dollarsToMinor = (value) => {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return 0;
  }
  return Math.round(parsed * 100);
};

const todayISO = () => new Date().toISOString().slice(0, 10);

const currentMonthStartISO = () => {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`;
};


const computeCurrentMonthSpend = (transactions) => {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();
  return transactions.reduce((total, tx) => {
    if (!tx || !tx.transaction_date) return total;
    const txDate = new Date(`${tx.transaction_date}T00:00:00`);
    if (
      txDate.getMonth() === currentMonth &&
      txDate.getFullYear() === currentYear &&
      tx.amount_minor < 0
    ) {
      return total + Math.abs(tx.amount_minor);
    }
    return total;
  }, 0);
};

const populateSelect = (selectEl, items, { valueKey, labelKey }, placeholder) => {
  if (!selectEl) {
    return;
  }
  const previous = selectEl.value;
  const fragment = document.createDocumentFragment();
  if (placeholder) {
    const option = document.createElement("option");
    option.value = "";
    option.disabled = true;
    option.selected = !previous || previous === "";
    option.textContent = placeholder;
    fragment.appendChild(option);
  }
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item[valueKey];
    option.textContent = item[labelKey];
    fragment.appendChild(option);
  });
  selectEl.innerHTML = "";
  selectEl.appendChild(fragment);
  if (items.some((item) => item[valueKey] === previous)) {
    selectEl.value = previous;
  }
};

const updateAccountSelects = () => {
  const sorted = [...state.reference.accounts].sort((a, b) => a.name.localeCompare(b.name));
  populateSelect(document.querySelector(selectors.transactionAccountSelect), sorted, { valueKey: "account_id", labelKey: "name" }, "Select account");
  populateSelect(document.querySelector(selectors.transferSourceSelect), sorted, { valueKey: "account_id", labelKey: "name" }, "Select source");
  populateSelect(document.querySelector(selectors.transferDestinationSelect), sorted, { valueKey: "account_id", labelKey: "name" }, "Select destination");
};

const getCategoryOptions = () => {
  const source = state.budgets.categories.length ? state.budgets.categories : state.reference.categories;
  return [...source].filter((category) => category.is_active !== false).sort((a, b) => a.name.localeCompare(b.name));
};

const findBudgetCategory = (categoryId) => state.budgets.categories.find((category) => category.category_id === categoryId);

const getCategoryAvailableMinor = (categoryId) => {
  const category = findBudgetCategory(categoryId);
  return category ? category.available_minor ?? 0 : 0;
};

const getCategoryDisplayName = (categoryId) => {
  if (!categoryId) {
    return "Ready to Assign";
  }
  const category = findBudgetCategory(categoryId) || state.reference.categories.find((cat) => cat.category_id === categoryId);
  return category ? category.name : categoryId;
};

const updateCategorySelects = () => {
  const categories = getCategoryOptions();
  populateSelect(document.querySelector(selectors.transactionCategorySelect), categories, { valueKey: "category_id", labelKey: "name" }, "Select category");
  populateSelect(document.querySelector(selectors.transferCategorySelect), categories, { valueKey: "category_id", labelKey: "name" }, "Select category");
  populateSelect(document.querySelector(selectors.allocationToSelect), categories, { valueKey: "category_id", labelKey: "name" }, "Select category");
  const fromSelect = document.querySelector(selectors.allocationFromSelect);
  if (fromSelect) {
    const previous = fromSelect.value;
    const fragment = document.createDocumentFragment();
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Ready to Assign";
    fragment.appendChild(defaultOption);
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category.category_id;
      option.textContent = category.name;
      fragment.appendChild(option);
    });
    fromSelect.innerHTML = "";
    fromSelect.appendChild(fragment);
    if (previous && categories.some((category) => category.category_id === previous)) {
      fromSelect.value = previous;
    } else {
      fromSelect.value = "";
    }
  }
};

const updateHeaderStats = () => {
  const spendEl = document.querySelector(selectors.monthSpend);
  if (spendEl) {
    spendEl.textContent = formatAmount(computeCurrentMonthSpend(state.transactions));
  }

  const budgetedEl = document.querySelector(selectors.monthBudgeted);
  if (budgetedEl) {
    budgetedEl.textContent = formatAmount(state.budgets.allocatedMinor ?? 0);
  }
};

const setInlineRowBusy = (row, busy) => {
  if (!row) {
    return;
  }
  row.classList.toggle("is-saving", Boolean(busy));
};

const bindInlineEscHandler = (transactionVersionId) => {
  if (detachInlineEscHandler) {
    detachInlineEscHandler();
  }
  const handler = (event) => {
    if (event.key !== "Escape") {
      return;
    }
    if (state.editingTransactionId !== transactionVersionId) {
      return;
    }
    event.preventDefault();
    cancelInlineTransactionEdit();
  };
  document.addEventListener("keydown", handler, true);
  detachInlineEscHandler = () => {
    document.removeEventListener("keydown", handler, true);
    detachInlineEscHandler = null;
  };
};

const applyStatusToggleState = (toggle, state) => {
  if (!toggle) {
    return;
  }
  const nextState = state === "cleared" ? "cleared" : "pending";
  toggle.dataset.state = nextState;
  toggle.classList.toggle("is-cleared", nextState === "cleared");
  toggle.classList.toggle("is-pending", nextState !== "cleared");
  const isSwitch = toggle.getAttribute("role") === "switch";
  if (isSwitch) {
    toggle.setAttribute("aria-checked", nextState === "cleared" ? "true" : "false");
  }
  const labelText = nextState === "cleared" ? "Status: Cleared" : "Status: Pending";
  toggle.setAttribute("title", labelText);
  toggle.setAttribute("aria-label", labelText);
};

const initializeStatusToggle = (toggle, initialState = "pending") => {
  if (!toggle) {
    return;
  }
  applyStatusToggleState(toggle, initialState);
  const handleToggle = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const nextState = toggle.dataset.state === "cleared" ? "pending" : "cleared";
    applyStatusToggleState(toggle, nextState);
  };
  toggle.addEventListener("click", handleToggle);
  toggle.addEventListener("keydown", (event) => {
    if (event.key === " " || event.key === "Spacebar" || event.key === "Enter") {
      handleToggle(event);
    }
  });
};

const startInlineTransactionEdit = (transaction) => {
  if (!transaction) {
    return;
  }
  state.editingTransactionId = transaction.transaction_version_id;
  state.forms.transactionEdit.conceptId = transaction.concept_id || null;
  state.forms.transactionEdit.transactionId = transaction.transaction_version_id || null;
  bindInlineEscHandler(transaction.transaction_version_id);
  renderTransactions(transactionsBodyEl, state.transactions);
};

const cancelInlineTransactionEdit = () => {
  state.editingTransactionId = null;
  state.forms.transactionEdit.conceptId = null;
  state.forms.transactionEdit.transactionId = null;
  if (detachInlineEscHandler) {
    detachInlineEscHandler();
  }
  renderTransactions(transactionsBodyEl, state.transactions);
};

const hydrateInlineEditRow = (row, transaction) => {
  if (!row || !transaction) {
    return;
  }
  row.classList.add("inline-edit-row");
  const errorEl = row.querySelector("[data-inline-error]");
  setFormError(errorEl, "");
  const accountSelect = row.querySelector("[data-inline-account]");
  if (accountSelect) {
    const sortedAccounts = [...state.reference.accounts].sort((a, b) => a.name.localeCompare(b.name));
    populateSelect(accountSelect, sortedAccounts, { valueKey: "account_id", labelKey: "name" }, "Select account");
    accountSelect.value = transaction.account_id || "";
  }
  const categorySelect = row.querySelector("[data-inline-category]");
  if (categorySelect) {
    const categories = getCategoryOptions();
    populateSelect(categorySelect, categories, { valueKey: "category_id", labelKey: "name" }, "Select category");
    categorySelect.value = transaction.category_id || "";
  }
  const dateInput = row.querySelector("[data-inline-date]");
  if (dateInput) {
    dateInput.value = transaction.transaction_date || todayISO();
  }
  const memoInput = row.querySelector("[data-inline-memo]");
  if (memoInput) {
    memoInput.value = transaction.memo || "";
  }
  const inflowInput = row.querySelector("[data-inline-inflow]");
  const outflowInput = row.querySelector("[data-inline-outflow]");
  if (inflowInput || outflowInput) {
    const amountMinor = transaction.amount_minor ?? 0;
    if (outflowInput) {
      outflowInput.value = amountMinor < 0 ? minorToDollars(Math.abs(amountMinor)) : "";
    }
    if (inflowInput) {
      inflowInput.value = amountMinor >= 0 ? minorToDollars(Math.abs(amountMinor)) : "";
    }
    const enforceExclusiveAmount = (source, target) => {
      if (!source || !target) {
        return;
      }
      source.addEventListener("input", () => {
        if (source.value && source.value.trim() !== "") {
          target.value = "";
        }
      });
    };
    enforceExclusiveAmount(inflowInput, outflowInput);
    enforceExclusiveAmount(outflowInput, inflowInput);
  }
  const statusToggle = row.querySelector("[data-inline-status-toggle]");
  initializeStatusToggle(statusToggle, transaction.status === "cleared" ? "cleared" : "pending");

  const keyHandler = (event) => {
    const isStatusToggle = event.target?.closest?.("[data-inline-status-toggle]");
    if (event.key === "Enter" && !event.shiftKey && !isStatusToggle) {
      event.preventDefault();
      handleInlineTransactionSave(row, transaction);
    }
  };
  row.addEventListener("keydown", keyHandler);
  window.requestAnimationFrame(() => {
    dateInput?.focus();
  });
};

const handleInlineTransactionSave = async (row, transaction) => {
  if (!row || !transaction) {
    return;
  }
  if (state.forms.transactionEdit.submitting) {
    return;
  }
  const errorEl = row.querySelector("[data-inline-error]");
  const dateInput = row.querySelector("[data-inline-date]");
  const accountSelect = row.querySelector("[data-inline-account]");
  const categorySelect = row.querySelector("[data-inline-category]");
  const memoInput = row.querySelector("[data-inline-memo]");
  const inflowInput = row.querySelector("[data-inline-inflow]");
  const outflowInput = row.querySelector("[data-inline-outflow]");
  const statusToggle = row.querySelector("[data-inline-status-toggle]");
  const conceptId = transaction.concept_id || state.forms.transactionEdit.conceptId;
  if (!conceptId) {
    setFormError(errorEl, "Missing concept identifier for edit.");
    return;
  }
  if (!accountSelect?.value || !categorySelect?.value) {
    setFormError(errorEl, "Account and category are required.");
    return;
  }
  if (!inflowInput && !outflowInput) {
    setFormError(errorEl, "Amount inputs are missing.");
    return;
  }
  const inflowMinor = inflowInput ? Math.abs(dollarsToMinor(inflowInput.value)) : 0;
  const outflowMinor = outflowInput ? Math.abs(dollarsToMinor(outflowInput.value)) : 0;
  if (inflowMinor > 0 && outflowMinor > 0) {
    setFormError(errorEl, "Enter either an inflow or an outflow, not both.");
    return;
  }
  const pickedAmountMinor = inflowMinor || outflowMinor;
  if (pickedAmountMinor === 0) {
    setFormError(errorEl, "Amount must be non-zero.");
    return;
  }
  const signedAmount = inflowMinor ? Math.abs(pickedAmountMinor) : -Math.abs(pickedAmountMinor);
  const payload = {
    concept_id: conceptId,
    transaction_date: dateInput?.value || todayISO(),
    account_id: accountSelect.value,
    category_id: categorySelect.value,
    memo: (memoInput?.value || "").trim() || null,
    amount_minor: signedAmount,
    status: statusToggle?.dataset.state === "cleared" ? "cleared" : "pending",
  };
  try {
    state.forms.transactionEdit.submitting = true;
    setInlineRowBusy(row, true);
    setFormError(errorEl, "");
    await fetchJSON("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.editingTransactionId = null;
    state.forms.transactionEdit.conceptId = null;
    state.forms.transactionEdit.transactionId = null;
    if (detachInlineEscHandler) {
      detachInlineEscHandler();
    }
    await Promise.all([refreshTransactions(transactionsBodyEl), refreshAccountsPage(), loadBudgetsData()]);
    updateCategorySelects();
    renderBudgetsPage();
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save changes.");
  } finally {
    state.forms.transactionEdit.submitting = false;
    setInlineRowBusy(row, false);
  }
};

const renderTransactions = (bodyEl, transactions) => {
  bodyEl.innerHTML = "";
  if (!Array.isArray(transactions) || !transactions.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "muted";
    cell.style.textAlign = "center";
    cell.textContent = "No transactions found.";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }

  transactions.forEach((tx) => {
    if (!tx) return;
    const row = document.createElement("tr");
    const isEditing = state.editingTransactionId === tx.transaction_version_id;
    if (isEditing) {
      row.innerHTML = `
        <td><input type="date" data-inline-date /></td>
        <td>
          <select data-inline-account>
            <option value="" disabled>Select account</option>
          </select>
        </td>
        <td>
          <select data-inline-category>
            <option value="" disabled>Select category</option>
          </select>
        </td>
        <td>
          <input type="text" data-inline-memo placeholder="Optional memo" />
          <p class="inline-row-feedback" data-inline-error aria-live="polite"></p>
        </td>
        <td class="amount-cell amount-edit-cell">
          <input
            type="number"
            step="0.01"
            inputmode="decimal"
            placeholder="0.00"
            data-inline-outflow
            aria-label="Outflow amount"
          />
        </td>
        <td class="amount-cell amount-edit-cell">
          <input
            type="number"
            step="0.01"
            inputmode="decimal"
            placeholder="0.00"
            data-inline-inflow
            aria-label="Inflow amount"
          />
        </td>
        <td>
          <button
            type="button"
            class="status-toggle-badge is-pending"
            data-inline-status-toggle
            data-state="pending"
            role="switch"
            aria-checked="false"
            tabindex="0"
          >
            ${statusToggleIcons}
          </button>
        </td>
      `;
      hydrateInlineEditRow(row, tx);
    } else {
      const statusValue = tx.status === "cleared" ? "cleared" : "pending";
      const amountMinor = tx.amount_minor ?? 0;
      const outflowDisplay = amountMinor < 0 ? formatAmount(Math.abs(amountMinor)) : "—";
      const inflowDisplay = amountMinor >= 0 ? formatAmount(Math.abs(amountMinor)) : "—";
      row.innerHTML = `
        <td>${tx.transaction_date || "N/A"}</td>
        <td>${tx.account_name || "N/A"}</td>
        <td>${tx.category_name || "N/A"}</td>
        <td>${tx.memo || "—"}</td>
        <td class="amount-cell">${outflowDisplay}</td>
        <td class="amount-cell">${inflowDisplay}</td>
        <td>
          <button
            type="button"
            class="status-toggle-badge"
            data-status-display
            data-state="${statusValue}"
            role="status"
            aria-disabled="true"
            tabindex="-1"
          >
            ${statusToggleIcons}
          </button>
        </td>
      `;
      row.dataset.conceptId = tx.concept_id || "";
      row.dataset.transactionId = tx.transaction_version_id || "";
      row.addEventListener("click", (event) => {
        startInlineTransactionEdit(tx);
      });
      const displayToggle = row.querySelector("[data-status-display]");
      applyStatusToggleState(displayToggle, statusValue);
    }
    bodyEl.appendChild(row);
  });
};

const refreshTransactions = async (bodyEl = document.querySelector(selectors.transactionsBody)) => {
  if (!bodyEl) {
    return;
  }
  const data = await fetchJSON("/api/transactions?limit=100");
  state.transactions = (data || []).sort((a, b) => {
    const dateA = a.transaction_date ? new Date(a.transaction_date) : 0;
    const dateB = b.transaction_date ? new Date(b.transaction_date) : 0;
    return dateB - dateA;
  });
  renderTransactions(bodyEl, state.transactions);
  updateHeaderStats();
};

const fetchAccounts = async () => {
  const accounts = await fetchJSON("/api/accounts");
  state.accounts = (accounts || []).filter((acct) => acct.is_active);
};

const fetchNetWorth = async () => {
  state.netWorth = await fetchJSON("/api/net-worth/current");
};

const fetchReadyToAssign = async () => {
  state.readyToAssign = await fetchJSON("/api/budget/ready-to-assign");
};

const loadReferenceData = async () => {
  try {
    const reference = await fetchJSON("/api/reference-data");
    state.reference.accounts = reference?.accounts ?? [];
    state.reference.categories = reference?.categories ?? [];
    updateAccountSelects();
    updateCategorySelects();
  } catch (error) {
    console.error("Failed to load reference data", error);
  }
};

const updateAccountStats = () => {
  const assetsEl = document.querySelector(selectors.assetsTotal);
  const liabilitiesEl = document.querySelector(selectors.liabilitiesTotal);
  const netWorthEl = document.querySelector(selectors.netWorth);
  const readyEl = document.querySelector(selectors.readyToAssign);

  if (state.netWorth) {
    if (assetsEl) {
      assetsEl.textContent = formatAmount(state.netWorth.assets_minor);
    }
    if (liabilitiesEl) {
      liabilitiesEl.textContent = formatAmount(-state.netWorth.liabilities_minor);
    }
    if (netWorthEl) {
      netWorthEl.textContent = formatAmount(state.netWorth.net_worth_minor);
    }
  }

  if (readyEl) {
    if (state.readyToAssign) {
      readyEl.textContent = formatAmount(state.readyToAssign.ready_to_assign_minor);
    } else {
      readyEl.textContent = "—";
    }
  }
};

const slugify = (value) => {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  const trimmed = normalized.replace(/^_+|_+$/g, "");
  return `${trimmed || "account"}_${Date.now().toString(36)}`;
};

const slugifyCategoryName = (value) => {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  return normalized.replace(/^_+|_+$/g, "") || "category";
};

const groupAccounts = () => {
  return accountGroupDefinitions.map((group) => ({
    ...group,
    accounts: state.accounts.filter((account) => account.account_class === group.id),
  }));
};

const getFilteredGroups = () => {
  const groups = groupAccounts();
  const scope =
    state.accountFilter === "all"
      ? groups
      : groups.filter((group) => (state.accountFilter === "assets" ? group.type === "asset" : group.type === "liability"));
  return scope.filter((group) => group.accounts.length > 0);
};

const formatRoleLabel = (role) => (role === "on_budget" ? "On-budget" : "Tracking");

const renderAccountGroups = () => {
  const container = document.querySelector(selectors.accountGroups);
  if (!container) {
    return;
  }

  const groups = getFilteredGroups();
  if (!groups.length) {
    container.innerHTML = "<p class=\"muted\">No accounts available.</p>";
    return;
  }

  container.innerHTML = groups
    .map((group) => {
      const cards = group.accounts
        .map(
          (account) => `
            <div class="account-card" data-account-id="${account.account_id}">
              <div class="account-card__header">
                <div class="account-card__title">
                  <span class="account-card__name">${account.name}</span>
                  <span class="account-card__role-icon" data-role="${account.account_role}" aria-label="${formatRoleLabel(
                    account.account_role
                  )}"></span>
                </div>
                <span class="account-card__balance">${formatAmount(
                  account.account_type === "liability" ? -account.current_balance_minor : account.current_balance_minor
                )}</span>
              </div>
              <div class="account-card__meta">
                <span>${account.account_class.replace(/_/g, " ")}</span>
                <span>${account.account_type === "asset" ? "Asset" : "Liability"}</span>
              </div>
            </div>
          `
        )
        .join("");

      return `
        <article class="account-group">
          <header class="account-group__header">
            <div>
              <p class="account-group__title">${group.title}</p>
              <p class="muted">${group.description}</p>
            </div>
            <span class="muted">${group.accounts.length} account${group.accounts.length === 1 ? "" : "s"}</span>
          </header>
          <div class="account-cards">
            ${cards || `<p class=\"muted\">No accounts in this section yet.</p>`}
          </div>
        </article>
      `;
    })
    .join("");

  container
    .querySelectorAll(".account-card")
    .forEach((card) => {
      card.addEventListener("click", () => {
        const accountId = card.getAttribute("data-account-id");
        const account = state.accounts.find((acc) => acc.account_id === accountId);
        if (account) {
          showAccountDetail(account);
        }
      });
    });
};




const setFormError = (element, message) => {
  if (!element) {
    return;
  }
  element.textContent = message || "";
};

const setButtonBusy = (button, busy) => {
  if (!button) {
    return;
  }
  button.disabled = busy;
  button.setAttribute("aria-busy", busy ? "true" : "false");
};

const formatBudgetDisplay = (minor) => formatAmount(minor);

const showToast = (message) => {
  const stack = document.querySelector(selectors.toastStack);
  if (!stack) {
    return;
  }
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  stack.appendChild(toast);
  window.setTimeout(() => {
    toast.remove();
  }, 6000);
};

const modalOverlay = document.querySelector(selectors.accountModal);
const modalElement = modalOverlay?.querySelector(".modal");
const modalTitle = document.querySelector(selectors.accountModalTitle);
const modalLabel = document.querySelector(selectors.accountModalLabel);
const modalSubtitle = document.querySelector(selectors.accountModalSubtitle);
const modalMetadata = document.querySelector(selectors.accountModalMetadata);
const modalBalance = document.querySelector(selectors.accountModalBalance);

const setModalView = (view) => {
  if (!modalOverlay) return;
  modalOverlay.dataset.view = view;
  if (modalElement) {
    modalElement.dataset.view = view;
  }
};

const toggleAccountModal = (show, view = "add") => {
  if (!modalOverlay) return;
  modalOverlay.classList.toggle("is-visible", show);
  modalOverlay.style.display = show ? "flex" : "none";
  modalOverlay.setAttribute("aria-hidden", show ? "false" : "true");
  setModalView(show ? view : modalOverlay.dataset.view || "add");
};

const showAccountDetail = (account) => {
  modalLabel.textContent = "Account detail";
  modalTitle.textContent = account.name;
  modalSubtitle.textContent = `ID • ${account.account_id}`;
  if (modalBalance) {
    modalBalance.textContent = formatAmount(account.current_balance_minor);
  }
  if (modalMetadata) {
    modalMetadata.innerHTML = `
      <li><strong>Type</strong><span>${account.account_type === "asset" ? "Asset" : "Liability"}</span></li>
      <li><strong>Class</strong><span>${account.account_class.replace(/_/g, " ")}</span></li>
      <li><strong>Role</strong><span>${formatRoleLabel(account.account_role)}</span></li>
    `;
  }
  toggleAccountModal(true, "detail");
};

const showAddAccountModal = () => {
  modalLabel.textContent = "Add account";
  modalTitle.textContent = "Follow the guided steps";
  modalSubtitle.textContent = "Create a new asset or liability";
  toggleAccountModal(true, "add");
};

const handleAddAccount = async () => {
  const formData = {};
  const nameInput = document.querySelector(selectors.modalNameInput);
  const balanceInput = document.querySelector(selectors.modalBalanceInput);
  const typeSelect = document.querySelector(selectors.modalTypeSelect);

  if (!nameInput || !balanceInput || !typeSelect) return;

  const name = nameInput.value.trim();
  if (!name) {
    alert("Please provide an account name.");
    return;
  }

  const mapping = accountTypeMapping[typeSelect.value];
  if (!mapping) {
    alert("Please choose a valid account type.");
    return;
  }

  const parsedBalance = Number.parseFloat(balanceInput.value) || 0;
  const balanceMinor = Math.round(parsedBalance * 100);
  const accountId = slugify(name);

  const payload = {
    account_id: accountId,
    name,
    account_type: mapping.account_type,
    account_class: mapping.account_class,
    account_role: mapping.account_role,
    current_balance_minor: balanceMinor,
    currency: "USD",
  };

  try {
    await fetchJSON("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    nameInput.value = "";
    balanceInput.value = "";
    toggleAccountModal(false);
    await refreshAccountsPage();
    await loadReferenceData();
  } catch (error) {
    console.error(error);
    alert(error.message || "Failed to create account.");
  }
};

const refreshAccountsPage = async () => {
  try {
    await fetchAccounts();
    await fetchNetWorth();
    await fetchReadyToAssign();
    updateAccountStats();
    renderAccountGroups();
  } catch (error) {
    console.error("Failed to refresh account data", error);
  }
};

const loadBudgetsData = async () => {
  const month = currentMonthStartISO();
  try {
    const [categories, groups, ready] = await Promise.all([
      fetchJSON(`/api/budget-categories?month=${month}`),
      fetchJSON("/api/budget-category-groups"),
      fetchJSON(`/api/budget/ready-to-assign?month=${month}`),
    ]);
    state.budgets.categories = (categories || []).map((category) => ({
      ...category,
      available_minor: category.available_minor ?? 0,
      activity_minor: category.activity_minor ?? 0,
      allocated_minor: category.allocated_minor ?? 0,
    }));
    state.budgets.groups = (groups || []).sort((a, b) => a.sort_order - b.sort_order);
    state.budgets.readyToAssignMinor = ready?.ready_to_assign_minor ?? 0;
    state.budgets.activityMinor = state.budgets.categories.reduce((total, category) => total + (category.activity_minor ?? 0), 0);
    state.budgets.availableMinor = state.budgets.categories.reduce((total, category) => total + (category.available_minor ?? 0), 0);
    state.budgets.allocatedMinor = state.budgets.categories.reduce((total, category) => total + (category.allocated_minor ?? 0), 0);
    state.budgets.monthStartISO = month;
    const monthDate = new Date(`${month}T00:00:00`);
    state.budgets.monthLabel = monthDate.toLocaleDateString(undefined, { year: "numeric", month: "long" });
    state.readyToAssign = ready;
    updateCategorySelects();
    updateAccountStats();
    updateHeaderStats();
  } catch (error) {
    console.error("Failed to load budgets data", error);
    throw error;
  }
};

const loadAllocationsData = async () => {
  const month = currentMonthStartISO();
  try {
    const data = await fetchJSON(`/api/budget/allocations?month=${month}`);
    state.allocations.entries = data?.allocations ?? [];
    state.allocations.inflowMinor = data?.inflow_minor ?? 0;
    state.allocations.readyMinor = data?.ready_to_assign_minor ?? 0;
    state.allocations.monthStartISO = data?.month_start ?? month;
    const labelDate = new Date(`${state.allocations.monthStartISO}T00:00:00`);
    state.allocations.monthLabel = labelDate.toLocaleDateString(undefined, { year: "numeric", month: "long" });
  } catch (error) {
    console.error("Failed to load allocations", error);
    throw error;
  }
};

const renderBudgetsPage = () => {
  const readyEl = document.querySelector(selectors.budgetsReadyValue);
  const activityEl = document.querySelector(selectors.budgetsActivityValue);
  const availableEl = document.querySelector(selectors.budgetsAvailableValue);
  const monthLabelEl = document.querySelector(selectors.budgetsMonthLabel);
  if (readyEl) {
    readyEl.textContent = formatBudgetDisplay(state.budgets.readyToAssignMinor);
  }
  if (activityEl) {
    activityEl.textContent = formatBudgetDisplay(state.budgets.activityMinor);
  }
  if (availableEl) {
    availableEl.textContent = formatBudgetDisplay(state.budgets.availableMinor);
  }
  if (monthLabelEl) {
    monthLabelEl.textContent = state.budgets.monthLabel || "—";
  }
  const body = document.querySelector("#budgets-body");
  if (!body) {
    return;
  }
  
  const groups = state.budgets.groups;
  const categories = state.budgets.categories;
  const grouped = {};

  groups.forEach((g) => (grouped[g.group_id] = { ...g, items: [] }));
  grouped["uncategorized"] = { group_id: "uncategorized", name: "Uncategorized", items: [] };

  categories.forEach((cat) => {
    const gid = cat.group_id || "uncategorized";
    if (!grouped[gid]) {
      grouped[gid] = { group_id: gid, name: "Unknown Group", items: [] };
    }
    grouped[gid].items.push(cat);
  });

  body.innerHTML = "";

  const renderGroup = (group) => {
    if (group.group_id === "uncategorized" && group.items.length === 0) return;

    const groupRow = document.createElement("tr");
    groupRow.className = "group-row";
    groupRow.style.cursor = "pointer";
    groupRow.dataset.groupId = group.group_id;
    groupRow.innerHTML = `
      <td colspan="4" class="group-cell" style="background-color: var(--stone-50); font-weight: 600;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>${group.name}</span>
        </div>
      </td>
    `;
    body.appendChild(groupRow);

    group.items.forEach((cat) => {
      const row = document.createElement("tr");
      row.style.cursor = "pointer";
      row.dataset.categoryId = cat.category_id;
      
      let goalText = "";
      if (cat.goal_type === "target_date" && cat.goal_amount_minor) {
        goalText = `<div class="small-note muted">Goal: ${formatAmount(cat.goal_amount_minor)} by ${cat.goal_target_date || "?"}</div>`;
      } else if (cat.goal_type === "recurring" && cat.goal_amount_minor) {
        const freq = cat.goal_frequency ? cat.goal_frequency.charAt(0).toUpperCase() + cat.goal_frequency.slice(1) : "Recurring";
        goalText = `<div class="small-note muted">${freq}: ${formatAmount(cat.goal_amount_minor)}</div>`;
      }

      row.innerHTML = `
        <td>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span>${cat.name}</span>
              ${goalText}
            </div>
          </div>
        </td>
        <td class="amount-cell">${formatBudgetDisplay(cat.allocated_minor)}</td>
        <td class="amount-cell">${formatBudgetDisplay(cat.activity_minor)}</td>
        <td class="amount-cell">
          <span class="${cat.available_minor < 0 ? "form-error" : ""}">${formatBudgetDisplay(cat.available_minor)}</span>
        </td>
      `;
      body.appendChild(row);
    });
  };

  groups.forEach((g) => renderGroup(grouped[g.group_id]));
  if (grouped["uncategorized"].items.length > 0) {
    renderGroup(grouped["uncategorized"]);
  }

  // Attach click listeners to rows
  body.querySelectorAll("tr[data-group-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const gid = row.dataset.groupId;
      if (gid === "uncategorized") {
        openGroupDetailModal(grouped["uncategorized"]);
      } else {
        const group = state.budgets.groups.find((g) => g.group_id === gid);
        if (group) openGroupDetailModal(grouped[gid]);
      }
    });
  });

  body.querySelectorAll("tr[data-category-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const cid = row.dataset.categoryId;
      const cat = state.budgets.categories.find((c) => c.category_id === cid);
      if (cat) openBudgetDetailModal(cat);
    });
  });
};

const renderAllocationsPage = () => {
  const inflowEl = document.querySelector(selectors.allocationInflowValue);
  const readyEl = document.querySelector(selectors.allocationReadyValue);
  const monthEl = document.querySelector(selectors.allocationMonthLabel);
  if (inflowEl) {
    inflowEl.textContent = formatBudgetDisplay(state.allocations.inflowMinor);
  }
  if (readyEl) {
    readyEl.textContent = formatBudgetDisplay(state.allocations.readyMinor);
  }
  if (monthEl) {
    monthEl.textContent = state.allocations.monthLabel || "—";
  }
  const body = document.querySelector(selectors.allocationsBody);
  if (body) {
    body.innerHTML = "";
    if (!state.allocations.entries.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5" class="muted">No allocations recorded for this month.</td>';
      body.appendChild(row);
    } else {
      state.allocations.entries.forEach((entry) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${entry.allocation_date || "—"}</td>
          <td class="amount-cell">${formatAmount(entry.amount_minor ?? 0)}</td>
          <td>${entry.from_category_name || getCategoryDisplayName(entry.from_category_id)}</td>
          <td>${entry.to_category_name || getCategoryDisplayName(entry.to_category_id)}</td>
          <td>${entry.memo || "—"}</td>
        `;
        body.appendChild(row);
      });
    }
  }
  const dateInput = document.querySelector(selectors.allocationDateInput);
  if (dateInput && !dateInput.value) {
    dateInput.value = todayISO();
  }
  const toSelect = document.querySelector(selectors.allocationToSelect);
  if (toSelect && state.forms.allocation.pendingToCategory) {
    toSelect.value = state.forms.allocation.pendingToCategory;
    state.forms.allocation.pendingToCategory = null;
  }
};


const handleAllocationFormSubmit = async (event) => {
  event.preventDefault();
  if (state.forms.allocation.submitting) {
    return;
  }
  const form = event.currentTarget;
  const formData = new FormData(form);
  const toCategoryId = formData.get("to_category_id");
  const fromCategoryId = formData.get("from_category_id") || null;
  const allocationDate = formData.get("allocation_date") || todayISO();
  const memo = (formData.get("memo") || "").toString().trim();
  const amountMinor = Math.abs(dollarsToMinor(formData.get("amount")));
  const errorEl = document.querySelector(selectors.allocationError);
  setFormError(errorEl, "");
  if (!toCategoryId) {
    setFormError(errorEl, "Choose the destination category.");
    return;
  }
  if (fromCategoryId && fromCategoryId === toCategoryId) {
    setFormError(errorEl, "Source and destination categories must differ.");
    return;
  }
  if (amountMinor === 0) {
    setFormError(errorEl, "Amount must be greater than zero.");
    return;
  }
  if (fromCategoryId) {
    const available = getCategoryAvailableMinor(fromCategoryId);
    if (available < amountMinor) {
      setFormError(errorEl, "Source category does not have enough available funds.");
      return;
    }
  } else if (state.budgets.readyToAssignMinor < amountMinor) {
    setFormError(errorEl, "Ready-to-Assign is insufficient for this allocation.");
    return;
  }

  const payload = {
    to_category_id: toCategoryId,
    from_category_id: fromCategoryId || null,
    amount_minor: amountMinor,
    allocation_date: allocationDate,
    memo: memo || null,
  };
  const button = document.querySelector(selectors.allocationSubmit);
  try {
    state.forms.allocation.submitting = true;
    setButtonBusy(button, true);
    await fetchJSON("/api/budget/allocations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const amountInput = form.querySelector("input[name='amount']");
    if (amountInput) {
      amountInput.value = "";
      amountInput.focus();
    }
    setFormError(errorEl, "");
    await Promise.all([
      loadAllocationsData(),
      loadBudgetsData(),
      refreshAccountsPage(),
    ]);
    renderAllocationsPage();
    renderBudgetsPage();
    updateCategorySelects();
    const fromLabel = getCategoryDisplayName(fromCategoryId);
    const toLabel = getCategoryDisplayName(toCategoryId);
    showToast(`Moved ${formatAmount(Math.abs(payload.amount_minor))} from ${fromLabel} to ${toLabel}`);
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Allocation failed.");
  } finally {
    state.forms.allocation.submitting = false;
    setButtonBusy(button, false);
  }
};

const openGroupModal = (group = null) => {
  const modal = document.querySelector(selectors.groupModal);
  const title = document.querySelector(selectors.groupModalTitle);
  const form = document.querySelector(selectors.groupForm);
  const errorEl = document.querySelector(selectors.groupError);
  if (!modal || !form) return;

  state.pendingGroupEdit = group;
  setFormError(errorEl, "");

  const nameInput = form.querySelector("input[name='name']");
  const sortInput = form.querySelector("input[name='sort_order']");

  if (group) {
    title.textContent = "Edit Group";
    nameInput.value = group.name;
    sortInput.value = group.sort_order;
  } else {
    title.textContent = "Add Group";
    nameInput.value = "";
    sortInput.value = 0;
  }

  modal.classList.add("is-visible");
  modal.style.display = "flex";
  modal.setAttribute("aria-hidden", "false");
  nameInput.focus();
};

const closeGroupModal = () => {
  const modal = document.querySelector(selectors.groupModal);
  if (!modal) return;
  modal.classList.remove("is-visible");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
  state.pendingGroupEdit = null;
};

const handleGroupFormSubmit = async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const name = formData.get("name").trim();
  const sortOrder = parseInt(formData.get("sort_order"), 10) || 0;
  const errorEl = document.querySelector(selectors.groupError);
  const submitButton = document.querySelector(selectors.groupSubmit);

  if (!name) {
    setFormError(errorEl, "Name is required.");
    return;
  }

  try {
    setButtonBusy(submitButton, true);
    setFormError(errorEl, "");
    const isEditing = Boolean(state.pendingGroupEdit);

    if (isEditing) {
      await fetchJSON(`/api/budget-category-groups/${state.pendingGroupEdit.group_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, sort_order: sortOrder, is_active: true }),
      });
    } else {
      const groupId = slugify(name);
      await fetchJSON("/api/budget-category-groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ group_id: groupId, name, sort_order: sortOrder, is_active: true }),
      });
    }
    closeGroupModal();
    await loadBudgetsData();
    renderBudgetsPage();
    showToast(isEditing ? `Updated ${name}` : `Created ${name}`);
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save group.");
  } finally {
    setButtonBusy(submitButton, false);
  }
};

const initGroupModal = () => {
  const modal = document.querySelector(selectors.groupModal);
  if (!modal) return;
  const form = document.querySelector(selectors.groupForm);
  form?.addEventListener("submit", handleGroupFormSubmit);
  const closeButton = document.querySelector(selectors.groupModalClose);
  closeButton?.addEventListener("click", () => closeGroupModal());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeGroupModal();
  });
};

const handleQuickAllocation = async (categoryId, amountMinor) => {
  if (state.budgets.readyToAssignMinor < amountMinor) {
    alert("Not enough Ready to Assign funds.");
    return;
  }
  const payload = {
    to_category_id: categoryId,
    amount_minor: amountMinor,
    allocation_date: todayISO(),
    memo: "Quick allocation",
  };
  try {
    await fetchJSON("/api/budget/allocations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    closeBudgetDetailModal();
    await Promise.all([loadBudgetsData(), loadAllocationsData(), refreshAccountsPage()]);
    renderBudgetsPage();
    renderAllocationsPage();
    showToast(`Allocated ${formatAmount(amountMinor)}`);
  } catch (error) {
    console.error(error);
    alert(error.message || "Allocation failed.");
  }
};

const openBudgetDetailModal = (category) => {
  const modal = document.querySelector(selectors.budgetDetailModal);
  if (!modal) return;

  state.activeBudgetDetail = category;

  document.querySelector(selectors.budgetDetailTitle).textContent = category.name;

  // available = leftover + allocated + activity (activity is negative)
  // leftover = available - allocated - activity
  const leftover = category.available_minor - category.allocated_minor - category.activity_minor;
  
  document.querySelector(selectors.budgetDetailLeftover).textContent = formatAmount(leftover);
  document.querySelector(selectors.budgetDetailBudgeted).textContent = formatAmount(category.allocated_minor);
  document.querySelector(selectors.budgetDetailActivity).textContent = formatAmount(category.activity_minor);
  document.querySelector(selectors.budgetDetailAvailable).textContent = formatAmount(category.available_minor);

  const actionsContainer = document.querySelector(selectors.budgetDetailQuickActions);
  actionsContainer.innerHTML = "";

  if (category.goal_amount_minor && category.goal_amount_minor > 0) {
    const target = category.goal_amount_minor;
    const needed = Math.max(0, target - category.available_minor);

    if (needed > 0) {
      const btn = document.createElement("button");
      btn.className = "secondary";
      btn.textContent = `Fund Goal: ${formatAmount(needed)}`;
      btn.onclick = () => handleQuickAllocation(category.category_id, needed);
      actionsContainer.appendChild(btn);
    } else {
      const p = document.createElement("p");
      p.className = "muted small-note";
      p.textContent = "Goal fully funded.";
      actionsContainer.appendChild(p);
    }
  } else {
      const p = document.createElement("p");
      p.className = "muted small-note";
      p.textContent = "No goal set.";
      actionsContainer.appendChild(p);
  }

  const editBtn = document.querySelector(selectors.budgetDetailEdit);
  editBtn.onclick = () => {
    closeBudgetDetailModal();
    openCategoryModal(category);
  };

  modal.classList.add("is-visible");
  modal.style.display = "flex";
  modal.setAttribute("aria-hidden", "false");
};

const closeBudgetDetailModal = () => {
  const modal = document.querySelector(selectors.budgetDetailModal);
  if (!modal) return;
  modal.classList.remove("is-visible");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
  state.activeBudgetDetail = null;
};

const initBudgetDetailModal = () => {
  const modal = document.querySelector(selectors.budgetDetailModal);
  if (!modal) return;
  const closeButton = document.querySelector(selectors.budgetDetailClose);
  closeButton?.addEventListener("click", () => closeBudgetDetailModal());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeBudgetDetailModal();
  });
};

const handleGroupQuickAllocation = async (group, totalNeeded) => {
  if (state.budgets.readyToAssignMinor < totalNeeded) {
    alert("Not enough Ready to Assign funds.");
    return;
  }

  try {
    // Execute sequentially
    for (const cat of group.items) {
      const needed = Math.max(0, (cat.goal_amount_minor || 0) - cat.available_minor);
      if (needed > 0) {
        await fetchJSON("/api/budget/allocations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            to_category_id: cat.category_id,
            amount_minor: needed,
            allocation_date: todayISO(),
            memo: "Group quick allocation",
          }),
        });
      }
    }
    closeGroupDetailModal();
    await Promise.all([loadBudgetsData(), loadAllocationsData(), refreshAccountsPage()]);
    renderBudgetsPage();
    renderAllocationsPage();
    showToast(`Funded group ${group.name} with ${formatAmount(totalNeeded)}`);
  } catch (error) {
    console.error(error);
    alert("Partial failure during group allocation.");
    await loadBudgetsData();
    renderBudgetsPage();
  }
};

const openGroupDetailModal = (group) => {
  const modal = document.querySelector(selectors.groupDetailModal);
  if (!modal) return;

  document.querySelector(selectors.groupDetailTitle).textContent = group.name;

  let totalLeftover = 0;
  let totalBudgeted = 0;
  let totalActivity = 0;
  let totalAvailable = 0;
  let totalNeeded = 0;

  group.items.forEach((cat) => {
    const leftover = cat.available_minor - cat.allocated_minor - cat.activity_minor;
    totalLeftover += leftover;
    totalBudgeted += cat.allocated_minor;
    totalActivity += cat.activity_minor;
    totalAvailable += cat.available_minor;
    
    if (cat.goal_amount_minor && cat.goal_amount_minor > 0) {
        totalNeeded += Math.max(0, cat.goal_amount_minor - cat.available_minor);
    }
  });

  document.querySelector(selectors.groupDetailLeftover).textContent = formatAmount(totalLeftover);
  document.querySelector(selectors.groupDetailBudgeted).textContent = formatAmount(totalBudgeted);
  document.querySelector(selectors.groupDetailActivity).textContent = formatAmount(totalActivity);
  document.querySelector(selectors.groupDetailAvailable).textContent = formatAmount(totalAvailable);

  const actionsContainer = document.querySelector(selectors.groupDetailQuickActions);
  actionsContainer.innerHTML = "";

  if (totalNeeded > 0) {
    const btn = document.createElement("button");
    btn.className = "secondary";
    btn.textContent = `Fund Underfunded: ${formatAmount(totalNeeded)}`;
    btn.onclick = () => handleGroupQuickAllocation(group, totalNeeded);
    actionsContainer.appendChild(btn);
  } else {
    const p = document.createElement("p");
    p.className = "muted small-note";
    p.textContent = "All goals in this group are fully funded.";
    actionsContainer.appendChild(p);
  }

  const editBtn = document.querySelector(selectors.groupDetailEdit);
  editBtn.onclick = () => {
    closeGroupDetailModal();
    openGroupModal(group);
  };

  modal.classList.add("is-visible");
  modal.style.display = "flex";
  modal.setAttribute("aria-hidden", "false");
};

const closeGroupDetailModal = () => {
  const modal = document.querySelector(selectors.groupDetailModal);
  if (!modal) return;
  modal.classList.remove("is-visible");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
};

const initGroupDetailModal = () => {
  const modal = document.querySelector(selectors.groupDetailModal);
  if (!modal) return;
  const closeButton = document.querySelector(selectors.groupDetailClose);
  closeButton?.addEventListener("click", () => closeGroupDetailModal());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeGroupDetailModal();
  });
};

const initBudgetsInteractions = () => {
  const openModalButton = document.querySelector("[data-open-category-modal]");
  openModalButton?.addEventListener("click", () => openCategoryModal());

  const openGroupButton = document.querySelector("[data-open-group-modal]");
  openGroupButton?.addEventListener("click", () => openGroupModal());

  initBudgetDetailModal();
  initGroupDetailModal();
};

const initAllocationsPage = () => {
  const form = document.querySelector(selectors.allocationForm);
  form?.addEventListener("submit", handleAllocationFormSubmit);
};

const setTransactionFlow = (flow) => {
  state.forms.transaction.flow = flow;
  document.querySelectorAll(selectors.transactionFlowInputs).forEach((input) => {
    const isMatch = input.value === flow;
    input.checked = isMatch;
  });
};

const handleTransactionSubmit = async (event) => {
  event.preventDefault();
  if (state.forms.transaction.submitting) {
    return;
  }
  const form = event.currentTarget;
  const errorEl = document.querySelector(selectors.transactionError);
  const submitButton = document.querySelector(selectors.transactionSubmit);
  setFormError(errorEl, "");
  const formData = new FormData(form);
  const transactionDate = formData.get("transaction_date") || todayISO();
  const categoryId = formData.get("category_id");
  const accountId = formData.get("account_id");
  const memo = (formData.get("memo") || "").toString().trim();
  const amountMinor = Math.abs(dollarsToMinor(formData.get("amount")));
  const flow = state.forms.transaction.flow || "outflow";
  if (!categoryId) {
    setFormError(errorEl, "Category is required.");
    return;
  }
  if (!accountId) {
    setFormError(errorEl, "Account is required.");
    return;
  }
  if (amountMinor === 0) {
    setFormError(errorEl, "Amount must be non-zero.");
    return;
  }
  const signedAmount = flow === "outflow" ? -Math.abs(amountMinor) : Math.abs(amountMinor);
  const payload = {
    transaction_date: transactionDate,
    account_id: accountId,
    category_id: categoryId,
    amount_minor: signedAmount,
    memo: memo || null,
    status: "pending",
  };
  try {
    state.forms.transaction.submitting = true;
    setButtonBusy(submitButton, true);
    await fetchJSON("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const memoInput = form.querySelector("input[name='memo']");
    if (memoInput) {
      memoInput.value = "";
    }
    const amountInput = form.querySelector("input[name='amount']");
    if (amountInput) {
      amountInput.value = "";
      amountInput.focus();
    }
    await Promise.all([refreshTransactions(transactionsBodyEl), refreshAccountsPage(), loadBudgetsData()]);
    updateCategorySelects();
    renderBudgetsPage();
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save transaction.");
  } finally {
    state.forms.transaction.submitting = false;
    setButtonBusy(submitButton, false);
  }
};

const validateTransferForm = () => {
  const form = document.querySelector(selectors.transferForm);
  if (!form) {
    return false;
  }
  const sourceSelect = document.querySelector(selectors.transferSourceSelect);
  const destinationSelect = document.querySelector(selectors.transferDestinationSelect);
  const categorySelect = document.querySelector(selectors.transferCategorySelect);
  const amountInput = form.querySelector("input[name='amount']");
  const source = sourceSelect?.value;
  const destination = destinationSelect?.value;
  const categoryId = categorySelect?.value;
  const amountMinor = Math.abs(dollarsToMinor(amountInput?.value));
  const sourceHelper = form.querySelector('[data-validation="source"]');
  const destinationHelper = form.querySelector('[data-validation="destination"]');
  const identical = source && destination && source === destination;
  if (sourceHelper) {
    sourceHelper.textContent = identical ? "Source and destination must differ." : "";
  }
  if (destinationHelper) {
    destinationHelper.textContent = identical ? "Source and destination must differ." : "";
  }
  const valid = Boolean(source && destination && categoryId && !identical && amountMinor > 0);
  const submitButton = document.querySelector(selectors.transferSubmit);
  if (submitButton) {
    submitButton.disabled = !valid || state.forms.transfer.submitting;
  }
  return valid;
};

const handleTransferSubmit = async (event) => {
  event.preventDefault();
  if (!validateTransferForm() || state.forms.transfer.submitting) {
    return;
  }
  const form = event.currentTarget;
  const errorEl = document.querySelector(selectors.transferError);
  setFormError(errorEl, "");
  const formData = new FormData(form);
  const payload = {
    source_account_id: formData.get("source_account_id"),
    destination_account_id: formData.get("destination_account_id"),
    category_id: formData.get("category_id"),
    transaction_date: formData.get("transaction_date") || todayISO(),
    memo: (formData.get("memo") || "").toString().trim() || null,
    amount_minor: Math.abs(dollarsToMinor(formData.get("amount"))),
  };
  const submitButton = document.querySelector(selectors.transferSubmit);
  try {
    state.forms.transfer.submitting = true;
    setButtonBusy(submitButton, true);
    const response = await fetchJSON("/api/transfers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const amountInput = form.querySelector("input[name='amount']");
    if (amountInput) {
      amountInput.value = "";
    }
    const memoInput = form.querySelector("input[name='memo']");
    if (memoInput) {
      memoInput.value = "";
    }
    setFormError(errorEl, "");
    await Promise.all([refreshTransactions(transactionsBodyEl), refreshAccountsPage(), loadBudgetsData()]);
    renderBudgetsPage();
    showToast(`Transfer ${response.concept_id} posted (${response.budget_leg.transaction_version_id} & ${response.transfer_leg.transaction_version_id})`);
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Transfer failed.");
  } finally {
    state.forms.transfer.submitting = false;
    setButtonBusy(submitButton, false);
    validateTransferForm();
  }
};

const initTransactionForm = () => {
  const form = document.querySelector(selectors.transactionForm);
  if (!form) {
    return;
  }
  const dateInput = form.querySelector("input[name='transaction_date']");
  if (dateInput) {
    dateInput.value = todayISO();
  }
  form.addEventListener("submit", handleTransactionSubmit);
  document.querySelectorAll(selectors.transactionFlowInputs).forEach((input) => {
    input.addEventListener("change", () => {
      setTransactionFlow(input.value);
    });
  });
  setTransactionFlow(state.forms.transaction.flow);
};

const initTransferForm = () => {
  const form = document.querySelector(selectors.transferForm);
  if (!form) {
    return;
  }
  const dateInput = form.querySelector("input[name='transaction_date']");
  if (dateInput) {
    dateInput.value = todayISO();
  }
  form.addEventListener("submit", handleTransferSubmit);
  [selectors.transferSourceSelect, selectors.transferDestinationSelect, selectors.transferCategorySelect].forEach((selector) => {
    document.querySelector(selector)?.addEventListener("change", validateTransferForm);
  });
  form.querySelector("input[name='amount']")?.addEventListener("input", validateTransferForm);
  validateTransferForm();
};

const openCategoryModal = (category = null) => {
  const modal = document.querySelector(selectors.categoryModal);
  const title = document.querySelector(selectors.categoryModalTitle);
  const hint = document.querySelector(selectors.categoryModalHint);
  const nameInput = document.querySelector(selectors.categoryNameInput);
  const slugInput = document.querySelector(selectors.categorySlugInput);
  const groupSelect = document.querySelector(selectors.categoryGroupSelect);
  const errorEl = document.querySelector(selectors.categoryError);
  const form = document.querySelector(selectors.categoryForm);
  
  if (!modal || !title || !hint || !nameInput || !slugInput || !form) {
    return;
  }
  state.pendingCategoryEdit = category;
  categorySlugDirty = false;
  setFormError(errorEl, "");

  if (groupSelect) {
    populateSelect(groupSelect, state.budgets.groups, { valueKey: "group_id", labelKey: "name" }, "Uncategorized");
  }

  // Reset goal fields
  const goalRadios = form.querySelectorAll("input[name='goal_type']");
  goalRadios.forEach(r => r.checked = r.value === "recurring");
  form.querySelector("[data-goal-section='target_date']").style.display = "none";
  form.querySelector("[data-goal-section='recurring']").style.display = "block";
  form.querySelector("input[name='target_date_dt']").value = "";
  form.querySelector("input[name='target_amount']").value = "";
  form.querySelector("select[name='frequency']").value = "monthly";
  form.querySelector("input[name='recurring_date_dt']").value = "";
  form.querySelector("input[name='recurring_amount']").value = "";

  if (category) {
    title.textContent = "Rename category";
    hint.textContent = "Slug edits require migrations, so only the name is editable.";
    nameInput.value = category.name;
    slugInput.value = category.category_id;
    if (groupSelect) groupSelect.value = category.group_id || "";

    // Populate goal
    if (category.goal_type) {
      const radio = form.querySelector(`input[name='goal_type'][value='${category.goal_type}']`);
      if (radio) {
        radio.checked = true;
        const section = form.querySelector(`[data-goal-section='${category.goal_type}']`);
        if (section) section.style.display = "block";
        
        // Hide other sections
        const otherType = category.goal_type === "recurring" ? "target_date" : "recurring";
        const otherSection = form.querySelector(`[data-goal-section='${otherType}']`);
        if (otherSection) otherSection.style.display = "none";
        
        if (category.goal_type === "target_date") {
          form.querySelector("input[name='target_date_dt']").value = category.goal_target_date || "";
          form.querySelector("input[name='target_amount']").value = category.goal_amount_minor ? minorToDollars(category.goal_amount_minor) : "";
        } else if (category.goal_type === "recurring") {
          form.querySelector("select[name='frequency']").value = category.goal_frequency || "monthly";
          form.querySelector("input[name='recurring_date_dt']").value = category.goal_target_date || "";
          form.querySelector("input[name='recurring_amount']").value = category.goal_amount_minor ? minorToDollars(category.goal_amount_minor) : "";
        }
      }
    }
  } else {
    title.textContent = "Add category";
    hint.textContent = "Create a new envelope slug for allocations.";
    nameInput.value = "";
    slugInput.value = "";
    if (groupSelect) groupSelect.value = "";
  }
  modal.classList.add("is-visible");
  modal.style.display = "flex";
  modal.setAttribute("aria-hidden", "false");
  nameInput.focus();
};

const closeCategoryModal = () => {
  const modal = document.querySelector(selectors.categoryModal);
  if (!modal) {
    return;
  }
  modal.classList.remove("is-visible");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
  state.pendingCategoryEdit = null;
};

const handleCategoryFormSubmit = async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const nameInput = document.querySelector(selectors.categoryNameInput);
  const slugInput = document.querySelector(selectors.categorySlugInput);
  const groupSelect = document.querySelector(selectors.categoryGroupSelect);
  const errorEl = document.querySelector(selectors.categoryError);
  const submitButton = document.querySelector(selectors.categorySubmit);
  if (!nameInput || !slugInput) {
    return;
  }
  const name = nameInput.value.trim();
  const slug = slugInput.value.trim();
  const groupId = groupSelect?.value || null;
  if (!name) {
    setFormError(errorEl, "Name is required.");
    return;
  }

  const formData = new FormData(form);
  const goalType = formData.get("goal_type") || "recurring";
  let goalAmount = null;
  let goalDate = null;
  let goalFrequency = null;

  if (goalType === "target_date") {
    goalDate = formData.get("target_date_dt");
    goalAmount = dollarsToMinor(formData.get("target_amount"));
  } else if (goalType === "recurring") {
    goalFrequency = formData.get("frequency");
    goalDate = formData.get("recurring_date_dt");
    goalAmount = dollarsToMinor(formData.get("recurring_amount"));
  }

  const payload = {
    name,
    is_active: true,
    group_id: groupId,
    goal_type: goalType,
    goal_amount_minor: goalAmount,
    goal_target_date: goalDate || null,
    goal_frequency: goalFrequency,
  };

  try {
    setButtonBusy(submitButton, true);
    setFormError(errorEl, "");
    const isEditing = Boolean(state.pendingCategoryEdit);
    if (isEditing) {
      await fetchJSON(`/api/budget-categories/${state.pendingCategoryEdit.category_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      // Slug is optional now, backend generates it if missing
      if (slug) {
        payload.category_id = slug;
      }
      await fetchJSON("/api/budget-categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    closeCategoryModal();
    await Promise.all([loadBudgetsData(), loadReferenceData()]);
    renderBudgetsPage();
    showToast(isEditing ? `Renamed ${name}` : `Created ${name}`);
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save category.");
  } finally {
    setButtonBusy(submitButton, false);
  }
};

const initCategoryModal = () => {
  const modal = document.querySelector(selectors.categoryModal);
  if (!modal) {
    return;
  }
  const form = document.querySelector(selectors.categoryForm);
  form?.addEventListener("submit", handleCategoryFormSubmit);
  const closeButton = document.querySelector(selectors.categoryModalClose);
  closeButton?.addEventListener("click", () => closeCategoryModal());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeCategoryModal();
    }
  });
  const nameInput = document.querySelector(selectors.categoryNameInput);
  const slugInput = document.querySelector(selectors.categorySlugInput);
  nameInput?.addEventListener("input", () => {
    if (state.pendingCategoryEdit || categorySlugDirty || !slugInput) {
      return;
    }
    // Slug input is hidden now, but we keep this logic if we ever re-enable it or use it internally
    slugInput.value = slugifyCategoryName(nameInput.value);
  });
  slugInput?.addEventListener("input", () => {
    categorySlugDirty = true;
  });

  const goalRadios = form.querySelectorAll("input[name='goal_type']");
  goalRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      form.querySelector("[data-goal-section='target_date']").style.display = radio.value === "target_date" ? "block" : "none";
      form.querySelector("[data-goal-section='recurring']").style.display = radio.value === "recurring" ? "block" : "none";
    });
  });
};


const init = async () => {
  transactionsBodyEl = document.querySelector(selectors.transactionsBody);
  if (!transactionsBodyEl) {
    console.error("Fatal: Transaction table body not found.");
    return;
  }

  const pageNodes = document.querySelectorAll(".page");
  const routeLinks = document.querySelectorAll("[data-route-link]");
  const activateRoute = (route) => {
    const normalizedRoute = route && document.querySelector(`[data-route="${route}"]`) ? route : "transactions";
    pageNodes.forEach((page) => {
      page.classList.toggle("active", page.dataset.route === normalizedRoute);
    });
    routeLinks.forEach((link) => {
      link.classList.toggle("active", link.dataset.routeLink === normalizedRoute);
    });
    if (normalizedRoute === "budgets") {
      loadBudgetsData()
        .then(() => renderBudgetsPage())
        .catch((error) => console.error("Budgets refresh failed", error));
    }
    if (normalizedRoute === "allocations") {
      Promise.all([loadBudgetsData(), loadAllocationsData()])
        .then(() => {
          renderBudgetsPage();
          renderAllocationsPage();
        })
        .catch((error) => console.error("Allocations refresh failed", error));
    }
  };

  const handleHashChange = () => {
    const rawRoute = window.location.hash.replace("#/", "");
    activateRoute(rawRoute);
  };

  window.addEventListener("hashchange", handleHashChange);
  handleHashChange();

  updateHeaderStats();

  initBudgetsInteractions();
  initAllocationsPage();
  initCategoryModal();
  initGroupModal();
  initTransactionForm();
  initTransferForm();

  await loadReferenceData();

  try {
    await refreshTransactions(transactionsBodyEl);
  } catch (error) {
    console.error(error);
    transactionsBodyEl.innerHTML = `
      <tr>
        <td colspan="6" class="muted" style="text-align: center; color: var(--danger);">
          Error: Could not load transaction data.
        </td>
      </tr>
    `;
  }

  const sectionLinks = document.querySelectorAll(selectors.accountSectionLink);
  const updateSectionActive = (active) => {
    sectionLinks.forEach((link) => {
      const section = link.getAttribute("data-account-section");
      link.classList.toggle("is-active", section === active);
    });
  };

  updateSectionActive(state.accountFilter);

  sectionLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const section = link.getAttribute("data-account-section");
      state.accountFilter = section;
      updateSectionActive(section);
      renderAccountGroups();
    });
  });

  const addAccountBtn = document.querySelector(selectors.addAccountButton);
  addAccountBtn?.addEventListener("click", () => showAddAccountModal());

  const modalClose = document.querySelector(selectors.modalClose);
  modalClose?.addEventListener("click", () => toggleAccountModal(false));

  if (modalOverlay) {
    modalOverlay.addEventListener("click", (event) => {
      if (event.target === modalOverlay) {
        toggleAccountModal(false);
      }
    });
  }

  const modalSubmit = document.querySelector(selectors.modalAddButton);
  modalSubmit?.addEventListener("click", async () => {
    await handleAddAccount();
  });

  const addFormType = document.querySelector(selectors.modalTypeSelect);
  if (addFormType) {
    addFormType.addEventListener("change", () => {
      const mapping = accountTypeMapping[addFormType.value];
      const subtitle = document.querySelector("[data-modal-type-hint]");
      if (subtitle) {
        subtitle.textContent = mapping
          ? `${mapping.account_class.replace(/_/g, " ")} · ${mapping.account_role === "on_budget" ? "On-budget" : "Tracking"}`
          : "";
      }
    });
  }

  await refreshAccountsPage();
  await loadBudgetsData();
  renderBudgetsPage();
  await loadAllocationsData();
  renderAllocationsPage();
};

document.addEventListener("DOMContentLoaded", init);
