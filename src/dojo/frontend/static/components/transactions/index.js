import { selectors, statusToggleIcons } from "../../constants.js";
import { api } from "../../services/api.js";
import { formatAmount, dollarsToMinor, minorToDollars, todayISO } from "../../services/format.js";
import { setFormError, setButtonBusy, populateSelect } from "../../services/dom.js";
import { store } from "../../store.js";
import { getCategoryOptions } from "../categories/utils.js";
import { refreshSelectOptions } from "../reference/index.js";

let transactionsBodyEl = null;
let detachInlineEscHandler = null;

const computeCurrentMonthSpend = (transactions) => {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();
  return transactions.reduce((total, tx) => {
    if (!tx || !tx.transaction_date) return total;
    const txDate = new Date(`${tx.transaction_date}T00:00:00`);
    if (txDate.getMonth() === currentMonth && txDate.getFullYear() === currentYear && tx.amount_minor < 0) {
      return total + Math.abs(tx.amount_minor);
    }
    return total;
  }, 0);
};

export const updateHeaderStats = () => {
  const state = store.getState();
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
    if (store.getState().editingTransactionId !== transactionVersionId) {
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

const applyStatusToggleState = (toggle, stateValue) => {
  if (!toggle) {
    return;
  }
  const nextState = stateValue === "cleared" ? "cleared" : "pending";
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
  store.setState((prev) => ({
    ...prev,
    editingTransactionId: transaction.transaction_version_id,
    forms: {
      ...prev.forms,
      transactionEdit: {
        ...prev.forms.transactionEdit,
        conceptId: transaction.concept_id || null,
        transactionId: transaction.transaction_version_id || null,
      },
    },
  }));
  bindInlineEscHandler(transaction.transaction_version_id);
  renderTransactions(transactionsBodyEl, store.getState().transactions);
};

const cancelInlineTransactionEdit = () => {
  store.setState((prev) => ({
    ...prev,
    editingTransactionId: null,
    forms: {
      ...prev.forms,
      transactionEdit: {
        ...prev.forms.transactionEdit,
        conceptId: null,
        transactionId: null,
      },
    },
  }));
  if (detachInlineEscHandler) {
    detachInlineEscHandler();
  }
  renderTransactions(transactionsBodyEl, store.getState().transactions);
};

const hydrateInlineEditRow = (row, transaction) => {
  if (!row || !transaction) {
    return;
  }
  row.classList.add("inline-edit-row");
  const errorEl = row.querySelector("[data-inline-error]");
  setFormError(errorEl, "");
  const state = store.getState();
  const accountSelect = row.querySelector("[data-inline-account]");
  if (accountSelect) {
    const sortedAccounts = [...state.reference.accounts].sort((a, b) => a.name.localeCompare(b.name));
    populateSelect(accountSelect, sortedAccounts, { valueKey: "account_id", labelKey: "name" }, "Select account");
    accountSelect.value = transaction.account_id || "";
  }
  const categorySelect = row.querySelector("[data-inline-category]");
  if (categorySelect) {
    const categories = getCategoryOptions({ includeSystem: true });
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
  const state = store.getState();
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
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        transactionEdit: { ...prev.forms.transactionEdit, submitting: true },
      },
    }));
    setInlineRowBusy(row, true);
    setFormError(errorEl, "");
    await api.transactions.create(payload);
    store.setState((prev) => ({
      ...prev,
      editingTransactionId: null,
      forms: {
        ...prev.forms,
        transactionEdit: { submitting: false, conceptId: null, transactionId: null },
      },
    }));
    if (detachInlineEscHandler) {
      detachInlineEscHandler();
    }
    await Promise.all([refreshTransactions(transactionsBodyEl), refreshAccountsPage(), loadBudgetsData()]);
    refreshSelectOptions();
    renderBudgetsPage();
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save changes.");
  } finally {
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        transactionEdit: { ...prev.forms.transactionEdit, submitting: false },
      },
    }));
    setInlineRowBusy(row, false);
  }
};

const renderTransactions = (bodyEl, transactions) => {
  if (!bodyEl) {
    return;
  }
  bodyEl.innerHTML = "";
  if (!Array.isArray(transactions) || !transactions.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "u-muted";
    cell.style.textAlign = "center";
    cell.textContent = "No transactions found.";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }

  const state = store.getState();

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
      row.addEventListener("click", () => {
        startInlineTransactionEdit(tx);
      });
      const displayToggle = row.querySelector("[data-status-display]");
      applyStatusToggleState(displayToggle, statusValue);
    }
    bodyEl.appendChild(row);
  });
};

export const refreshTransactions = async (bodyEl = transactionsBodyEl) => {
  if (!bodyEl) {
    return;
  }
  const data = await api.transactions.list(100);
  const sorted = (data || []).sort((a, b) => {
    const dateA = a.transaction_date ? new Date(a.transaction_date) : 0;
    const dateB = b.transaction_date ? new Date(b.transaction_date) : 0;
    return dateB - dateA;
  });
  store.setState((prev) => ({ ...prev, transactions: sorted }));
  renderTransactions(bodyEl, sorted);
  updateHeaderStats();
};

const setTransactionFlow = (flow) => {
  store.setState((prev) => ({
    ...prev,
    forms: {
      ...prev.forms,
      transaction: { ...prev.forms.transaction, flow },
    },
  }));
  document.querySelectorAll(selectors.transactionFlowInputs).forEach((input) => {
    const isMatch = input.value === flow;
    input.checked = isMatch;
  });
};

const handleTransactionSubmit = async (event) => {
  event.preventDefault();
  const state = store.getState();
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
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        transaction: { ...prev.forms.transaction, submitting: true },
      },
    }));
    setButtonBusy(submitButton, true);
    await api.transactions.create(payload);
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
    refreshSelectOptions();
    renderBudgetsPage();
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save transaction.");
  } finally {
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        transaction: { ...prev.forms.transaction, submitting: false },
      },
    }));
    setButtonBusy(submitButton, false);
  }
};

export const initTransactions = ({ onBudgetsRefresh, onAccountsRefresh, onBudgetsRender } = {}) => {
  transactionsBodyEl = document.querySelector(selectors.transactionsBody);
  if (!transactionsBodyEl) {
    console.error("Fatal: Transaction table body not found.");
    return;
  }

  refreshAccountsPage = onAccountsRefresh || (() => Promise.resolve());
  loadBudgetsData = onBudgetsRefresh || (() => Promise.resolve());
  renderBudgetsPage = onBudgetsRender || (() => {});

  updateHeaderStats();

  const form = document.querySelector(selectors.transactionForm);
  if (form) {
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
    setTransactionFlow(store.getState().forms.transaction.flow);
  }
};

let refreshAccountsPage = async () => {};
let loadBudgetsData = async () => {};
let renderBudgetsPage = () => {};
