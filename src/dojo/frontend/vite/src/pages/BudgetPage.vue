<template>
  <section class="route-page route-page--active budgets-page" id="budgets-page" data-route="budgets">
    <header class="budgets-page__header">
      <div>
        <p class="page-label">Budgets</p>
        <p class="u-muted u-small-note">Allocate Ready-to-Assign into envelopes.</p>
      </div>
      <div class="budgets-page__actions">
        <button type="button" class="button button--secondary" data-testid="open-allocation-modal" @click="openAllocationModal()">Allocate funds</button>
        <button type="button" class="button button--secondary" data-testid="create-group-btn" @click="openGroupModal()">+ Add group</button>
        <button type="button" class="button button--primary" data-testid="add-budget-button" @click="openCategoryModal()">+ Add budget</button>
      </div>
    </header>

    <div class="budgets-summary" role="region" aria-label="Budget summary">
      <article class="summary-chip">
        <span class="summary-chip__label">Ready to assign</span>
        <strong id="budgets-ready-value">{{ formatAmount(readyToAssign) }}</strong>
      </article>
      <article class="summary-chip">
        <span class="summary-chip__label">Activity this month</span>
        <strong id="budgets-activity-value">{{ formatAmount(activityMinor) }}</strong>
      </article>
      <article class="summary-chip summary-chip--warning">
        <span class="summary-chip__label">Available this month</span>
        <strong id="budgets-available-value">{{ formatAmount(availableMinor) }}</strong>
      </article>
      <article class="summary-chip summary-chip--muted">
        <span class="summary-chip__label">Budget month</span>
        <strong id="budgets-month-label">{{ monthLabel }}</strong>
      </article>
    </div>

    <div class="budgets-page__reorder budgets-page__reorder--inline" :class="{ 'is-editing': isReorderMode }">
      <button type="button" class="button button--tertiary" data-budgets-reorder data-testid="reorder-groups-btn" :disabled="isReorderMode" @click="enterReorderMode">Reorder</button>
      <div class="budgets-page__reorder-editing" aria-live="polite">
        <button type="button" class="button button--tertiary" data-budgets-reorder-save data-testid="save-group-order-btn" @click="saveReorder" :disabled="!isReorderMode">Save</button>
        <button type="button" class="button button--tertiary" data-budgets-reorder-cancel @click="cancelReorder" :disabled="!isReorderMode">Cancel</button>
      </div>
    </div>

    <div class="ledger-card ledger-card--budgets">
      <table class="ledger-table ledger-table--budgets">
        <thead>
          <tr>
            <th>Category</th>
            <th class="ledger-table__amount">Budgeted</th>
            <th class="ledger-table__amount">Activity</th>
            <th class="ledger-table__amount">Available</th>
          </tr>
        </thead>
        <tbody id="budgets-body">
          <tr v-if="isLoading"><td colspan="4" class="u-muted">Loading budgets…</td></tr>
          <template v-else>
             <template v-for="group in displayedGroups" :key="group.group_id">
                <tr
                  class="group-row"
                  :class="{ 'is-draggable': isReorderMode }"
                  :style="{ cursor: isReorderMode ? 'grab' : 'pointer' }"
                  :data-group-id="group.group_id"
                  data-testid="budget-group-row"
                  :draggable="isReorderMode && group.group_id !== 'uncategorized'"
                  @dragstart="handleDragStart($event, group)"
                  @dragover="handleDragOver($event)"
                  @drop="handleDrop($event, group)"
                  @dragend="handleDragEnd"
                  @click="!isReorderMode && openGroupDetailModal(group)"
                >
                  <td colspan="4" class="group-cell">
                     <div class="group-cell__content">
                        <span v-if="isReorderMode && group.group_id !== 'uncategorized'" class="group-row__drag-handle" aria-label="Drag to reorder" v-html="dragHandleIcon"></span>
                        <span class="group-cell__label">{{ group.name }}</span>
                        <button
                          type="button"
                          class="group-toggle"
                          @click.stop="toggleGroup(group.group_id)"
                        >
                           <span class="group-toggle__icon" aria-hidden="true">{{ isCollapsed(group.group_id) ? '▸' : '▾' }}</span>
                        </button>
                     </div>
                  </td>
                </tr>
                <template v-if="!isCollapsed(group.group_id)">
                  <tr
                    v-for="cat in group.items"
                    :key="cat.category_id"
                    :data-category-id="cat.category_id"
                    data-testid="budget-category-row"
                    :style="{ cursor: isReorderMode ? 'default' : 'pointer' }"
                    @click="!isReorderMode && openBudgetDetailModal(cat)"
                  >
                    <td data-testid="budget-col-name">
                      <div class="category-row">
                        <div>
                          <span>{{ cat.name }}</span>
                          <div v-if="cat.goal_text" class="u-muted u-small-note">{{ cat.goal_text }}</div>
                        </div>
                      </div>
                    </td>
                    <td class="amount-cell" data-testid="budget-col-budgeted">{{ formatAmount(cat.allocated_minor) }}</td>
                    <td class="amount-cell" data-testid="budget-col-activity">{{ formatAmount(cat.activity_minor) }}</td>
                    <td class="amount-cell" data-testid="budget-col-available">
                       <span :class="{ 'form-error': cat.available_minor < 0 }">{{ formatAmount(cat.available_minor) }}</span>
                    </td>
                  </tr>
                </template>
             </template>
          </template>
        </tbody>
      </table>
    </div>
        
    <div class="budgets-summary" role="region" aria-label="Allocation summary">
      <article class="summary-chip">
        <span class="summary-chip__label">Cash inflow this month</span>
        <strong id="allocations-inflow-value">{{ isLoadingAllocations ? "—" : formatAmount(inflowMinor) }}</strong>
      </article>
      <article class="summary-chip">
        <span class="summary-chip__label">Ready to assign (allocations)</span>
        <strong id="allocations-ready-value">{{ isLoadingAllocations ? "—" : formatAmount(readyToAssignMinor) }}</strong>
      </article>
    </div>

    <AllocationTable
      :allocations="allocations"
      :allocationCategories="allocationCategories"
      :isLoading="isLoadingAllocations"
      :refreshBudgetData="invalidateAll"
    />

    <!-- Modals -->
    <!-- Category Modal -->
    <div v-if="categoryModalOpen" class="modal-overlay is-visible" id="category-modal" style="display: flex;" @click.self="closeCategoryModal">
      <div class="modal">
        <header class="modal__header">
          <div>
            <p class="stat-card__label">Budget category</p>
            <h2 data-category-modal-title>{{ categoryForm.isEditing ? 'Rename category' : 'Add category' }}</h2>
            <p class="u-muted u-small-note" data-category-modal-hint>{{ categoryForm.isEditing ? 'Slug edits require migrations, so only the name is editable.' : 'Create a new envelope slug for allocations.' }}</p>
          </div>
          <button class="modal__close" type="button" @click="closeCategoryModal">×</button>
        </header>
        <form class="modal-form" @submit.prevent="submitCategoryForm">
          <label>
            Display name
            <input type="text" v-model="categoryForm.name" required data-testid="category-name-input" />
          </label>
          <label>
            Group
            <select v-model="categoryForm.group_id" data-testid="category-group-select">
              <option value="">Uncategorized</option>
              <option v-for="g in groups" :key="g.group_id" :value="g.group_id">{{ g.name }}</option>
            </select>
          </label>

          <div class="segmented-control" role="group" aria-label="Goal type">
             <span class="segmented-control__label">Goal</span>
             <label class="segmented-control__option">
               <input type="radio" value="recurring" v-model="categoryForm.goal_type" data-testid="goal-type-recurring">
               <span>Recurring</span>
             </label>
             <label class="segmented-control__option">
               <input type="radio" value="target_date" v-model="categoryForm.goal_type" data-testid="goal-type-target-date">
               <span>Target Date</span>
             </label>
          </div>

          <div v-if="categoryForm.goal_type === 'target_date'">
             <div class="form-panel__grid form-panel__grid--compact">
                <label class="form-panel__field">
                   <span>Target Date</span>
                   <input type="date" v-model="categoryForm.target_date_dt" data-testid="target-date-input">
                </label>
                <label class="form-panel__field form-panel__field--amount">
                   <span>Target Amount</span>
                   <input type="number" step="0.01" placeholder="0.00" v-model="categoryForm.target_amount" data-testid="target-amount-input">
                </label>
             </div>
          </div>
          <div v-else>
             <div class="form-panel__grid form-panel__grid--compact">
                <label class="form-panel__field">
                   <span>Frequency</span>
                   <select v-model="categoryForm.frequency" data-testid="frequency-select">
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="yearly">Yearly</option>
                   </select>
                </label>
                <label class="form-panel__field">
                   <span>Next Due Date</span>
                   <input type="date" v-model="categoryForm.recurring_date_dt" data-testid="recurring-date-input">
                </label>
                <label class="form-panel__field form-panel__field--amount">
                   <span>Amount</span>
                   <input type="number" step="0.01" placeholder="0.00" v-model="categoryForm.recurring_amount" data-testid="recurring-amount-input">
                </label>
             </div>
          </div>
          <p v-if="categoryFormError" class="form-panel__error" aria-live="polite">{{ categoryFormError }}</p>
          <div class="form-panel__actions">
             <button type="submit" class="button button--primary" data-testid="save-category-btn" :disabled="isSubmittingCategory">{{ isSubmittingCategory ? 'Saving...' : 'Save budget' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Group Modal -->
    <div v-if="groupModalOpen" class="modal-overlay is-visible" id="group-modal" style="display: flex;" @click.self="closeGroupModal">
       <div class="modal">
          <header class="modal__header">
             <div>
                <p class="stat-card__label">Category group</p>
                <h2 data-group-modal-title>{{ groupForm.isEditing ? 'Edit group' : 'Add group' }}</h2>
             </div>
             <button class="modal__close" type="button" @click="closeGroupModal">×</button>
          </header>
          <form class="modal-form" @submit.prevent="submitGroupForm">
             <label>
                Group Name
                <input type="text" v-model="groupForm.name" required data-testid="group-name-input">
             </label>
             <label>
                Assign uncategorized budgets
                <select multiple size="6" v-model="groupForm.selectedUncategorized" data-testid="uncategorized-category-select">
                   <option v-if="!uncategorizedAndGroupCategories.length" value="" disabled>No uncategorized budgets</option>
                   <option v-for="cat in uncategorizedAndGroupCategories" :key="cat.category_id" :value="cat.category_id">
                      {{ (groupForm.selectedUncategorized.includes(cat.category_id) ? '[x] ' : '[ ] ') + cat.name }}
                   </option>
                </select>
                <p class="form-panel__helper">Toggle budgets to include them in this group.</p>
             </label>
             <p v-if="groupFormError" class="form-panel__error">{{ groupFormError }}</p>
             <div class="form-panel__actions">
                <button type="submit" class="button button--primary" data-testid="save-group-btn" :disabled="isSubmittingGroup">{{ isSubmittingGroup ? 'Saving...' : 'Save group' }}</button>
             </div>
          </form>
       </div>
    </div>

    <!-- Budget Detail Modal -->
    <div v-if="budgetDetailModalOpen && activeBudgetDetail" class="modal-overlay is-visible" id="budget-detail-modal" style="display: flex;" @click.self="closeBudgetDetailModal">
       <div class="modal">
          <header class="modal__header">
             <div>
                <p class="stat-card__label">Budget detail</p>
                <h2>{{ activeBudgetDetail.name }}</h2>
             </div>
             <button class="modal__close" type="button" @click="closeBudgetDetailModal">×</button>
          </header>
          <div class="modal__body">
             <div class="budget-detail-summary">
                <table class="ledger-table">
                   <tbody>
                      <tr><td>Left over from last month</td><td class="ledger-table__amount">{{ formatAmount(activeBudgetDetail.available_minor - activeBudgetDetail.allocated_minor - activeBudgetDetail.activity_minor) }}</td></tr>
                      <tr><td>Budgeted this month</td><td class="ledger-table__amount">{{ formatAmount(activeBudgetDetail.allocated_minor) }}</td></tr>
                      <tr><td>Activity</td><td class="ledger-table__amount">{{ formatAmount(activeBudgetDetail.activity_minor) }}</td></tr>
                      <tr><td>Available</td><td class="ledger-table__amount">{{ formatAmount(activeBudgetDetail.available_minor) }}</td></tr>
                   </tbody>
                </table>
             </div>
             <div class="quick-allocations">
                <p class="stat-card__label">Quick allocations</p>
                <div class="quick-allocations__actions">
                   <p v-if="!budgetQuickActions.length" class="u-muted u-small-note">No quick allocations available.</p>
                   <button v-for="action in budgetQuickActions" :key="action.label" type="button" class="secondary" @click="handleQuickAllocation(activeBudgetDetail.category_id, action.amount, action.label)">
                      {{ action.label }}: {{ formatAmount(action.amount) }}
                   </button>
                </div>
             </div>
             <div class="form-panel__actions form-panel__actions--split">
                <button type="button" class="button button--secondary" @click="editCategoryFromDetail">Edit settings</button>
             </div>
          </div>
       </div>
    </div>

    <!-- Group Detail Modal -->
     <div v-if="groupDetailModalOpen && activeGroupDetail" class="modal-overlay is-visible" id="group-detail-modal" style="display: flex;" @click.self="closeGroupDetailModal">
        <div class="modal">
           <header class="modal__header">
              <div>
                 <p class="stat-card__label">Group detail</p>
                 <h2>{{ activeGroupDetail.name }}</h2>
              </div>
              <button class="modal__close" type="button" @click="closeGroupDetailModal">×</button>
           </header>
           <div class="modal__body">
              <div class="budget-detail-summary">
                 <table class="ledger-table">
                    <tbody>
                       <tr><td>Left over from last month</td><td class="ledger-table__amount">{{ formatAmount(groupDetailStats.leftover) }}</td></tr>
                       <tr><td>Budgeted this month</td><td class="ledger-table__amount">{{ formatAmount(groupDetailStats.budgeted) }}</td></tr>
                       <tr><td>Activity</td><td class="ledger-table__amount">{{ formatAmount(groupDetailStats.activity) }}</td></tr>
                       <tr><td>Available</td><td class="ledger-table__amount">{{ formatAmount(groupDetailStats.available) }}</td></tr>
                    </tbody>
                 </table>
              </div>
              <div class="quick-allocations">
                 <p class="stat-card__label">Quick allocations</p>
                 <div class="quick-allocations__actions">
                     <p v-if="!groupQuickActions.length" class="u-muted u-small-note">No quick allocations available.</p>
                     <button v-for="action in groupQuickActions" :key="action.label" type="button" class="secondary" @click="handleGroupQuickAllocation(action.allocations, action.label)">
                       {{ action.label }}: {{ formatAmount(action.total) }}
                    </button>
                 </div>
              </div>
              <div class="form-panel__actions form-panel__actions--split">
                 <button type="button" class="button button--secondary" @click="editGroupFromDetail">Edit group</button>
              </div>
           </div>
        </div>
     </div>

    <AllocationModal
      :open="allocationModalOpen"
      :allocationCategories="allocationCategories"
      :readyToAssignMinor="readyToAssignMinor"
      :refreshBudgetData="invalidateAll"
      @close="closeAllocationModal"
    />


  </section>
 </template>


<script setup>
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, reactive, ref, watch } from "vue";
import { filterUserFacingCategories } from "../utils/categories.js";
import { api } from "../services/api.js";
import AllocationModal from "../components/AllocationModal.vue";
import AllocationTable from "../components/AllocationTable.vue";
import {
	currentMonthStartISO,
	dollarsToMinor,
	formatAmount,
	minorToDollars,
	todayISO,
} from "../services/format.js";

const queryClient = useQueryClient();
const monthStart = currentMonthStartISO();

const collapsedGroups = reactive({});
const isReorderMode = ref(false);
const reorderDraft = ref([]);
const dragHandleIcon = `<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M8 1.5 10 3.5 9.2 4.3 8 3.1 6.8 4.3 6 3.5Z" /><path d="M8 14.5 6 12.5 6.8 11.7 8 12.9 9.2 11.7 10 12.5Z" /><path d="M4.25 6.25h7.5v1h-7.5zM4.25 8.75h7.5v1h-7.5zM4.25 11.25h7.5v1h-7.5z" /></svg>`;

// Queries
const categoriesQuery = useQuery({
	queryKey: ["budget-categories", monthStart],
	queryFn: () => api.budgets.categories(monthStart),
});

const allocationsQuery = useQuery({
	queryKey: ["allocations", monthStart],
	queryFn: () => api.budgets.allocations(monthStart),
});

const groupsQuery = useQuery({
	queryKey: ["budget-category-groups"],
	queryFn: api.budgets.groups,
});

const readyToAssignQuery = useQuery({
	queryKey: ["ready-to-assign", monthStart],
	queryFn: () => api.readyToAssign.current(monthStart),
});

const isLoading = computed(
	() => categoriesQuery.isPending.value || groupsQuery.isPending.value,
);

const isLoadingAllocations = computed(
	() => allocationsQuery.isPending.value || allocationsQuery.isFetching.value,
);

const allocations = computed(
	() => allocationsQuery.data.value?.allocations ?? [],
);

const inflowMinor = computed(
	() => allocationsQuery.data.value?.inflow_minor ?? 0,
);

const readyToAssignMinor = computed(
	() => allocationsQuery.data.value?.ready_to_assign_minor ?? 0,
);

// Computed Data
const categories = computed(() => {
	const raw = categoriesQuery.data.value || [];
	const normalized = raw.map((c) => ({
		...c,
		available_minor: c.available_minor ?? 0,
		activity_minor: c.activity_minor ?? 0,
		allocated_minor: c.allocated_minor ?? 0,
	}));
	return filterUserFacingCategories(normalized).map((c) => {
		let goalText = "";
		if (c.goal_type === "target_date" && c.goal_amount_minor) {
			goalText = `Goal: ${formatAmount(c.goal_amount_minor)} by ${c.goal_target_date || "?"}`;
		} else if (c.goal_type === "recurring" && c.goal_amount_minor) {
			const freq = c.goal_frequency
				? c.goal_frequency.charAt(0).toUpperCase() + c.goal_frequency.slice(1)
				: "Recurring";
			goalText = `${freq}: ${formatAmount(c.goal_amount_minor)}`;
		}
		return { ...c, goal_text: goalText };
	});
});

const allocationCategories = computed(() =>
	[...categories.value].sort((a, b) => a.name.localeCompare(b.name)),
);

const groups = computed(() =>
	[...(groupsQuery.data.value || [])].sort(
		(a, b) => a.sort_order - b.sort_order,
	),
);

const displayedGroups = computed(() => {
	const baseGroups =
		isReorderMode.value && reorderDraft.value.length
			? reorderDraft.value
			: groups.value;
	const grouped = {};
	baseGroups.forEach((g) => {
		grouped[g.group_id] = { ...g, items: [] };
	});
	grouped.uncategorized = {
		group_id: "uncategorized",
		name: "Uncategorized",
		items: [],
	};

	categories.value.forEach((cat) => {
		const gid = cat.group_id || "uncategorized";
		if (grouped[gid]) {
			grouped[gid].items.push(cat);
		} else {
			grouped.uncategorized.items.push(cat);
		}
	});

	// Convert back to array respecting sort order
	const result = baseGroups.map((g) => grouped[g.group_id]);
	if (grouped.uncategorized.items.length > 0) {
		result.push(grouped.uncategorized);
	}
	return result;
});

const readyToAssign = computed(
	() => readyToAssignQuery.data.value?.ready_to_assign_minor ?? 0,
);
const activityMinor = computed(() =>
	categories.value.reduce((sum, c) => sum + c.activity_minor, 0),
);
const availableMinor = computed(() =>
	categories.value.reduce((sum, c) => sum + c.available_minor, 0),
);
const monthLabel = computed(() =>
	new Date(`${monthStart}T00:00:00`).toLocaleDateString(undefined, {
		year: "numeric",
		month: "long",
	}),
);

// Helper
const toggleGroup = (groupId) => {
	collapsedGroups[groupId] = !collapsedGroups[groupId];
};
const isCollapsed = (groupId) => !!collapsedGroups[groupId];

// Reorder Logic
const enterReorderMode = () => {
	reorderDraft.value = [...groups.value];
	isReorderMode.value = true;
};
const cancelReorder = () => {
	isReorderMode.value = false;
	reorderDraft.value = [];
};

let draggedItem = null;
const handleDragStart = (e, group) => {
	draggedItem = group;
	e.dataTransfer.effectAllowed = "move";
};
const handleDragOver = (e) => {
	e.preventDefault();
	e.dataTransfer.dropEffect = "move";
};
const handleDrop = (_e, targetGroup) => {
	if (!draggedItem || draggedItem === targetGroup) return;
	const fromIndex = reorderDraft.value.findIndex(
		(g) => g.group_id === draggedItem.group_id,
	);
	const toIndex = reorderDraft.value.findIndex(
		(g) => g.group_id === targetGroup.group_id,
	);
	if (fromIndex !== -1 && toIndex !== -1) {
		const item = reorderDraft.value.splice(fromIndex, 1)[0];
		reorderDraft.value.splice(toIndex, 0, item);
	}
	draggedItem = null;
};
const handleDragEnd = () => {
	draggedItem = null;
};

const updateGroupMutation = useMutation({
	mutationFn: ({ groupId, payload }) =>
		api.budgets.updateGroup(groupId, payload),
	onSuccess: () => {
		queryClient.invalidateQueries({ queryKey: ["budget-category-groups"] });
	},
});

const saveReorder = async () => {
	try {
		const updates = reorderDraft.value.map((group, index) =>
			api.budgets.updateGroup(group.group_id, {
				name: group.name,
				sort_order: index + 1,
				is_active: group.is_active !== false,
			}),
		);
		await Promise.all(updates);
		queryClient.invalidateQueries({ queryKey: ["budget-category-groups"] });
		isReorderMode.value = false;
	} catch (e) {
		alert(e.message || "Failed to save order");
	}
};

// --- Category Modal Logic ---
const categoryModalOpen = ref(false);
const categoryForm = reactive({
	isEditing: false,
	category_id: null,
	name: "",
	group_id: "",
	goal_type: "recurring",
	target_date_dt: "",
	target_amount: "",
	frequency: "monthly",
	recurring_date_dt: "",
	recurring_amount: "",
});
const categoryFormError = ref("");
const createCategoryMutation = useMutation({
	mutationFn: api.budgets.createCategory,
	onSuccess: () => invalidateAll(),
});
const updateCategoryMutation = useMutation({
	mutationFn: ({ id, payload }) => api.budgets.updateCategory(id, payload),
	onSuccess: () => invalidateAll(),
});
const isSubmittingCategory = computed(
	() =>
		createCategoryMutation.isPending.value ||
		updateCategoryMutation.isPending.value,
);

const firstOfNextMonthISO = () => {
	const today = new Date();
	const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, 1);
	const m = `${nextMonth.getMonth() + 1}`.padStart(2, "0");
	const d = `${nextMonth.getDate()}`.padStart(2, "0");
	return `${nextMonth.getFullYear()}-${m}-${d}`;
};

