import { selectors } from "../../constants.js";
import { api } from "../../services/api.js";
import {
	formatAmount,
	minorToDollars,
	todayISO,
	currentMonthStartISO,
	dollarsToMinor,
} from "../../services/format.js";
import {
	populateSelect,
	setFormError,
	setButtonBusy,
} from "../../services/dom.js";
import { store } from "../../store.js";
import { filterUserFacingCategories } from "../categories/utils.js";
import { showToast } from "../toast.js";
import { refreshSelectOptions } from "../reference/index.js";
import { waitForPendingAllocations } from "../../services/allocationTracker.js";

let categorySlugDirty = false;
let loadAllocationsData = async () => {};
let renderAllocationsPage = () => {};
let refreshAccountsPage = async () => {};
let refreshReferenceData = async () => {};
let updateHeaderStats = () => {};

const dragHandleIcon = `
  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
    <path d="M8 1.5 10 3.5 9.2 4.3 8 3.1 6.8 4.3 6 3.5Z" />
    <path d="M8 14.5 6 12.5 6.8 11.7 8 12.9 9.2 11.7 10 12.5Z" />
    <path d="M4.25 6.25h7.5v1h-7.5zM4.25 8.75h7.5v1h-7.5zM4.25 11.25h7.5v1h-7.5z" />
  </svg>
`;

let activeDragGroupId = null;

const refreshReadyToAssign = (ready) => {
	store.setState((prev) => ({ ...prev, readyToAssign: ready }));
};

const isGroupCollapsed = (groupId) => {
	const collapsed = store.getState().budgets.collapsedGroups || {};
	return Boolean(collapsed[groupId]);
};

const toggleGroupCollapsed = (groupId) => {
	store.setState((prev) => {
		const nextCollapsed = { ...(prev.budgets.collapsedGroups || {}) };
		nextCollapsed[groupId] = !nextCollapsed[groupId];
		return {
			...prev,
			budgets: { ...prev.budgets, collapsedGroups: nextCollapsed },
		};
	});
	renderBudgetsPage();
};

const getUncategorizedBudgetCategories = () => {
	const state = store.getState();
	const categories = filterUserFacingCategories(state.budgets.rawCategories || []);
	return categories
		.filter((category) => !category.group_id)
		.sort((a, b) => a.name.localeCompare(b.name));
};

const getGroupBudgetCategories = (groupId) => {
	if (!groupId) return [];
	const state = store.getState();
	const categories = filterUserFacingCategories(state.budgets.rawCategories || []);
	return categories
		.filter((category) => category.group_id === groupId)
		.sort((a, b) => a.name.localeCompare(b.name));
};

const buildCategoryUpdatePayload = (category, targetGroupId) => ({
	name: category.name,
	group_id: targetGroupId,
	is_active: category.is_active !== false,
	goal_type: category.goal_type || null,
	goal_amount_minor: category.goal_amount_minor ?? null,
	goal_target_date: category.goal_target_date || null,
	goal_frequency: category.goal_frequency || null,
});

const formatCategoryOptionLabel = (label, isSelected) => `${isSelected ? "[x]" : "[ ]"} ${label}`;

const refreshSelectOptionIndicators = (selectEl) => {
	if (!selectEl) return;
	Array.from(selectEl.options || []).forEach((option) => {
		const baseLabel = option.dataset.baseLabel || option.textContent || "";
		option.textContent = formatCategoryOptionLabel(
			baseLabel.replace(/^\[(x| )\]\s+/, ""),
			option.selected,
		);
	});
};

const populateGroupCategorySelect = (selectEl, helperEl, groupId) => {
	if (!selectEl) {
		return;
	}
	const uncategorized = getUncategorizedBudgetCategories();
	const inGroup = getGroupBudgetCategories(groupId);
	const combined = [...inGroup, ...uncategorized];
	selectEl.innerHTML = "";
	if (combined.length === 0) {
		const option = document.createElement("option");
		option.value = "";
		option.textContent = "No uncategorized budgets";
		option.disabled = true;
		option.selected = true;
		selectEl.appendChild(option);
		selectEl.disabled = true;
		if (helperEl) {
			helperEl.textContent = "All budgets already belong to a group.";
		}
		return;
	}
	selectEl.disabled = false;
	combined.forEach((category) => {
		const option = document.createElement("option");
		option.value = category.category_id;
		option.selected = category.group_id === groupId;
		option.dataset.baseLabel = category.name;
		option.textContent = formatCategoryOptionLabel(category.name, option.selected);
		selectEl.appendChild(option);
	});
	if (helperEl) {
		helperEl.textContent =
			"Toggle budgets to include them in this group. Untoggle to move back to Uncategorized.";
	}
};

