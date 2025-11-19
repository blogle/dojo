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
};

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

const getTransactionStatus = (transactionDate) => {
  const today = new Date();
  const txDate = new Date(transactionDate);
  const diffTime = Math.abs(today - txDate);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 3 ? "Settled" : "Pending";
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

  const reconcileEl = document.querySelector(selectors.lastReconcileDate);
  if (reconcileEl) {
    const today = new Date();
    today.setDate(today.getDate() - 1);
    reconcileEl.textContent = today.toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }
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
    if (!tx) return;
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

const refreshTransactions = async (bodyEl) => {
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
    addAccountBtn.addEventListener("click", () => showAddAccountModal());
  }

  const modalClose = document.querySelector(selectors.modalClose);
  if (modalClose) {
    modalClose.addEventListener("click", () => toggleAccountModal(false));
  }

  if (modalOverlay) {
    modalOverlay.addEventListener("click", (event) => {
      if (event.target === modalOverlay) {
        toggleAccountModal(false);
      }
    });
  }

  const modalSubmit = document.querySelector(selectors.modalAddButton);
  if (modalSubmit) {
    modalSubmit.addEventListener("click", async () => {
      await handleAddAccount();
    });
  }

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
};

document.addEventListener("DOMContentLoaded", init);
