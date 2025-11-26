import { selectors } from "../../constants.js";
import { api } from "../../services/api.js";
import { formatAmount, minorToDollars, todayISO, currentMonthStartISO, dollarsToMinor } from "../../services/format.js";
import { populateSelect, setFormError, setButtonBusy } from "../../services/dom.js";
import { store } from "../../store.js";
import { filterUserFacingCategories } from "../categories/utils.js";
import { showToast } from "../toast.js";
import { refreshSelectOptions } from "../reference/index.js";

let categorySlugDirty = false;
let loadAllocationsData = async () => {};
let renderAllocationsPage = () => {};
let refreshAccountsPage = async () => {};
let refreshReferenceData = async () => {};
let updateHeaderStats = () => {};

const refreshReadyToAssign = (ready) => {
  store.setState((prev) => ({ ...prev, readyToAssign: ready }));
};

export const loadBudgetsData = async () => {
  const month = currentMonthStartISO();
  try {
    const [categories, groups, ready] = await Promise.all([
      api.budgets.categories(month),
      api.budgets.groups(),
      api.readyToAssign.current(month),
    ]);
    const normalizedCategories = (categories || []).map((category) => ({
      ...category,
      available_minor: category.available_minor ?? 0,
      activity_minor: category.activity_minor ?? 0,
      allocated_minor: category.allocated_minor ?? 0,
    }));
    const filtered = filterUserFacingCategories(normalizedCategories);
    const readyMinor = ready?.ready_to_assign_minor ?? 0;
    const activityMinor = filtered.reduce((total, category) => total + (category.activity_minor ?? 0), 0);
    const availableMinor = filtered.reduce((total, category) => total + (category.available_minor ?? 0), 0);
    const allocatedMinor = filtered.reduce((total, category) => total + (category.allocated_minor ?? 0), 0);
    const monthDate = new Date(`${month}T00:00:00`);
    store.setState((prev) => ({
      ...prev,
      budgets: {
        ...prev.budgets,
        rawCategories: normalizedCategories,
        categories: filtered,
        groups: (groups || []).sort((a, b) => a.sort_order - b.sort_order),
        readyToAssignMinor: readyMinor,
        activityMinor,
        availableMinor,
        allocatedMinor,
        monthStartISO: month,
        monthLabel: monthDate.toLocaleDateString(undefined, { year: "numeric", month: "long" }),
      },
    }));
    refreshReadyToAssign(ready);
    refreshSelectOptions();
    updateHeaderStats();
  } catch (error) {
    console.error("Failed to load budgets data", error);
    throw error;
  }
};

const renderGroupRows = (grouped, body) => {
  const renderGroup = (group) => {
    if (!group || (group.group_id === "uncategorized" && group.items.length === 0)) return;

    const groupRow = document.createElement("tr");
    groupRow.className = "group-row";
    groupRow.style.cursor = "pointer";
    groupRow.dataset.groupId = group.group_id;
    groupRow.dataset.testid = group.group_id === "uncategorized" ? "budget-group-uncategorized" : "budget-group-row";
    groupRow.innerHTML = `
      <td colspan="4" class="group-cell">
        <div class="group-cell__content">
          <span>${group.name}</span>
          <button type="button" class="icon-button" data-edit-group-id="${group.group_id}" data-testid="edit-group-btn" aria-label="Edit group">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
        </div>
      </td>
    `;
    body.appendChild(groupRow);

    group.items.forEach((cat) => {
      const row = document.createElement("tr");
      row.style.cursor = "pointer";
      row.dataset.categoryId = cat.category_id;
      row.dataset.groupId = cat.group_id || "uncategorized";
      row.dataset.testid = "budget-category-row";

      let goalText = "";
      if (cat.goal_type === "target_date" && cat.goal_amount_minor) {
        goalText = `<div class="u-muted u-small-note">Goal: ${formatAmount(cat.goal_amount_minor)} by ${cat.goal_target_date || "?"}</div>`;
      } else if (cat.goal_type === "recurring" && cat.goal_amount_minor) {
        const freq = cat.goal_frequency ? cat.goal_frequency.charAt(0).toUpperCase() + cat.goal_frequency.slice(1) : "Recurring";
        goalText = `<div class="u-muted u-small-note">${freq}: ${formatAmount(cat.goal_amount_minor)}</div>`;
      }

      row.innerHTML = `
        <td>
          <div class="category-row">
            <div>
              <span>${cat.name}</span>
              ${goalText}
            </div>
            <button type="button" class="icon-button" data-edit-category-id="${cat.category_id}" data-testid="edit-category-btn" aria-label="Edit category">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
          </div>
        </td>
        <td class="amount-cell">${formatAmount(cat.allocated_minor)}</td>
        <td class="amount-cell">${formatAmount(cat.activity_minor)}</td>
        <td class="amount-cell">
          <span class="${cat.available_minor < 0 ? "form-error" : ""}">${formatAmount(cat.available_minor)}</span>
        </td>
      `;
      body.appendChild(row);
    });
  };

  const state = store.getState();
  state.budgets.groups.forEach((g) => {
    renderGroup(grouped[g.group_id]);
  });
  if (grouped.uncategorized.items.length > 0) {
    renderGroup(grouped.uncategorized);
  }
};