const firstOfNextMonthISO = () => {
	const today = new Date();
	const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, 1);
	const year = nextMonth.getFullYear();
	const month = `${nextMonth.getMonth() + 1}`.padStart(2, "0");
	const day = `${nextMonth.getDate()}`.padStart(2, "0");
	return `${year}-${month}-${day}`;
};

const getNextGroupSortOrder = () => {
	const state = store.getState();
	const groups =
		(state.budgets.reorderDraft && state.budgets.reorderDraft.length > 0
			? state.budgets.reorderDraft
			: state.budgets.groups) || [];
	if (!groups.length) return 1;
	const maxOrder = Math.max(
		...groups.map((group) => (Number.isFinite(group.sort_order) ? group.sort_order : 0)),
	);
	return maxOrder + 1;
};

const reorderGroupsByIds = (groups = [], orderIds = []) => {
	if (!orderIds || orderIds.length === 0) {
		return [...groups];
	}
	const indexById = new Map(orderIds.map((id, index) => [id, index]));
	return [...groups].sort((a, b) => {
		const aIndex = indexById.has(a.group_id)
			? indexById.get(a.group_id)
			: orderIds.length + (a.sort_order ?? 0);
		const bIndex = indexById.has(b.group_id)
			? indexById.get(b.group_id)
			: orderIds.length + (b.sort_order ?? 0);
		if (aIndex === bIndex) {
			return (a.sort_order ?? 0) - (b.sort_order ?? 0);
		}
		return aIndex - bIndex;
	});
};

const updateReorderControls = () => {
	const reorderButton = document.querySelector(selectors.budgetsReorderButton);
	const saveButton = document.querySelector(selectors.budgetsReorderSave);
	const cancelButton = document.querySelector(selectors.budgetsReorderCancel);
	const container = document.querySelector(".budgets-page__reorder");
	const isReorderMode = store.getState().budgets.reorderMode;
	if (container) {
		container.classList.toggle("is-editing", isReorderMode);
	}
	if (reorderButton) {
		reorderButton.disabled = isReorderMode;
	}
	if (saveButton) {
		saveButton.disabled = !isReorderMode;
	}
	if (cancelButton) {
		cancelButton.disabled = !isReorderMode;
	}
};

const enterGroupReorderMode = () => {
	const state = store.getState();
	const orderIds =
		(state.budgets.reorderDraft?.map((group) => group.group_id) ||
			state.budgets.groups.map((group) => group.group_id)) ?? [];
	const draft = reorderGroupsByIds(state.budgets.groups, orderIds);
	store.setState((prev) => ({
		...prev,
		budgets: { ...prev.budgets, reorderMode: true, reorderDraft: draft },
	}));
	renderBudgetsPage();
};

const exitGroupReorderMode = () => {
	store.setState((prev) => ({
		...prev,
		budgets: { ...prev.budgets, reorderMode: false, reorderDraft: [] },
	}));
	renderBudgetsPage();
};

const cancelGroupReorder = () => {
	exitGroupReorderMode();
	showToast("Reorder canceled");
};

const moveGroupInDraft = (sourceId, targetId) => {
	const state = store.getState();
	if (!state.budgets.reorderMode) return;
	const draft =
		(state.budgets.reorderDraft && state.budgets.reorderDraft.length > 0
			? state.budgets.reorderDraft
			: state.budgets.groups) || [];
	const sourceIndex = draft.findIndex((group) => group.group_id === sourceId);
	const targetIndex = draft.findIndex((group) => group.group_id === targetId);
	if (sourceIndex === -1 || targetIndex === -1 || sourceIndex === targetIndex) {
		return;
	}
	const updated = [...draft];
	const [moved] = updated.splice(sourceIndex, 1);
	updated.splice(targetIndex, 0, moved);
	store.setState((prev) => ({
		...prev,
		budgets: { ...prev.budgets, reorderDraft: updated },
	}));
	renderBudgetsPage();
};

