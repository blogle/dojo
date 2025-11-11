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
};

const state = {
  referenceLoaded: false,
  transactions: [],
};

const fetchJSON = async (url, options) => {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail ?? "Request failed");
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
};

const formatAmount = (minor) => currencyFormatter.format(minor / 100);

const setStatus = (statusEl, message, isError = false) => {
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

const refreshReferenceData = async (form, statusEl) => {
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

  try {
    disableForm(form, true);
    await Promise.all([
      refreshReferenceData(form, statusEl),
      refreshTransactions(transactionsBody),
      refreshNetWorth(netWorthValueEl, netWorthUpdatedEl),
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