const openCategoryModal = (cat = null) => {
	categoryFormError.value = "";
	if (cat) {
		categoryForm.isEditing = true;
		categoryForm.category_id = cat.category_id;
		categoryForm.name = cat.name;
		categoryForm.group_id = cat.group_id || "";
		categoryForm.goal_type = cat.goal_type || "recurring";
		categoryForm.target_date_dt = cat.goal_target_date || "";
		categoryForm.target_amount = cat.goal_amount_minor
			? minorToDollars(cat.goal_amount_minor)
			: "";
		categoryForm.frequency = cat.goal_frequency || "monthly";
		categoryForm.recurring_date_dt = cat.goal_target_date || "";
		categoryForm.recurring_amount = cat.goal_amount_minor
			? minorToDollars(cat.goal_amount_minor)
			: "";
		if (cat.goal_type === "target_date") {
			categoryForm.recurring_date_dt = firstOfNextMonthISO();
		} else {
			categoryForm.target_date_dt = "";
		}
	} else {
		categoryForm.isEditing = false;
		categoryForm.category_id = null;
		categoryForm.name = "";
		categoryForm.group_id = "";
		categoryForm.goal_type = "recurring";
		categoryForm.target_date_dt = "";
		categoryForm.target_amount = "";
		categoryForm.frequency = "monthly";
		categoryForm.recurring_date_dt = firstOfNextMonthISO();
		categoryForm.recurring_amount = "";
	}
	categoryModalOpen.value = true;
};
const closeCategoryModal = () => {
	categoryModalOpen.value = false;
};