export const renderBudgetsPage = () => {
  const state = store.getState();
  const readyEl = document.querySelector(selectors.budgetsReadyValue);
  const activityEl = document.querySelector(selectors.budgetsActivityValue);
  const availableEl = document.querySelector(selectors.budgetsAvailableValue);
  const monthLabelEl = document.querySelector(selectors.budgetsMonthLabel);
  if (readyEl) {
    readyEl.textContent = formatAmount(state.budgets.readyToAssignMinor);
  }
  if (activityEl) {
    activityEl.textContent = formatAmount(state.budgets.activityMinor);
  }
  if (availableEl) {
    availableEl.textContent = formatAmount(state.budgets.availableMinor);
  }
  if (monthLabelEl) {
    monthLabelEl.textContent = state.budgets.monthLabel || "—";
  }
  const body = document.querySelector("#budgets-body");
  if (!body) {
    return;
  }

  const grouped = {};
  state.budgets.groups.forEach((g) => {
    grouped[g.group_id] = { ...g, items: [] };
  });
  grouped.uncategorized = { group_id: "uncategorized", name: "Uncategorized", items: [] };

  state.budgets.categories.forEach((cat) => {
    const gid = cat.group_id || "uncategorized";
    if (!grouped[gid]) {
      grouped[gid] = { group_id: gid, name: "Unknown Group", items: [] };
    }
    grouped[gid].items.push(cat);
  });

  body.innerHTML = "";
  renderGroupRows(grouped, body);

  body.querySelectorAll("tr[data-group-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const gid = row.dataset.groupId;
        if (gid === "uncategorized") {
          openGroupDetailModal(grouped.uncategorized);

      } else {
        const group = grouped[gid];
        if (group) openGroupDetailModal(group);
      }
    });
    const editButton = row.querySelector('[data-edit-group-id]');
    if (editButton) {
      editButton.addEventListener("click", (event) => {
        event.stopPropagation();
        const gid = editButton.dataset.editGroupId;
        const group = state.budgets.groups.find((g) => g.group_id === gid);
        if (group) openGroupModal(group);
      });
    }
  });

  body.querySelectorAll("tr[data-category-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const cid = row.dataset.categoryId;
      const cat = state.budgets.categories.find((c) => c.category_id === cid);
      if (cat) openBudgetDetailModal(cat);
    });
    const editButton = row.querySelector('[data-edit-category-id]');
    if (editButton) {
      editButton.addEventListener("click", (event) => {
        event.stopPropagation();
        const cid = editButton.dataset.editCategoryId;
        const cat = state.budgets.categories.find((c) => c.category_id === cid);
        if (cat) openCategoryModal(cat);
      });
    }
  });
};

