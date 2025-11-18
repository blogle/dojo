const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const selectors = {
  todayDate: "#today-date",
  lastReconcileDate: "#last-reconcile-date",
  monthSpend: "#month-spend",
  transactionsBody: "#transactions-body",
  assetsTotal: "#assets-total",
  liabilitiesTotal: "#liabilities-total",
  netWorth: "#net-worth",
  accountGroups: "#account-groups",
  addAccountButton: "[data-add-account-button]",
  accountModal: "#account-modal",
  modalClose: "[data-close-modal]",
  accountSectionLink: "[data-account-section]",
};

const state = {
  transactions: [],
  accountFilter: "all",
};

const fetchJSON = async (url, options) => {
  const response = await fetch(url, options);
  if (response.status === 204) {
    return null;
  }
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    const data = JSON.parse(text);
    if (!response.ok) {
      const error = new Error(data?.detail ?? "Request failed");
      error.status = response.status;
      error.payload = data;
      throw error;
    }
    return data;
  } catch (error) {
    console.error("Failed to parse JSON:", text);
    throw new Error("Server returned non-JSON response");
  }
};

const formatAmount = (minor) => currencyFormatter.format(minor / 100);

const getTransactionStatus = (transactionDate) => {
  const today = new Date();
  const txDate = new Date(transactionDate);
  const diffTime = Math.abs(today - txDate);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 3 ? "Settled" : "Pending";
};