const submitCategoryForm = async () => {
	const goalAmount =
		categoryForm.goal_type === "target_date"
			? categoryForm.target_amount
			: categoryForm.recurring_amount;
	const goalDate =
		categoryForm.goal_type === "target_date"
			? categoryForm.target_date_dt
			: categoryForm.recurring_date_dt;

	const payload = {
		name: categoryForm.name,
		is_active: true,
		group_id: categoryForm.group_id || null,
		goal_type: categoryForm.goal_type,
		goal_amount_minor: dollarsToMinor(goalAmount),
		goal_target_date: goalDate || null,
		goal_frequency:
			categoryForm.goal_type === "recurring" ? categoryForm.frequency : null,
	};

	try {
		if (categoryForm.isEditing) {
			await updateCategoryMutation.mutateAsync({
				id: categoryForm.category_id,
				payload,
			});
		} else {
			// Slug is auto-generated by backend if not provided? Legacy code allows editing slug on create, but here I'm skipping it for simplicity as backend generates it from name usually.
			// Actually legacy code `slugifyCategoryName` implies frontend generates it if user types, but let's see.
			// The legacy code sends `category_id` (slug) on create.
			// I'll assume backend handles it or I need to slugify.
			const slug =
				categoryForm.name
					.toLowerCase()
					.replace(/[^a-z0-9]+/g, "_")
					.replace(/^_+|_+$/g, "") || "category";
			await createCategoryMutation.mutateAsync({
				...payload,
				category_id: slug,
			});
		}
		closeCategoryModal();
	} catch (e) {
		categoryFormError.value = e.message || "Failed to save";
	}
};

