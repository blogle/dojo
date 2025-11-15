const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const selectors = {
  form: "#transaction-form",
  netWorthValue: "#net-worth-value",
  netWorthUpdated: "#net-worth-updated",
  status: "#submission-status",
  transactionsBody: "#transactions-body",
  navButtons: "[data-view-button]",
  viewPanels: "[data-view-panel]",
  accountForm: "#account-form",
  accountStatus: "#account-status",
  accountsTableBody: "#accounts-table-body",
  categoryForm: "#category-form",
  categoryStatus: "#category-status",
  categoriesTableBody: "#categories-table-body",
};

const state = {
  referenceLoaded: false,
  transactions: [],
  accounts: [],
  categories: [],
  accountEditingId: null,
  categoryEditingId: null,
  activeView: "ledger",
};

const parseJSONBody = async (response) => {
  if (response.status === 204) {
    return null;
  }
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    return null;
  }
};

const fetchJSON = async (url, options) => {
  const response = await fetch(url, options);
  const data = await parseJSONBody(response);
  if (!response.ok) {
    const error = new Error(data?.detail ?? "Request failed");
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
};

const formatAmount = (minor) => currencyFormatter.format(minor / 100);

const dollarsToMinor = (value) => {
  if (value === null || value === "") {
    return 0;
  }
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return null;
  }
  return Math.round(parsed * 100);
};

const minorToInputValue = (minor) => (minor / 100).toFixed(2);

const normalizeSlug = (value) => (value ?? "").trim().toLowerCase();

const setStatus = (statusEl, message, isError = false) => {
  if (!statusEl) {
    return;
  }
  statusEl.textContent = message ?? "";
  statusEl.style.color = isError ? "#b91c1c" : "";
};

const clearErrors = (errorEls) => {
  Object.values(errorEls).forEach((el) => {
    el.textContent = "";
  });
};

const renderTransactions = (bodyEl, transactions) => {
  bodyEl.innerHTML = "";
  if (!transactions.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "muted";
    cell.textContent = "No transactions yet. Add one above.";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }

  transactions.forEach((tx) => {
    const row = document.createElement("tr");
    const amountClass = tx.amount_minor < 0 ? "amount-negative" : "amount-positive";
    row.innerHTML = `
      <td>${tx.transaction_date}</td>
      <td>${tx.account_name}</td>
      <td>${tx.category_name}</td>
      <td class="${amountClass}">${formatAmount(tx.amount_minor)}</td>
      <td>${tx.amount_minor < 0 ? "Expense" : "Income"}</td>
      <td>${tx.memo ?? "—"}</td>
      <td>${new Date(tx.recorded_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
    `;
    bodyEl.appendChild(row);
  });
};

const populateSelect = (selectEl, items, valueKey, labelKey) => {
  selectEl.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item[valueKey];
    option.textContent = item[labelKey];
    selectEl.appendChild(option);
  });
};

const refreshReferenceData = async (form, statusEl = null) => {
  const data = await fetchJSON("/api/reference-data");
  populateSelect(form.querySelector('select[name="account_id"]'), data.accounts, "account_id", "name");
  populateSelect(form.querySelector('select[name="category_id"]'), data.categories, "category_id", "name");
  state.referenceLoaded = true;
  setStatus(statusEl, "");
};

const refreshTransactions = async (bodyEl) => {
  const data = await fetchJSON("/api/transactions?limit=100");
  state.transactions = data;
  renderTransactions(bodyEl, state.transactions);
};

const refreshNetWorth = async (valueEl, timestampEl) => {
  const snapshot = await fetchJSON("/api/net-worth/current");
  valueEl.textContent = formatAmount(snapshot.net_worth_minor);
  timestampEl.textContent = `Updated ${new Date().toLocaleString()}`;
};