const renderTransactions = (bodyEl, transactions) => {
  bodyEl.innerHTML = "";
  if (!Array.isArray(transactions) || !transactions.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.className = "muted";
    cell.style.textAlign = "center";
    cell.textContent = "No transactions found.";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }

  transactions.forEach((tx) => {
    if (!tx) return; // Skip if transaction is null or undefined
    const row = document.createElement("tr");
    const status = getTransactionStatus(tx.transaction_date);
    const statusClass = status === "Settled" ? "status-settled" : "status-pending";

    row.innerHTML = `
      <td>${tx.transaction_date || "N/A"}</td>
      <td>${tx.account_name || "N/A"}</td>
      <td>${tx.category_name || "N/A"}</td>
      <td>${tx.memo || "—"}</td>
      <td class="${statusClass}">${status}</td>
      <td class="amount-cell">${formatAmount(tx.amount_minor || 0)}</td>
    `;
    bodyEl.appendChild(row);
  });
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

const updateHeaderStats = () => {
  const todayEl = document.querySelector(selectors.todayDate);
  if (todayEl) {
    todayEl.textContent = new Date().toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  const spendEl = document.querySelector(selectors.monthSpend);
  if (spendEl) {
    spendEl.textContent = formatAmount(computeCurrentMonthSpend(state.transactions));
  }

  // Mock "Last Reconcile Date"
  const reconcileEl = document.querySelector(selectors.lastReconcileDate);
  if (reconcileEl) {
    const today = new Date();
    today.setDate(today.getDate() - 1); // Yesterday
    reconcileEl.textContent = today.toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }
};

const refreshTransactions = async (bodyEl) => {
  const data = await fetchJSON("/api/transactions?limit=100");
  // Sort by date descending
  state.transactions = (data || []).sort((a, b) => {
    const dateA = a.transaction_date ? new Date(a.transaction_date) : 0;
    const dateB = b.transaction_date ? new Date(b.transaction_date) : 0;
    return dateB - dateA;
  });
  renderTransactions(bodyEl, state.transactions);
  updateHeaderStats();
};

const accountGroupsData = [
  {
    id: "cash",
    title: "Cash & Checking",
    type: "asset",
    description: "Everyday banking and liquid cash.",
    accounts: [
      { name: "Main Checking", institution: "Northwind Bank", balance_minor: 542_000 },
      { name: "Backup Savings", institution: "Tidal Savings", balance_minor: 128_450 },
    ],
  },
  {
    id: "short-term",
    title: "Accessible Assets",
    type: "asset",
    description: "Short-term deposits and cash equivalents.",
    accounts: [
      {
        name: "Money Market",
        institution: "Atlas Capital",
        balance_minor: 89_320,
      },
      {
        name: "High Yield CD",
        institution: "Brightline Credit",
        balance_minor: 41_200,
      },
    ],
  },
  {
    id: "investment",
    title: "Investments",
    type: "asset",
    description: "Brokerage, retirement accounts, and other holdings.",
    accounts: [
      {
        name: "Core Brokerage",
        institution: "Northwind Investments",
        balance_minor: 185_670,
      },
      {
        name: "IRA",
        institution: "Northwind Investments",
        balance_minor: 139_890,
      },
    ],
  },
  {
    id: "borrowing",
    title: "Credit & Borrowing",
    type: "liability",
    description: "Lines of credit, cards, and short-term loans.",
    accounts: [
      {
        name: "Visa Rewards",
        institution: "Orbital Credit Union",
        balance_minor: 8_240,
      },
      {
        name: "Business Card",
        institution: "Axis Trust",
        balance_minor: 15_750,
      },
    ],
  },
  {
    id: "long-term",
    title: "Long-Term Borrowing",
    type: "liability",
    description: "Mortgages, student loans, and other long-duration debt.",
    accounts: [
      {
        name: "Mortgage",
        institution: "Atlas Home Loans",
        balance_minor: 355_420,
      },
      {
        name: "Student Loan",
        institution: "Lumen Education",
        balance_minor: 23_750,
      },
    ],
  },
];

const formatAccountBalance = (minor, type) => {
  const value = type === "liability" ? -Math.abs(minor) : minor;
  return formatAmount(value);
};

const getFilteredGroups = () => {
  if (state.accountFilter === "all") {
    return accountGroupsData;
  }
  return accountGroupsData.filter((group) => group.type === state.accountFilter);
};

const renderAccountGroups = () => {
  const container = document.querySelector(selectors.accountGroups);
  if (!container) {
    return;
  }

  const groups = getFilteredGroups();
  container.innerHTML = groups
    .map(
      (group) => `
        <article class="account-group">
          <header class="account-group__header">
            <div>
              <p class="account-group__title">${group.title}</p>
              <p class="muted">${group.description}</p>
            </div>
            <span class="muted">${group.accounts.length} account${group.accounts.length === 1 ? "" : "s"}</span>
          </header>
          <div class="account-cards">
            ${group.accounts
              .map(
                (account) => `
                  <div class="account-card">
                    <div class="account-card__header">
                      <span class="account-card__name">${account.name}</span>
                      <span class="account-card__balance">${formatAccountBalance(
                        account.balance_minor,
                        group.type
                      )}</span>
                    </div>
                    <div class="account-card__meta">
                      <span>${account.institution}</span>
                      <span>${group.type === "asset" ? "Asset" : "Liability"}</span>
                    </div>
                  </div>
                `
              )
              .join("")}
          </div>
        </article>
      `
    )
    .join("");
};

const updateAccountStats = () => {
  const assetsEl = document.querySelector(selectors.assetsTotal);
  const liabilitiesEl = document.querySelector(selectors.liabilitiesTotal);
  const netWorthEl = document.querySelector(selectors.netWorth);
  if (!assetsEl || !liabilitiesEl || !netWorthEl) {
    return;
  }

  const totals = accountGroupsData.reduce(
    (acc, group) => {
      const sum = group.accounts.reduce((grp, account) => grp + account.balance_minor, 0);
      if (group.type === "asset") {
        acc.assets += sum;
      } else {
        acc.liabilities += sum;
      }
      return acc;
    },
    { assets: 0, liabilities: 0 }
  );

  const netWorth = totals.assets - totals.liabilities;
  assetsEl.textContent = formatAmount(totals.assets);
  liabilitiesEl.textContent = formatAmount(-totals.liabilities);
  netWorthEl.textContent = formatAmount(netWorth);
};

const accountModalElement = document.querySelector(selectors.accountModal);
const toggleAccountModal = (show) => {
  if (!accountModalElement) {
    return;
  }
  accountModalElement.classList.toggle("is-visible", show);
  accountModalElement.setAttribute("aria-hidden", show ? "false" : "true");
};

const init = async () => {
  const transactionsBody = document.querySelector(selectors.transactionsBody);
  if (!transactionsBody) {
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
  };

  const handleHashChange = () => {
    const rawRoute = window.location.hash.replace("#/", "");
    activateRoute(rawRoute);
  };

  window.addEventListener("hashchange", handleHashChange);
  handleHashChange();

  updateHeaderStats();

  try {
    await refreshTransactions(transactionsBody);
  } catch (error) {
    console.error(error);
    const bodyEl = document.querySelector(selectors.transactionsBody);
    bodyEl.innerHTML = `
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
  if (addAccountBtn) {
    addAccountBtn.addEventListener("click", () => toggleAccountModal(true));
  }

  const modalClose = document.querySelector(selectors.modalClose);
  if (modalClose) {
    modalClose.addEventListener("click", () => toggleAccountModal(false));
  }

  if (accountModalElement) {
    accountModalElement.addEventListener("click", (event) => {
      if (event.target === accountModalElement) {
        toggleAccountModal(false);
      }
    });
  }

  renderAccountGroups();
  updateAccountStats();
};

document.addEventListener("DOMContentLoaded", init);