// --- Group Modal Logic ---
const groupModalOpen = ref(false);
const groupForm = reactive({
	isEditing: false,
	group_id: null,
	name: "",
	selectedUncategorized: [],
});
const groupFormError = ref("");
const createGroupMutation = useMutation({
	mutationFn: api.budgets.createGroup,
	onSuccess: () => invalidateAll(),
});
const isSubmittingGroup = computed(
	() =>
		createGroupMutation.isPending.value || updateGroupMutation.isPending.value,
);

const uncategorizedAndGroupCategories = computed(() => {
	if (!groupForm.group_id && !groupModalOpen.value) return [];
	// Show uncategorized + categories currently in this group
	return categories.value
		.filter((c) => !c.group_id || c.group_id === groupForm.group_id)
		.sort((a, b) => a.name.localeCompare(b.name));
});

const openGroupModal = (group = null) => {
	groupFormError.value = "";
	if (group) {
		groupForm.isEditing = true;
		groupForm.group_id = group.group_id;
		groupForm.name = group.name;
		// Pre-select categories in this group
		groupForm.selectedUncategorized = categories.value
			.filter((c) => c.group_id === group.group_id)
			.map((c) => c.category_id);
	} else {
		groupForm.isEditing = false;
		groupForm.group_id = null;
		groupForm.name = "";
		groupForm.selectedUncategorized = [];
	}
	groupModalOpen.value = true;
};
const closeGroupModal = () => {
	groupModalOpen.value = false;
};