const handleGroupDragStart = (event) => {
	const target = event.currentTarget;
	activeDragGroupId = target?.dataset.groupId || null;
	if (target) {
		target.classList.add("is-dragging");
	}
	if (event.dataTransfer) {
		event.dataTransfer.effectAllowed = "move";
	}
};

const handleGroupDragOver = (event) => {
	if (!store.getState().budgets.reorderMode) return;
	event.preventDefault();
	if (event.dataTransfer) {
		event.dataTransfer.dropEffect = "move";
	}
};

const handleGroupDrop = (event) => {
	if (!store.getState().budgets.reorderMode) return;
	event.preventDefault();
	const targetId = event.currentTarget?.dataset.groupId;
	if (!activeDragGroupId || !targetId || activeDragGroupId === targetId) {
		return;
	}
	moveGroupInDraft(activeDragGroupId, targetId);
	activeDragGroupId = null;
};

const handleGroupDragEnd = (event) => {
	activeDragGroupId = null;
	event.currentTarget?.classList.remove("is-dragging");
};

const persistGroupReorder = async () => {
	const saveButton = document.querySelector(selectors.budgetsReorderSave);
	const state = store.getState();
	const draft =
		(state.budgets.reorderDraft && state.budgets.reorderDraft.length > 0
			? state.budgets.reorderDraft
			: state.budgets.groups) || [];
	if (!draft.length) {
		exitGroupReorderMode();
		return;
	}
	try {
		setButtonBusy(saveButton, true);
		const updates = draft.map((group, index) =>
			api.budgets.updateGroup(group.group_id, {
				name: group.name,
				sort_order: index + 1,
				is_active: group.is_active !== false,
			}),
		);
		await Promise.all(updates);
		exitGroupReorderMode();
		await loadBudgetsData({ skipPendingCheck: true });
		renderBudgetsPage();
		showToast("Saved group order");
	} catch (error) {
		console.error(error);
		alert(error.message || "Failed to save group order.");
	} finally {
		setButtonBusy(saveButton, false);
	}
};