const disableForm = (form, disabled) => {
  [...form.elements].forEach((el) => {
    if (el.tagName === "BUTTON" || el.tagName === "INPUT" || el.tagName === "SELECT") {
      el.disabled = disabled;
    }
  });
};

const handleValidationErrors = (errorEls, error) => {
  if (error.status === 422 && Array.isArray(error.payload?.detail)) {
    const validationErrors = {};
    error.payload.detail.forEach((detail) => {
      if (Array.isArray(detail.loc) && detail.loc[0] === "body") {
        validationErrors[detail.loc[1]] = detail.msg;
      }
    });
    Object.entries(validationErrors).forEach(([field, message]) => {
      if (errorEls[field]) {
        errorEls[field].textContent = message;
      }
    });
    return true;
  }
  return false;
};

const focusFirstInput = (form) => {
  const first = form.querySelector('input[name="transaction_date"]');
  if (first) {
    first.focus();
  }
};

const showView = (viewName) => {
  state.activeView = viewName;
  document.querySelectorAll(selectors.viewPanels).forEach((panel) => {
    panel.hidden = panel.dataset.viewPanel !== viewName;
  });
  document.querySelectorAll(selectors.navButtons).forEach((button) => {
    button.classList.toggle("active", button.dataset.viewButton === viewName);
  });
};

const initNavigation = () => {
  document.querySelectorAll(selectors.navButtons).forEach((button) => {
    button.addEventListener("click", () => {
      showView(button.dataset.viewButton);
    });
  });
  showView(state.activeView);
};