const submitGroupForm = async () => {
	try {
		const slug =
			groupForm.name
				.toLowerCase()
				.replace(/[^a-z0-9]+/g, "_")
				.replace(/^_+|_+$/g, "") || "group";
		const groupId = groupForm.isEditing ? groupForm.group_id : slug;

		if (groupForm.isEditing) {
			// sort_order is preserved in updateGroup if not passed? No, legacy passes it.
			const original = groups.value.find((g) => g.group_id === groupId);
			await updateGroupMutation.mutateAsync({
				groupId,
				payload: {
					name: groupForm.name,
					is_active: true,
					sort_order: original?.sort_order ?? 0,
				},
			});
		} else {
			const maxOrder = Math.max(
				...groups.value.map((g) => g.sort_order || 0),
				0,
			);
			await createGroupMutation.mutateAsync({
				group_id: groupId,
				name: groupForm.name,
				sort_order: maxOrder + 1,
				is_active: true,
			});
		}

		// Handle category moves
		const selected = new Set(groupForm.selectedUncategorized);
		const currentGroupCats = categories.value.filter(
			(c) => c.group_id === groupId,
		);
		const updates = [];

		// Add to group
		for (const catId of selected) {
			const cat = categories.value.find((c) => c.category_id === catId);
			if (cat && cat.group_id !== groupId) {
				updates.push(
					api.budgets.updateCategory(catId, { ...cat, group_id: groupId }),
				);
			}
		}
		// Remove from group
		for (const cat of currentGroupCats) {
			if (!selected.has(cat.category_id)) {
				updates.push(
					api.budgets.updateCategory(cat.category_id, {
						...cat,
						group_id: null,
					}),
				);
			}
		}

		if (updates.length) await Promise.all(updates);
		invalidateAll();
		closeGroupModal();
	} catch (e) {
		groupFormError.value = e.message || "Failed to save group";
	}
};

