import { selectors } from "../../constants.js";
import { api } from "../../services/api.js";
import { formatAmount, dollarsToMinor, todayISO, currentMonthStartISO } from "../../services/format.js";
import { setFormError, setButtonBusy } from "../../services/dom.js";
import { store } from "../../store.js";
import { getCategoryAvailableMinor, getCategoryDisplayName } from "../categories/utils.js";
import { showToast } from "../toast.js";

let loadBudgetsData = async () => {};
let renderBudgetsPage = () => {};
let refreshAccountsPage = async () => {};

export const loadAllocationsData = async () => {
  const month = currentMonthStartISO();
  try {
    const data = await api.budgets.allocations(month);
    store.setState((prev) => ({
      ...prev,
      allocations: {
        entries: data?.allocations ?? [],
        inflowMinor: data?.inflow_minor ?? 0,
        readyMinor: data?.ready_to_assign_minor ?? 0,
        monthStartISO: data?.month_start ?? month,
        monthLabel: new Date(`${data?.month_start ?? month}T00:00:00`).toLocaleDateString(undefined, {
          year: "numeric",
          month: "long",
        }),
      },
    }));
  } catch (error) {
    console.error("Failed to load allocations", error);
    throw error;
  }
};

export const renderAllocationsPage = () => {
  const state = store.getState();
  const inflowEl = document.querySelector(selectors.allocationInflowValue);
  const readyEl = document.querySelector(selectors.allocationReadyValue);
  const monthEl = document.querySelector(selectors.allocationMonthLabel);
  if (inflowEl) {
    inflowEl.textContent = formatAmount(state.allocations.inflowMinor);
  }
  if (readyEl) {
    readyEl.textContent = formatAmount(state.allocations.readyMinor);
  }
  if (monthEl) {
    monthEl.textContent = state.allocations.monthLabel || "—";
  }
  const body = document.querySelector(selectors.allocationsBody);
  if (body) {
    body.innerHTML = "";
    if (!state.allocations.entries.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5" class="u-muted">No allocations recorded for this month.</td>';
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
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        allocation: { ...prev.forms.allocation, pendingToCategory: null },
      },
    }));
  }
};

const handleAllocationFormSubmit = async (event) => {
  event.preventDefault();
  const state = store.getState();
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
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        allocation: { ...prev.forms.allocation, submitting: true },
      },
    }));
    setButtonBusy(button, true);
    await api.budgets.createAllocation(payload);
    const amountInput = form.querySelector("input[name='amount']");
    if (amountInput) {
      amountInput.value = "";
      amountInput.focus();
    }
    setFormError(errorEl, "");
    await Promise.all([loadAllocationsData(), loadBudgetsData(), refreshAccountsPage()]);
    renderAllocationsPage();
    renderBudgetsPage();
    const fromLabel = getCategoryDisplayName(fromCategoryId);
    const toLabel = getCategoryDisplayName(toCategoryId);
    showToast(`Moved ${formatAmount(Math.abs(payload.amount_minor))} from ${fromLabel} to ${toLabel}`);
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Allocation failed.");
  } finally {
    store.setState((prev) => ({
      ...prev,
      forms: {
        ...prev.forms,
        allocation: { ...prev.forms.allocation, submitting: false },
      },
    }));
    setButtonBusy(button, false);
  }
};

export const initAllocations = ({ onBudgetsRefresh, onBudgetsRender, onAccountsRefresh } = {}) => {
  loadBudgetsData = onBudgetsRefresh || (() => Promise.resolve());
  renderBudgetsPage = onBudgetsRender || (() => {});
  refreshAccountsPage = onAccountsRefresh || (() => Promise.resolve());

  const form = document.querySelector(selectors.allocationForm);
  form?.addEventListener("submit", handleAllocationFormSubmit);
};