const renderAccountsTable = (bodyEl, accounts) => {
  bodyEl.innerHTML = "";
  if (!accounts.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.className = "muted";
    cell.textContent = "No accounts yet.";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }
  accounts.forEach((account) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${account.account_id}</td>
      <td>${account.name}</td>
      <td>${account.account_type}</td>
      <td>${formatAmount(account.current_balance_minor)}</td>
      <td>${account.currency}</td>
      <td>${account.is_active ? "Yes" : "No"}</td>
      <td>${account.opened_on ?? "—"}</td>
      <td>
        <button type="button" class="link-button" data-account-edit="${account.account_id}">Edit</button>
        <button type="button" class="link-button" data-account-remove="${account.account_id}" ${account.is_active ? "" : "disabled"}>
          Remove
        </button>
      </td>
    `;
    bodyEl.appendChild(row);
  });
};

const refreshAccountsAdmin = async (bodyEl) => {
  const accounts = await fetchJSON("/api/accounts");
  state.accounts = accounts;
  renderAccountsTable(bodyEl, accounts);
};

const resetAccountForm = (form) => {
  state.accountEditingId = null;
  form.reset();
  form.querySelector('input[name="account_id"]').disabled = false;
  form.querySelector('input[name="currency"]').value = "USD";
  form.querySelector('input[name="current_balance"]').value = "0";
  form.querySelector('input[name="is_active"]').checked = true;
  form.querySelector('[data-account-submit]').textContent = "Add Account";
  form.querySelector('[data-account-cancel]').hidden = true;
};

const populateAccountForm = (form, account) => {
  state.accountEditingId = account.account_id;
  const idInput = form.querySelector('input[name="account_id"]');
  idInput.value = account.account_id;
  idInput.disabled = true;
  form.querySelector('input[name="name"]').value = account.name;
  form.querySelector('select[name="account_type"]').value = account.account_type;
  form.querySelector('input[name="currency"]').value = account.currency;
  form.querySelector('input[name="current_balance"]').value = minorToInputValue(account.current_balance_minor);
  form.querySelector('input[name="opened_on"]').value = account.opened_on ?? "";
  form.querySelector('input[name="is_active"]').checked = account.is_active;
  form.querySelector('[data-account-submit]').textContent = "Save Changes";
  form.querySelector('[data-account-cancel]').hidden = false;
};

const initAccountsPanel = ({ refreshReference }) => {
  const form = document.querySelector(selectors.accountForm);
  const statusEl = document.querySelector(selectors.accountStatus);
  const tableBody = document.querySelector(selectors.accountsTableBody);

  if (!form || !statusEl || !tableBody) {
    return { refresh: async () => {} };
  }

  const cancelBtn = form.querySelector('[data-account-cancel]');
  cancelBtn.addEventListener("click", () => {
    resetAccountForm(form);
    setStatus(statusEl, "");
  });

  tableBody.addEventListener("click", (event) => {
    const editBtn = event.target.closest("[data-account-edit]");
    if (editBtn) {
      const account = state.accounts.find((acc) => acc.account_id === editBtn.dataset.accountEdit);
      if (account) {
        populateAccountForm(form, account);
        setStatus(statusEl, `Editing ${account.account_id}`);
      }
      return;
    }
    const removeBtn = event.target.closest("[data-account-remove]");
    if (removeBtn) {
      handleAccountRemove(removeBtn.dataset.accountRemove, form, statusEl, tableBody, refreshReference);
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    handleAccountSubmit(form, statusEl, tableBody, refreshReference);
  });

  const refresh = async () => {
    try {
      await refreshAccountsAdmin(tableBody);
    } catch (error) {
      console.error(error);
      setStatus(statusEl, "Unable to load accounts.", true);
    }
  };

  return { refresh };
};

const handleAccountSubmit = async (form, statusEl, tableBody, refreshReference) => {
  setStatus(statusEl, "");
  const formData = new FormData(form);
  const balanceMinor = dollarsToMinor(formData.get("current_balance"));
  if (balanceMinor === null) {
    setStatus(statusEl, "Enter a numeric balance.", true);
    return;
  }
  const accountId = normalizeSlug(formData.get("account_id"));
  if (!state.accountEditingId && !accountId) {
    setStatus(statusEl, "Account ID is required.", true);
    return;
  }
  const name = (formData.get("name") ?? "").trim();
  const accountType = formData.get("account_type") ?? "asset";
  const currency = ((formData.get("currency") ?? "USD").toString().trim() || "USD").toUpperCase();
  const openedRaw = formData.get("opened_on");
  const payload = {
    name,
    account_type: accountType,
    currency,
    current_balance_minor: balanceMinor,
    opened_on: openedRaw ? openedRaw : null,
    is_active: form.querySelector('input[name="is_active"]').checked,
  };
  const isEditing = Boolean(state.accountEditingId);
  const endpoint = isEditing ? `/api/accounts/${state.accountEditingId}` : "/api/accounts";
  const body = JSON.stringify(isEditing ? payload : { ...payload, account_id: accountId });
  disableForm(form, true);
  try {
    await fetchJSON(endpoint, {
      method: isEditing ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    setStatus(statusEl, isEditing ? "Account updated." : "Account created.");
    resetAccountForm(form);
    await refreshAccountsAdmin(tableBody);
    if (typeof refreshReference === "function") {
      await refreshReference();
    }
  } catch (error) {
    console.error(error);
    setStatus(statusEl, error.message, true);
  } finally {
    disableForm(form, false);
  }
};

const handleAccountRemove = async (accountId, form, statusEl, tableBody, refreshReference) => {
  if (!accountId) {
    return;
  }
  try {
    await fetchJSON(`/api/accounts/${accountId}`, { method: "DELETE" });
    if (state.accountEditingId === accountId) {
      resetAccountForm(form);
    }
    await refreshAccountsAdmin(tableBody);
    if (typeof refreshReference === "function") {
      await refreshReference();
    }
    setStatus(statusEl, `Account ${accountId} removed.`);
  } catch (error) {
    console.error(error);
    setStatus(statusEl, error.message, true);
  }
};

const renderCategoriesTable = (bodyEl, categories) => {
  bodyEl.innerHTML = "";
  if (!categories.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.className = "muted";
    cell.textContent = "No budget categories yet.";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }
  categories.forEach((category) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${category.category_id}</td>
      <td>${category.name}</td>
      <td>${category.is_active ? "Yes" : "No"}</td>
      <td>
        <button type="button" class="link-button" data-category-edit="${category.category_id}">Edit</button>
        <button type="button" class="link-button" data-category-remove="${category.category_id}" ${category.is_active ? "" : "disabled"}>
          Remove
        </button>
      </td>
    `;
    bodyEl.appendChild(row);
  });
};