// --- Detail Modals ---
const budgetDetailModalOpen = ref(false);
const activeBudgetDetail = ref(null);
const groupDetailModalOpen = ref(false);
const activeGroupDetail = ref(null);

const openBudgetDetailModal = (cat) => {
	activeBudgetDetail.value = cat;
	budgetDetailModalOpen.value = true;
};
const closeBudgetDetailModal = () => {
	budgetDetailModalOpen.value = false;
	activeBudgetDetail.value = null;
};

const openGroupDetailModal = (group) => {
	// Need to augment group with item details from categories list which might be updated
	const items = categories.value.filter((c) => c.group_id === group.group_id);
	activeGroupDetail.value = { ...group, items };
	groupDetailModalOpen.value = true;
};
const closeGroupDetailModal = () => {
	groupDetailModalOpen.value = false;
	activeGroupDetail.value = null;
};

const editCategoryFromDetail = () => {
	const cat = activeBudgetDetail.value;
	closeBudgetDetailModal();
	openCategoryModal(cat);
};

const editGroupFromDetail = () => {
	const group = groups.value.find(
		(g) => g.group_id === activeGroupDetail.value.group_id,
	);
	closeGroupDetailModal();
	openGroupModal(group);
};

const allocationModalOpen = ref(false);
const openAllocationModal = () => {
	allocationModalOpen.value = true;
};
const closeAllocationModal = () => {
	allocationModalOpen.value = false;
};

