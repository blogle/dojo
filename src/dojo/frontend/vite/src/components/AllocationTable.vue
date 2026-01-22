<template>
  <div class="ledger-card ledger-card--allocations allocation-table-card">
    <table class="ledger-table ledger-table--allocations">
      <thead>
        <tr>
          <th>Date</th>
          <th class="ledger-table__amount">Amount</th>
          <th>From</th>
          <th>To</th>
          <th>Memo</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="allocations-body">
        <tr v-if="isLoading">
          <td colspan="6" class="u-muted">Loading allocations…</td>
        </tr>
        <tr v-else-if="!allocationsList.length">
          <td colspan="6" class="u-muted">No allocations recorded for this month.</td>
        </tr>
        <tr
          v-else
          v-for="alloc in allocationsList"
          :key="alloc.concept_id"
          :class="{ 'is-editing': editingId === alloc.concept_id }"
          @click="startEditing(alloc)"
        >
          <template v-if="editingId === alloc.concept_id">
            <td>
              <input
                type="date"
                v-model="editForm.allocation_date"
                @keydown.enter.prevent="saveEdit"
                @keydown.esc.prevent="cancelEdit"
              />
            </td>
            <td class="amount-cell">
              <input
                type="number"
                step="0.01"
                v-model="editForm.amount"
                @keydown.enter.prevent="saveEdit"
                @keydown.esc.prevent="cancelEdit"
              />
            </td>
            <td>{{ getCategoryName(alloc.from_category_id) }}</td>
            <td>
              <select
                v-model="editForm.to_category_id"
                @keydown.enter.prevent="saveEdit"
                @keydown.esc.prevent="cancelEdit"
              >
                <option value="" disabled>Select category</option>
                <option v-for="cat in allocationCategories" :key="cat.category_id" :value="cat.category_id">
                  {{ cat.name }}
                </option>
              </select>
            </td>
            <td>
              <input
                type="text"
                v-model="editForm.memo"
                @keydown.enter.prevent="saveEdit"
                @keydown.esc.prevent="cancelEdit"
              />
            </td>
            <td>
              <button
                type="button"
                class="action-button"
                title="Delete allocation"
                @click.stop="deleteAllocation(alloc.concept_id)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </td>
          </template>
          <template v-else>
            <td>{{ alloc.allocation_date || '—' }}</td>
            <td class="amount-cell">{{ formatAmountDisplay(alloc.amount_minor) }}</td>
            <td>{{ getCategoryName(alloc.from_category_id) }}</td>
            <td>{{ getCategoryName(alloc.to_category_id) }}</td>
            <td>{{ alloc.memo || '—' }}</td>
            <td></td>
          </template>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useMutation } from "@tanstack/vue-query";
import { api } from "../services/api.js";
import {
	dollarsToMinor,
	minorToDollars,
	formatAmount,
} from "../services/format.js";

const props = defineProps({
	allocations: { type: Array, default: () => [] },
	allocationCategories: { type: Array, default: () => [] },
	isLoading: { type: Boolean, default: false },
	refreshBudgetData: { type: Function, required: true },
});

const allocationsList = computed(() => props.allocations ?? []);

const editingId = ref(null);
const editForm = reactive({
	concept_id: null,
	allocation_date: "",
	to_category_id: "",
	amount: "",
	memo: "",
});

const updateAllocationMutation = useMutation({
	mutationFn: ({ id, payload }) => api.budgets.updateAllocation(id, payload),
	onSuccess: () => {
		props.refreshBudgetData();
	},
});

const deleteAllocationMutation = useMutation({
	mutationFn: (id) => api.budgets.deleteAllocation(id),
	onSuccess: () => {
		props.refreshBudgetData();
	},
});

const formatAmountDisplay = (minor) => formatAmount(minor);

const getCategoryName = (id) => {
	if (!id) return "—";
	const cat = props.allocationCategories.find((c) => c.category_id === id);
	return cat ? cat.name : id;
};

const startEditing = (alloc) => {
	if (editingId.value === alloc.concept_id) return;
	editingId.value = alloc.concept_id;
	editForm.concept_id = alloc.concept_id;
	editForm.allocation_date = alloc.allocation_date;
	editForm.to_category_id = alloc.to_category_id;
	editForm.amount = minorToDollars(alloc.amount_minor);
	editForm.memo = alloc.memo || "";
};

const cancelEdit = () => {
	editingId.value = null;
};

const saveEdit = async () => {
	if (!editingId.value) return;
	try {
		await updateAllocationMutation.mutateAsync({
			id: editForm.concept_id,
			payload: {
				allocation_date: editForm.allocation_date,
				to_category_id: editForm.to_category_id,
				amount_minor: Math.abs(dollarsToMinor(editForm.amount)),
				memo: editForm.memo,
			},
		});
		editingId.value = null;
	} catch (e) {
		alert(e.message || "Failed to update allocation");
	}
};

const deleteAllocation = async (id) => {
	try {
		await deleteAllocationMutation.mutateAsync(id);
		editingId.value = null;
	} catch (e) {
		alert(e.message || "Failed to delete allocation");
	}
};

watch(
	() => props.allocations,
	(allocations) => {
		if (!allocations) return;
		const present = new Set(allocations.map((alloc) => alloc.concept_id));
		if (editingId.value && !present.has(editingId.value)) {
			editingId.value = null;
		}
	},
	{ immediate: true },
);
</script>

<style scoped>
.allocation-table-card {
  margin-top: 2rem;
}
</style>