const handleQuickAllocation = async (categoryId, amountMinor, memo = "Quick allocation") => {
  const state = store.getState();
  if (state.budgets.readyToAssignMinor < amountMinor) {
    alert("Not enough Ready to Assign funds.");
    return;
  }
  const payload = {
    to_category_id: categoryId,
    amount_minor: amountMinor,
    allocation_date: todayISO(),
    memo,
  };
  try {
    await api.budgets.createAllocation(payload);
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

const handleGroupQuickAllocation = async (allocations, label) => {
  const totalNeeded = allocations.reduce((sum, alloc) => sum + alloc.amount_minor, 0);
  if (totalNeeded <= 0) {
    alert("Nothing to allocate for this action.");
    return;
  }
  if (store.getState().budgets.readyToAssignMinor < totalNeeded) {
    alert("Not enough Ready to Assign funds.");
    return;
  }

  try {
    for (const alloc of allocations) {
      await api.budgets.createAllocation({
        to_category_id: alloc.category_id,
        amount_minor: alloc.amount_minor,
        allocation_date: todayISO(),
        memo: alloc.memo,
      });
    }
    closeGroupDetailModal();
    await Promise.all([loadBudgetsData(), loadAllocationsData(), refreshAccountsPage()]);
    renderBudgetsPage();
    renderAllocationsPage();
    showToast(`${label} (${formatAmount(totalNeeded)})`);
  } catch (error) {
    console.error(error);
    alert(error.message || "Partial failure during group allocation.");
    await loadBudgetsData();
    renderBudgetsPage();
  }
};

const openBudgetDetailModal = (category) => {
  const modal = document.querySelector(selectors.budgetDetailModal);
  if (!modal) return;

  store.setState((prev) => ({ ...prev, activeBudgetDetail: category }));

  document.querySelector(selectors.budgetDetailTitle).textContent = category.name;
  const leftover = category.available_minor - category.allocated_minor - category.activity_minor;
  document.querySelector(selectors.budgetDetailLeftover).textContent = formatAmount(leftover);
  document.querySelector(selectors.budgetDetailBudgeted).textContent = formatAmount(category.allocated_minor);
  document.querySelector(selectors.budgetDetailActivity).textContent = formatAmount(category.activity_minor);
  document.querySelector(selectors.budgetDetailAvailable).textContent = formatAmount(category.available_minor);

  const actionsContainer = document.querySelector(selectors.budgetDetailQuickActions);
  actionsContainer.innerHTML = "";

  const createBtn = (label, amount, memo) => {
    const btn = document.createElement("button");
    btn.className = "secondary";
    btn.textContent = `${label}: ${formatAmount(amount)}`;
    btn.onclick = () => handleQuickAllocation(category.category_id, amount, memo);
    actionsContainer.appendChild(btn);
  };

  if (category.goal_amount_minor && category.goal_amount_minor > 0) {
    const needed = Math.max(0, category.goal_amount_minor - category.available_minor);
    if (needed > 0) {
      createBtn("Fund Goal", needed, "Fund Goal");
    } else {
      const p = document.createElement("p");
      p.className = "u-muted u-small-note";
      p.textContent = "Goal fully funded.";
      actionsContainer.appendChild(p);
    }
  } else {
    const p = document.createElement("p");
    p.className = "u-muted u-small-note";
    p.textContent = "No goal set.";
    actionsContainer.appendChild(p);
  }

  if (category.last_month_allocated_minor > 0) {
    createBtn("Budgeted Last Month", category.last_month_allocated_minor, "Budgeted Last Month");
  }

  const spentLastMonth = -1 * category.last_month_activity_minor;
  if (spentLastMonth > 0) {
    createBtn("Spent Last Month", spentLastMonth, "Spent Last Month");
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
  store.setState((prev) => ({ ...prev, activeBudgetDetail: null }));
};

const openGroupDetailModal = (group) => {
  const modal = document.querySelector(selectors.groupDetailModal);
  if (!modal) return;

  document.querySelector(selectors.groupDetailTitle).textContent = group.name;

  let totalLeftover = 0;
  let totalBudgeted = 0;
  let totalActivity = 0;
  let totalAvailable = 0;

  group.items.forEach((cat) => {
    const leftover = cat.available_minor - cat.allocated_minor - cat.activity_minor;
    totalLeftover += leftover;
    totalBudgeted += cat.allocated_minor;
    totalActivity += cat.activity_minor;
    totalAvailable += cat.available_minor;
  });

  document.querySelector(selectors.groupDetailLeftover).textContent = formatAmount(totalLeftover);
  document.querySelector(selectors.groupDetailBudgeted).textContent = formatAmount(totalBudgeted);
  document.querySelector(selectors.groupDetailActivity).textContent = formatAmount(totalActivity);
  document.querySelector(selectors.groupDetailAvailable).textContent = formatAmount(totalAvailable);

  const actionsContainer = document.querySelector(selectors.groupDetailQuickActions);
  actionsContainer.innerHTML = "";

  const fundAllocations = [];
  const budgetedAllocations = [];
  const spentAllocations = [];

  group.items.forEach((cat) => {
    if (cat.goal_amount_minor && cat.goal_amount_minor > 0) {
      const needed = Math.max(0, cat.goal_amount_minor - cat.available_minor);
      if (needed > 0) {
        fundAllocations.push({
          category_id: cat.category_id,
          amount_minor: needed,
          memo: "Group quick allocation - Fund Goal",
        });
      }
    }

    if (cat.last_month_allocated_minor && cat.last_month_allocated_minor > 0) {
      budgetedAllocations.push({
        category_id: cat.category_id,
        amount_minor: cat.last_month_allocated_minor,
        memo: "Group quick allocation - Budgeted Last Month",
      });
    }

    const spentLastMonth = Math.max(0, -1 * cat.last_month_activity_minor);
    if (spentLastMonth > 0) {
      spentAllocations.push({
        category_id: cat.category_id,
        amount_minor: spentLastMonth,
        memo: "Group quick allocation - Spent Last Month",
      });
    }
  });

  const renderGroupAction = (label, allocations) => {
    const total = allocations.reduce((sum, alloc) => sum + alloc.amount_minor, 0);
    if (total <= 0) {
      return false;
    }
    const btn = document.createElement("button");
    btn.className = "secondary";
    btn.textContent = `${label}: ${formatAmount(total)}`;
    btn.onclick = () => handleGroupQuickAllocation(allocations, label);
    actionsContainer.appendChild(btn);
    return true;
  };

  let renderedAction = false;
  renderedAction = renderGroupAction("Fund Underfunded", fundAllocations) || renderedAction;
  renderedAction = renderGroupAction("Budgeted Last Month", budgetedAllocations) || renderedAction;
  renderedAction = renderGroupAction("Spent Last Month", spentAllocations) || renderedAction;

  if (!renderedAction) {
    const p = document.createElement("p");
    p.className = "u-muted u-small-note";
    p.textContent = "No quick allocations available for this group.";
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
  store.setState((prev) => ({ ...prev, pendingCategoryEdit: category }));
  categorySlugDirty = false;
  setFormError(errorEl, "");

  if (groupSelect) {
    const state = store.getState();
    populateSelect(groupSelect, state.budgets.groups, { valueKey: "group_id", labelKey: "name" }, "Uncategorized");
  }

  const goalRadios = form.querySelectorAll("input[name='goal_type']");
  goalRadios.forEach((radio) => {
    radio.checked = radio.value === "recurring";
  });
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

    if (category.goal_type) {
      const radio = form.querySelector(`input[name='goal_type'][value='${category.goal_type}']`);
      if (radio) {
        radio.checked = true;
        const section = form.querySelector(`[data-goal-section='${category.goal_type}']`);
        if (section) section.style.display = "block";
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
  store.setState((prev) => ({ ...prev, pendingCategoryEdit: null }));
};

const slugifyCategoryName = (value) => {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  return normalized.replace(/^_+|_+$/g, "") || "category";
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

  const isEditing = Boolean(store.getState().pendingCategoryEdit);

  try {
    setButtonBusy(submitButton, true);
    setFormError(errorEl, "");
    if (isEditing) {
      await api.budgets.updateCategory(store.getState().pendingCategoryEdit.category_id, payload);
    } else {
      if (slug) {
        payload.category_id = slug;
      }
      await api.budgets.createCategory(payload);
    }
    closeCategoryModal();
    await Promise.all([loadBudgetsData(), refreshReferenceData()]);
    renderBudgetsPage();
    showToast(isEditing ? `Renamed ${name}` : `Created ${name}`);
  } catch (error) {
    console.error(error);
    setFormError(errorEl, error.message || "Failed to save category.");
  } finally {
    setButtonBusy(submitButton, false);
  }
};

const openGroupModal = (group = null) => {
  const modal = document.querySelector(selectors.groupModal);
  const title = document.querySelector(selectors.groupModalTitle);
  const form = document.querySelector(selectors.groupForm);
  const errorEl = document.querySelector(selectors.groupError);
  if (!modal || !form) return;

  store.setState((prev) => ({ ...prev, pendingGroupEdit: group }));
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
  store.setState((prev) => ({ ...prev, pendingGroupEdit: null }));
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
    const isEditing = Boolean(store.getState().pendingGroupEdit);

    if (isEditing) {
      await api.budgets.updateGroup(store.getState().pendingGroupEdit.group_id, { name, sort_order: sortOrder, is_active: true });
    } else {
      const groupId = slugifyCategoryName(name);
      await api.budgets.createGroup({ group_id: groupId, name, sort_order: sortOrder, is_active: true });
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

const initBudgetDetailModal = () => {
  const modal = document.querySelector(selectors.budgetDetailModal);
  if (!modal) return;
  const closeButton = document.querySelector(selectors.budgetDetailClose);
  closeButton?.addEventListener("click", () => closeBudgetDetailModal());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeBudgetDetailModal();
  });
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
    if (store.getState().pendingCategoryEdit || categorySlugDirty || !slugInput) {
      return;
    }
    slugInput.value = slugifyCategoryName(nameInput.value);
  });
  slugInput?.addEventListener("input", () => {
    categorySlugDirty = true;
  });

  const formEl = document.querySelector(selectors.categoryForm);
  const goalRadios = formEl.querySelectorAll("input[name='goal_type']");
  goalRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      formEl.querySelector("[data-goal-section='target_date']").style.display = radio.value === "target_date" ? "block" : "none";
      formEl.querySelector("[data-goal-section='recurring']").style.display = radio.value === "recurring" ? "block" : "none";
    });
  });
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

export const initBudgets = ({
  onAllocationsRefresh,
  onAllocationsRender,
  onAccountsRefresh,
  onReferenceRefresh,
  onHeaderStats,
} = {}) => {
  loadAllocationsData = onAllocationsRefresh || (() => Promise.resolve());
  renderAllocationsPage = onAllocationsRender || (() => {});
  refreshAccountsPage = onAccountsRefresh || (() => Promise.resolve());
  refreshReferenceData = onReferenceRefresh || (() => Promise.resolve());
  updateHeaderStats = onHeaderStats || (() => {});

  const openModalButton = document.querySelector("[data-open-category-modal]");
  openModalButton?.addEventListener("click", () => openCategoryModal());

  const openGroupButton = document.querySelector("[data-open-group-modal]");
  openGroupButton?.addEventListener("click", () => openGroupModal());

  initBudgetDetailModal();
  initGroupDetailModal();
  initCategoryModal();
  initGroupModal();
};