// Quick Allocations

const handleQuickAllocation = async (to_category_id, amount_minor, memo) => {
	if (readyToAssign.value < amount_minor) {
		alert("Not enough Ready to Assign funds.");
		return;
	}
	try {
		await api.budgets.createAllocation({
			to_category_id,
			amount_minor,
			allocation_date: todayISO(),
			memo,
		});
		invalidateAll();
		closeBudgetDetailModal();
	} catch (e) {
		alert(e.message || "Allocation failed");
	}
};

const handleGroupQuickAllocation = async (allocations, _label) => {
	const total = allocations.reduce((sum, a) => sum + a.amount_minor, 0);
	if (readyToAssign.value < total) {
		alert("Not enough Ready to Assign funds.");
		return;
	}
	try {
		await Promise.all(
			allocations.map((a) =>
				api.budgets.createAllocation({
					to_category_id: a.category_id,
					amount_minor: a.amount_minor,
					allocation_date: todayISO(),
					memo: a.memo,
				}),
			),
		);
		invalidateAll();
		closeGroupDetailModal();
	} catch (e) {
		alert(e.message || "Allocation failed");
	}
};

const budgetQuickActions = computed(() => {
	if (!activeBudgetDetail.value) return [];
	const cat = activeBudgetDetail.value;
	const actions = [];
	if (cat.goal_amount_minor > 0) {
		const needed = Math.max(0, cat.goal_amount_minor - cat.available_minor);
		if (needed > 0) actions.push({ label: "Fund Goal", amount: needed });
	}
	if (cat.last_month_allocated_minor > 0) {
		actions.push({
			label: "Budgeted Last Month",
			amount: cat.last_month_allocated_minor,
		});
	}
	const spentLast = Math.max(0, -1 * (cat.last_month_activity_minor || 0)); // Activity is signed? Yes. Outflow is negative.
	if (spentLast > 0) {
		actions.push({ label: "Spent Last Month", amount: spentLast });
	}
	return actions;
});