export const loadBudgetsData = async ({ skipPendingCheck = false } = {}) => {
	if (!skipPendingCheck) {
		await waitForPendingAllocations();
	}
	const month = currentMonthStartISO();
	try {
		const [categories, groups, ready] = await Promise.all([
			api.budgets.categories(month),
			api.budgets.groups(),
			api.readyToAssign.current(month),
		]);
		const collapsedGroups = {};
		const existingCollapsed =
			store.getState().budgets.collapsedGroups || Object.create(null);
		const validGroupIds = new Set([
			...(groups || []).map((group) => group.group_id),
			"uncategorized",
		]);
		validGroupIds.forEach((gid) => {
			collapsedGroups[gid] = existingCollapsed[gid] ?? false;
		});
		const normalizedCategories = (categories || []).map((category) => ({
			...category,
			available_minor: category.available_minor ?? 0,
			activity_minor: category.activity_minor ?? 0,
			allocated_minor: category.allocated_minor ?? 0,
		}));
		const filtered = filterUserFacingCategories(normalizedCategories);
		const readyMinor = ready?.ready_to_assign_minor ?? 0;
		const activityMinor = filtered.reduce(
			(total, category) => total + (category.activity_minor ?? 0),
			0,
		);
		const availableMinor = filtered.reduce(
			(total, category) => total + (category.available_minor ?? 0),
			0,
		);
		const allocatedMinor = filtered.reduce(
			(total, category) => total + (category.allocated_minor ?? 0),
			0,
		);
		const monthDate = new Date(`${month}T00:00:00`);
		const sortedGroups = (groups || []).sort((a, b) => a.sort_order - b.sort_order);
		const previousState = store.getState();
		const previousOrderIds =
			previousState.budgets.reorderDraft?.map((group) => group.group_id) || [];
		const isReorderMode = Boolean(previousState.budgets.reorderMode);
		const reorderDraft = isReorderMode
			? reorderGroupsByIds(
					sortedGroups,
					previousOrderIds.length > 0
						? previousOrderIds
						: sortedGroups.map((group) => group.group_id),
				)
			: [];
		store.setState((prev) => ({
			...prev,
			budgets: {
				...prev.budgets,
				rawCategories: normalizedCategories,
				categories: filtered,
				groups: sortedGroups,
				reorderMode: isReorderMode,
				reorderDraft: isReorderMode ? reorderDraft : [],
				collapsedGroups,
				readyToAssignMinor: readyMinor,
				activityMinor,
				availableMinor,
				allocatedMinor,
				monthStartISO: month,
				monthLabel: monthDate.toLocaleDateString(undefined, {
					year: "numeric",
					month: "long",
				}),
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

const renderGroupRows = (grouped, body, orderedGroups = []) => {
	const state = store.getState();
	const isReorderMode = state.budgets.reorderMode;

	const renderGroup = (group) => {
		if (
			!group ||
			(group.group_id === "uncategorized" && group.items.length === 0)
		)
			return;

		const collapsed = isGroupCollapsed(group.group_id);
		const isReorderable = isReorderMode && group.group_id !== "uncategorized";
		const groupRow = document.createElement("tr");
		groupRow.className = `group-row${isReorderable ? " is-draggable" : ""}`;
		groupRow.style.cursor = isReorderable ? "grab" : "pointer";
		groupRow.dataset.groupId = group.group_id;
		groupRow.dataset.testid = "budget-group-row";
		groupRow.dataset.collapsed = collapsed ? "true" : "false";
		groupRow.draggable = isReorderable;
		const dragHandle = isReorderable
			? `<span class="group-row__drag-handle" aria-label="Drag to reorder ${group.name}">${dragHandleIcon}</span>`
			: "";
		groupRow.innerHTML = `
      <td colspan="4" class="group-cell">
        <div class="group-cell__content">
          ${dragHandle}
          <span class="group-cell__label">${group.name}</span>
          <button
            type="button"
            class="group-toggle"
            data-toggle-group-id="${group.group_id}"
            aria-expanded="${!collapsed}"
            aria-label="${collapsed ? "Expand" : "Collapse"} ${group.name} categories"
          >
            <span class="group-toggle__icon" aria-hidden="true">▾</span>
          </button>
        </div>
      </td>
    `;
		body.appendChild(groupRow);

		if (isReorderable) {
			groupRow.addEventListener("dragstart", handleGroupDragStart);
			groupRow.addEventListener("dragover", handleGroupDragOver);
			groupRow.addEventListener("drop", handleGroupDrop);
			groupRow.addEventListener("dragend", handleGroupDragEnd);
		}

		if (collapsed) {
			return;
		}

		group.items.forEach((cat) => {
			const row = document.createElement("tr");
			row.style.cursor = isReorderMode ? "default" : "pointer";
			row.dataset.categoryId = cat.category_id;
			row.dataset.testid = "budget-category-row";

			let goalText = "";
			if (cat.goal_type === "target_date" && cat.goal_amount_minor) {
				goalText = `<div class="u-muted u-small-note">Goal: ${formatAmount(cat.goal_amount_minor)} by ${cat.goal_target_date || "?"}</div>`;
			} else if (cat.goal_type === "recurring" && cat.goal_amount_minor) {
				const freq = cat.goal_frequency
					? cat.goal_frequency.charAt(0).toUpperCase() +
						cat.goal_frequency.slice(1)
					: "Recurring";
				goalText = `<div class="u-muted u-small-note">${freq}: ${formatAmount(cat.goal_amount_minor)}</div>`;
			}

			row.innerHTML = `
        <td data-testid="budget-col-name">
          <div class="category-row">
            <div>
              <span>${cat.name}</span>
              ${goalText}
            </div>
          </div>
        </td>
        <td class="amount-cell" data-testid="budget-col-budgeted">${formatAmount(cat.allocated_minor)}</td>
        <td class="amount-cell" data-testid="budget-col-activity">${formatAmount(cat.activity_minor)}</td>
        <td class="amount-cell" data-testid="budget-col-available">
          <span class="${cat.available_minor < 0 ? "form-error" : ""}">${formatAmount(cat.available_minor)}</span>
        </td>
      `;
			body.appendChild(row);
		});
	};

	orderedGroups.forEach((g) => {
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

	updateReorderControls();

	const baseGroups = state.budgets.groups || [];
	const orderedGroups =
		state.budgets.reorderMode && state.budgets.reorderDraft?.length
			? state.budgets.reorderDraft
			: baseGroups;

	const grouped = {};
	baseGroups.forEach((g) => {
		grouped[g.group_id] = { ...g, items: [] };
	});
	grouped.uncategorized = {
		group_id: "uncategorized",
		name: "Uncategorized",
		items: [],
	};

	state.budgets.categories.forEach((cat) => {
		const gid = cat.group_id || "uncategorized";
		if (!grouped[gid]) {
			grouped[gid] = { group_id: gid, name: "Unknown Group", items: [] };
		}
		grouped[gid].items.push(cat);
	});

	body.innerHTML = "";
	renderGroupRows(grouped, body, orderedGroups);

	body.querySelectorAll("[data-toggle-group-id]").forEach((button) => {
		button.addEventListener("click", (event) => {
			event.stopPropagation();
			const gid = button.dataset.toggleGroupId;
			if (gid) toggleGroupCollapsed(gid);
		});
	});

	if (!state.budgets.reorderMode) {
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
			const editButton = row.querySelector("[data-edit-group-id]");
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
			const editButton = row.querySelector("[data-edit-category-id]");
			if (editButton) {
				editButton.addEventListener("click", (event) => {
					event.stopPropagation();
					const cid = editButton.dataset.editCategoryId;
					const cat = state.budgets.categories.find((c) => c.category_id === cid);
					if (cat) openCategoryModal(cat);
				});
			}
		});
	}
};

const handleQuickAllocation = async (
	categoryId,
	amountMinor,
	memo = "Quick allocation",
) => {
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
		await Promise.all([
			loadBudgetsData({ skipPendingCheck: true }),
			loadAllocationsData(),
			refreshAccountsPage(),
		]);
		renderBudgetsPage();
		renderAllocationsPage();
		showToast(`Allocated ${formatAmount(amountMinor)}`);
	} catch (error) {
		console.error(error);
		alert(error.message || "Allocation failed.");
	}
};

const handleGroupQuickAllocation = async (allocations, label) => {
	const totalNeeded = allocations.reduce(
		(sum, alloc) => sum + alloc.amount_minor,
		0,
	);
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
		await Promise.all([
			loadBudgetsData({ skipPendingCheck: true }),
			loadAllocationsData(),
			refreshAccountsPage(),
		]);
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

	document.querySelector(selectors.budgetDetailTitle).textContent =
		category.name;
	const leftover =
		category.available_minor -
		category.allocated_minor -
		category.activity_minor;
	document.querySelector(selectors.budgetDetailLeftover).textContent =
		formatAmount(leftover);
	document.querySelector(selectors.budgetDetailBudgeted).textContent =
		formatAmount(category.allocated_minor);
	document.querySelector(selectors.budgetDetailActivity).textContent =
		formatAmount(category.activity_minor);
	document.querySelector(selectors.budgetDetailAvailable).textContent =
		formatAmount(category.available_minor);

	const actionsContainer = document.querySelector(
		selectors.budgetDetailQuickActions,
	);
	actionsContainer.innerHTML = "";

	const createBtn = (label, amount, memo) => {
		const btn = document.createElement("button");
		btn.className = "secondary";
		btn.textContent = `${label}: ${formatAmount(amount)}`;
		btn.onclick = () =>
			handleQuickAllocation(category.category_id, amount, memo);
		actionsContainer.appendChild(btn);
	};

	if (category.goal_amount_minor && category.goal_amount_minor > 0) {
		const needed = Math.max(
			0,
			category.goal_amount_minor - category.available_minor,
		);
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
		createBtn(
			"Budgeted Last Month",
			category.last_month_allocated_minor,
			"Budgeted Last Month",
		);
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
		const leftover =
			cat.available_minor - cat.allocated_minor - cat.activity_minor;
		totalLeftover += leftover;
		totalBudgeted += cat.allocated_minor;
		totalActivity += cat.activity_minor;
		totalAvailable += cat.available_minor;
	});

	document.querySelector(selectors.groupDetailLeftover).textContent =
		formatAmount(totalLeftover);
	document.querySelector(selectors.groupDetailBudgeted).textContent =
		formatAmount(totalBudgeted);
	document.querySelector(selectors.groupDetailActivity).textContent =
		formatAmount(totalActivity);
	document.querySelector(selectors.groupDetailAvailable).textContent =
		formatAmount(totalAvailable);

	const actionsContainer = document.querySelector(
		selectors.groupDetailQuickActions,
	);
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
		const total = allocations.reduce(
			(sum, alloc) => sum + alloc.amount_minor,
			0,
		);
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
	renderedAction =
		renderGroupAction("Fund Underfunded", fundAllocations) || renderedAction;
	renderedAction =
		renderGroupAction("Budgeted Last Month", budgetedAllocations) ||
		renderedAction;
	renderedAction =
		renderGroupAction("Spent Last Month", spentAllocations) || renderedAction;

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
		populateSelect(
			groupSelect,
			state.budgets.groups,
			{ valueKey: "group_id", labelKey: "name" },
			"Uncategorized",
		);
	}

	const goalRadios = form.querySelectorAll("input[name='goal_type']");
	goalRadios.forEach((radio) => {
		radio.checked = radio.value === "recurring";
	});
	form.querySelector("[data-goal-section='target_date']").style.display =
		"none";
	form.querySelector("[data-goal-section='recurring']").style.display = "block";
	form.querySelector("input[name='target_date_dt']").value = "";
	form.querySelector("input[name='target_amount']").value = "";
	form.querySelector("select[name='frequency']").value = "monthly";
	form.querySelector("input[name='recurring_date_dt']").value = firstOfNextMonthISO();
	form.querySelector("input[name='recurring_amount']").value = "";

	if (category) {
		title.textContent = "Rename category";
		hint.textContent =
			"Slug edits require migrations, so only the name is editable.";
		nameInput.value = category.name;
		slugInput.value = category.category_id;
		if (groupSelect) groupSelect.value = category.group_id || "";

		if (category.goal_type) {
			const radio = form.querySelector(
				`input[name='goal_type'][value='${category.goal_type}']`,
			);
			if (radio) {
				radio.checked = true;
				const section = form.querySelector(
					`[data-goal-section='${category.goal_type}']`,
				);
				if (section) section.style.display = "block";
				const otherType =
					category.goal_type === "recurring" ? "target_date" : "recurring";
				const otherSection = form.querySelector(
					`[data-goal-section='${otherType}']`,
				);
				if (otherSection) otherSection.style.display = "none";
				if (category.goal_type === "target_date") {
					form.querySelector("input[name='target_date_dt']").value =
						category.goal_target_date || "";
					form.querySelector("input[name='target_amount']").value =
						category.goal_amount_minor
							? minorToDollars(category.goal_amount_minor)
							: "";
				} else if (category.goal_type === "recurring") {
					form.querySelector("select[name='frequency']").value =
						category.goal_frequency || "monthly";
					form.querySelector("input[name='recurring_date_dt']").value =
						category.goal_target_date || "";
					form.querySelector("input[name='recurring_amount']").value =
						category.goal_amount_minor
							? minorToDollars(category.goal_amount_minor)
							: "";
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
			await api.budgets.updateCategory(
				store.getState().pendingCategoryEdit.category_id,
				payload,
			);
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
	const uncategorizedSelect = form.querySelector(selectors.groupUncategorizedSelect);
	const uncategorizedHelper = form.querySelector(selectors.groupUncategorizedHelper);

	if (group) {
		title.textContent = "Edit Group";
		nameInput.value = group.name;
	} else {
		title.textContent = "Add Group";
		nameInput.value = "";
	}

	if (uncategorizedSelect) {
		populateGroupCategorySelect(uncategorizedSelect, uncategorizedHelper, group?.group_id || null);
		refreshSelectOptionIndicators(uncategorizedSelect);
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
	const errorEl = document.querySelector(selectors.groupError);
	const submitButton = document.querySelector(selectors.groupSubmit);
	const uncategorizedSelect = document.querySelector(
		selectors.groupUncategorizedSelect,
	);

	if (!name) {
		setFormError(errorEl, "Name is required.");
		return;
	}

	const selectedCategoryIds =
		uncategorizedSelect && !uncategorizedSelect.disabled
			? Array.from(uncategorizedSelect.selectedOptions || [])
					.map((option) => option.value)
					.filter(Boolean)
			: [];

	try {
		setButtonBusy(submitButton, true);
		setFormError(errorEl, "");
		const state = store.getState();
		const pendingGroup = state.pendingGroupEdit;
		const isEditing = Boolean(pendingGroup);
		const targetGroupId = isEditing
			? pendingGroup.group_id
			: slugifyCategoryName(name);
		const sortOrder = isEditing
			? pendingGroup.sort_order ?? 0
			: getNextGroupSortOrder();

		if (isEditing) {
			await api.budgets.updateGroup(pendingGroup.group_id, {
				name,
				sort_order: sortOrder,
				is_active: true,
			});
		} else {
			await api.budgets.createGroup({
				group_id: targetGroupId,
				name,
				sort_order: sortOrder,
				is_active: true,
			});
		}

		const categoriesById = new Map(
			(state.budgets.rawCategories || []).map((category) => [
				category.category_id,
				category,
			]),
		);
		const currentGroupCategoryIds = new Set(
			(state.budgets.rawCategories || [])
				.filter((category) => category.group_id === targetGroupId)
				.map((category) => category.category_id),
		);

		const toAdd = selectedCategoryIds.filter(
			(categoryId) => !currentGroupCategoryIds.has(categoryId),
		);
		const toRemove = Array.from(currentGroupCategoryIds).filter(
			(categoryId) => !selectedCategoryIds.includes(categoryId),
		);

		const updates = [];
		toAdd.forEach((categoryId) => {
			const category = categoriesById.get(categoryId);
			if (!category) {
				updates.push(
					Promise.reject(
						new Error(`Category ${categoryId} is no longer available to assign.`),
					),
				);
				return;
			}
			updates.push(
				api.budgets.updateCategory(
					categoryId,
					buildCategoryUpdatePayload(category, targetGroupId),
				),
			);
		});

		toRemove.forEach((categoryId) => {
			const category = categoriesById.get(categoryId);
			if (!category) {
				updates.push(
					Promise.reject(
						new Error(`Category ${categoryId} is no longer available to move.`),
					),
				);
				return;
			}
			updates.push(
				api.budgets.updateCategory(
					categoryId,
					buildCategoryUpdatePayload(category, null),
				),
			);
		});

		if (updates.length > 0) {
			await Promise.all(updates);
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
		if (
			store.getState().pendingCategoryEdit ||
			categorySlugDirty ||
			!slugInput
		) {
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
			formEl.querySelector("[data-goal-section='target_date']").style.display =
				radio.value === "target_date" ? "block" : "none";
			formEl.querySelector("[data-goal-section='recurring']").style.display =
				radio.value === "recurring" ? "block" : "none";
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
	const uncategorizedSelect = document.querySelector(selectors.groupUncategorizedSelect);
	uncategorizedSelect?.addEventListener("change", () => {
		refreshSelectOptionIndicators(uncategorizedSelect);
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

	const reorderButton = document.querySelector(selectors.budgetsReorderButton);
	reorderButton?.addEventListener("click", () => enterGroupReorderMode());
	const reorderSaveButton = document.querySelector(selectors.budgetsReorderSave);
	reorderSaveButton?.addEventListener("click", () => persistGroupReorder());
	const reorderCancelButton = document.querySelector(selectors.budgetsReorderCancel);
	reorderCancelButton?.addEventListener("click", () => cancelGroupReorder());
	updateReorderControls();

	initBudgetDetailModal();
	initGroupDetailModal();
	initCategoryModal();
	initGroupModal();
};