const refreshCategoriesAdmin = async (bodyEl) => {
  const categories = await fetchJSON("/api/budget-categories");
  state.categories = categories;
  renderCategoriesTable(bodyEl, categories);
};

const resetCategoryForm = (form) => {
  state.categoryEditingId = null;
  form.reset();
  form.querySelector('input[name="category_id"]').disabled = false;
  form.querySelector('input[name="is_active"]').checked = true;
  form.querySelector('[data-category-submit]').textContent = "Add Category";
  form.querySelector('[data-category-cancel]').hidden = true;
};

const populateCategoryForm = (form, category) => {
  state.categoryEditingId = category.category_id;
  const idInput = form.querySelector('input[name="category_id"]');
  idInput.value = category.category_id;
  idInput.disabled = true;
  form.querySelector('input[name="name"]').value = category.name;
  form.querySelector('input[name="is_active"]').checked = category.is_active;
  form.querySelector('[data-category-submit]').textContent = "Save Changes";
  form.querySelector('[data-category-cancel]').hidden = false;
};

const initCategoriesPanel = ({ refreshReference }) => {
  const form = document.querySelector(selectors.categoryForm);
  const statusEl = document.querySelector(selectors.categoryStatus);
  const tableBody = document.querySelector(selectors.categoriesTableBody);

  if (!form || !statusEl || !tableBody) {
    return { refresh: async () => {} };
  }

  const cancelBtn = form.querySelector('[data-category-cancel]');
  cancelBtn.addEventListener("click", () => {
    resetCategoryForm(form);
    setStatus(statusEl, "");
  });

  tableBody.addEventListener("click", (event) => {
    const editBtn = event.target.closest("[data-category-edit]");
    if (editBtn) {
      const category = state.categories.find((cat) => cat.category_id === editBtn.dataset.categoryEdit);
      if (category) {
        populateCategoryForm(form, category);
        setStatus(statusEl, `Editing ${category.category_id}`);
      }
      return;
    }
    const removeBtn = event.target.closest("[data-category-remove]");
    if (removeBtn) {
      handleCategoryRemove(removeBtn.dataset.categoryRemove, form, statusEl, tableBody, refreshReference);
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    handleCategorySubmit(form, statusEl, tableBody, refreshReference);
  });

  const refresh = async () => {
    try {
      await refreshCategoriesAdmin(tableBody);
    } catch (error) {
      console.error(error);
      setStatus(statusEl, "Unable to load categories.", true);
    }
  };

  return { refresh };
};

const handleCategorySubmit = async (form, statusEl, tableBody, refreshReference) => {
  setStatus(statusEl, "");
  const formData = new FormData(form);
  const categoryId = normalizeSlug(formData.get("category_id"));
  if (!state.categoryEditingId && !categoryId) {
    setStatus(statusEl, "Category ID is required.", true);
    return;
  }
  const name = (formData.get("name") ?? "").trim();
  const payload = {
    name,
    is_active: form.querySelector('input[name="is_active"]').checked,
  };
  const isEditing = Boolean(state.categoryEditingId);
  const endpoint = isEditing ? `/api/budget-categories/${state.categoryEditingId}` : "/api/budget-categories";
  const body = JSON.stringify(isEditing ? payload : { ...payload, category_id: categoryId });
  disableForm(form, true);
  try {
    await fetchJSON(endpoint, {
      method: isEditing ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    setStatus(statusEl, isEditing ? "Category updated." : "Category created.");
    resetCategoryForm(form);
    await refreshCategoriesAdmin(tableBody);
    if (typeof refreshReference === "function") {
      await refreshReference();
    }
  } catch (error) {
    console.error(error);
    setStatus(statusEl, error.message, true);
  } finally {
    disableForm(form, false);
  }
};

const handleCategoryRemove = async (categoryId, form, statusEl, tableBody, refreshReference) => {
  if (!categoryId) {
    return;
  }
  try {
    await fetchJSON(`/api/budget-categories/${categoryId}`, { method: "DELETE" });
    if (state.categoryEditingId === categoryId) {
      resetCategoryForm(form);
    }
    await refreshCategoriesAdmin(tableBody);
    if (typeof refreshReference === "function") {
      await refreshReference();
    }
    setStatus(statusEl, `Category ${categoryId} removed.`);
  } catch (error) {
    console.error(error);
    setStatus(statusEl, error.message, true);
  }
};

const init = async () => {
  const form = document.querySelector(selectors.form);
  const netWorthValueEl = document.querySelector(selectors.netWorthValue);
  const netWorthUpdatedEl = document.querySelector(selectors.netWorthUpdated);
  const statusEl = document.querySelector(selectors.status);
  const transactionsBody = document.querySelector(selectors.transactionsBody);

  if (!form || !netWorthValueEl || !netWorthUpdatedEl || !statusEl || !transactionsBody) {
    return;
  }

  form.setAttribute("novalidate", "novalidate");
  const errorEls = [...document.querySelectorAll("[data-error-for]")].reduce((acc, el) => {
    acc[el.dataset.errorFor] = el;
    return acc;
  }, {});

  focusFirstInput(form);
  initNavigation();

  const refreshReference = () => refreshReferenceData(form, null);
  const accountsPanel = initAccountsPanel({ refreshReference });
  const categoriesPanel = initCategoriesPanel({ refreshReference });

  try {
    disableForm(form, true);
    await Promise.all([
      refreshReferenceData(form, statusEl),
      refreshTransactions(transactionsBody),
      refreshNetWorth(netWorthValueEl, netWorthUpdatedEl),
      accountsPanel.refresh(),
      categoriesPanel.refresh(),
    ]);
  } catch (error) {
    console.error(error);
    setStatus(statusEl, "Unable to load initial data.", true);
  } finally {
    disableForm(form, false);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(statusEl, "");
    clearErrors(errorEls);

    if (!state.referenceLoaded) {
      setStatus(statusEl, "Reference data not ready yet.", true);
      return;
    }

    const formData = new FormData(form);
    const amountFloat = parseFloat(formData.get("amount"));
    if (Number.isNaN(amountFloat)) {
      errorEls.amount_minor.textContent = "Enter a numeric amount.";
      return;
    }

    let amountMinor = Math.round(amountFloat * 100);
    if (formData.get("flow_direction") === "expense") {
      amountMinor *= -1;
    }

    const payload = {
      transaction_date: formData.get("transaction_date"),
      account_id: formData.get("account_id"),
      category_id: formData.get("category_id"),
      amount_minor: amountMinor,
      memo: formData.get("memo") || null,
    };

    disableForm(form, true);
    try {
      await fetchJSON("/api/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      form.reset();
      focusFirstInput(form);
      setStatus(statusEl, "Transaction recorded.");
      await Promise.all([
        refreshTransactions(transactionsBody),
        refreshNetWorth(netWorthValueEl, netWorthUpdatedEl),
        refreshReferenceData(form, null),
      ]);
    } catch (error) {
      const handled = handleValidationErrors(errorEls, error);
      if (!handled) {
        setStatus(statusEl, error.message, true);
      } else {
        setStatus(statusEl, "Fix the highlighted errors.", true);
      }
    } finally {
      disableForm(form, false);
    }
  });
};

document.addEventListener("DOMContentLoaded", init);