const groupDetailStats = computed(() => {
	if (!activeGroupDetail.value)
		return { leftover: 0, budgeted: 0, activity: 0, available: 0 };
	return activeGroupDetail.value.items.reduce(
		(acc, cat) => ({
			leftover:
				acc.leftover +
				(cat.available_minor - cat.allocated_minor - cat.activity_minor),
			budgeted: acc.budgeted + cat.allocated_minor,
			activity: acc.activity + cat.activity_minor,
			available: acc.available + cat.available_minor,
		}),
		{ leftover: 0, budgeted: 0, activity: 0, available: 0 },
	);
});

const groupQuickActions = computed(() => {
	if (!activeGroupDetail.value) return [];
	const items = activeGroupDetail.value.items;
	const actions = [];

	// Fund Underfunded
	const fundAllocations = items
		.filter(
			(cat) =>
				cat.goal_amount_minor > 0 &&
				cat.goal_amount_minor - cat.available_minor > 0,
		)
		.map((cat) => ({
			category_id: cat.category_id,
			amount_minor: cat.goal_amount_minor - cat.available_minor,
			memo: "Group Quick Allocation - Fund Goal",
		}));
	if (fundAllocations.length)
		actions.push({
			label: "Fund Underfunded",
			total: fundAllocations.reduce((s, a) => s + a.amount_minor, 0),
			allocations: fundAllocations,
		});

	// Budgeted Last Month
	const budgetedAllocations = items
		.filter((cat) => cat.last_month_allocated_minor > 0)
		.map((cat) => ({
			category_id: cat.category_id,
			amount_minor: cat.last_month_allocated_minor,
			memo: "Group Quick Allocation - Budgeted Last Month",
		}));
	if (budgetedAllocations.length)
		actions.push({
			label: "Budgeted Last Month",
			total: budgetedAllocations.reduce((s, a) => s + a.amount_minor, 0),
			allocations: budgetedAllocations,
		});

	// Spent Last Month
	const spentAllocations = items
		.filter((cat) => -1 * cat.last_month_activity_minor > 0)
		.map((cat) => ({
			category_id: cat.category_id,
			amount_minor: -1 * cat.last_month_activity_minor,
			memo: "Group Quick Allocation - Spent Last Month",
		}));
	if (spentAllocations.length)
		actions.push({
			label: "Spent Last Month",
			total: spentAllocations.reduce((s, a) => s + a.amount_minor, 0),
			allocations: spentAllocations,
		});

	return actions;
});

const invalidateAll = () => {
	queryClient.invalidateQueries({ queryKey: ["budget-categories"] });
	queryClient.invalidateQueries({ queryKey: ["budget-category-groups"] });
	queryClient.invalidateQueries({ queryKey: ["ready-to-assign"] });
	queryClient.invalidateQueries({ queryKey: ["allocations"] });
};
</script>
