<template>
  <section class="route-page route-page--active allocations-page" id="allocations-page" data-route="allocations">
    <header class="allocations-page__header">
      <div>
        <p class="page-label">Allocations</p>
        <p class="u-muted u-small-note">Move Ready-to-Assign between envelopes and track the ledger.</p>
      </div>
      <article class="summary-chip summary-chip--muted">
        <span class="summary-chip__label">Budget month</span>
        <strong id="allocations-month-label">{{ monthLabel }}</strong>
      </article>
    </header>
    <div class="allocations-page__summary">
      <article class="stat-card">
        <span class="stat-card__label">Inflow (this month)</span>
        <span id="allocations-inflow-value" class="stat-card__value">{{ formatAmount(inflowMinor) }}</span>
        <p class="u-muted u-small-note">Cash entering on-budget accounts this month.</p>
      </article>
      <article class="stat-card">
        <span class="stat-card__label">Available to budget</span>
        <span id="allocations-ready-value" class="stat-card__value">{{ formatAmount(readyToAssignMinor) }}</span>
        <p class="u-muted u-small-note">Matches Ready-to-Assign after allocations.</p>
      </article>
    </div>

    <section class="form-panel allocations-page__form">
      <form data-testid="allocation-form" @submit.prevent="submitAllocation">
        <div class="form-panel__grid form-panel__grid--compact">
          <label class="form-panel__field">
            <span>Date</span>
            <input type="date" name="allocation_date" required data-allocation-date v-model="form.allocation_date" />
          </label>
          <label class="form-panel__field">
            <span>From category</span>
            <select name="from_category_id" data-allocation-from v-model="form.from_category_id">
              <option value="">Ready to Assign</option>
              <option v-for="cat in categories" :key="cat.category_id" :value="cat.category_id">{{ cat.name }}</option>
            </select>
          </label>
          <label class="form-panel__field">
            <span>To category</span>
            <select name="to_category_id" required data-allocation-to v-model="form.to_category_id">
              <option value="" disabled>Select category</option>
              <option v-for="cat in categories" :key="cat.category_id" :value="cat.category_id">{{ cat.name }}</option>
            </select>
          </label>
          <label class="form-panel__field">
            <span>Memo</span>
            <input type="text" name="memo" placeholder="Optional note" v-model="form.memo" />
          </label>
          <label class="form-panel__field form-panel__field--amount">
            <span>Amount</span>
            <input type="number" name="amount" step="0.01" inputmode="decimal" placeholder="0.00" required v-model="form.amount" />
          </label>
        </div>
        <div class="form-panel__actions">
          <button type="submit" class="button button--primary" data-allocation-submit :disabled="isSubmitting">{{ isSubmitting ? 'Saving...' : 'Save allocation' }}</button>
        </div>
      </form>
      <p class="form-panel__error" data-testid="allocation-error" aria-live="polite">{{ formError }}</p>
    </section>

    <div class="ledger-card ledger-card--allocations">
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
          <tr v-if="isLoading"><td colspan="6" class="u-muted">Loading allocations…</td></tr>
          <tr v-else-if="!allocations.length"><td colspan="6" class="u-muted">No allocations recorded for this month.</td></tr>
          <tr
            v-for="alloc in allocations"
            :key="alloc.concept_id"
            :class="{ 'is-editing': editingId === alloc.concept_id }"
            @click="startEditing(alloc)"
          >
             <template v-if="editingId === alloc.concept_id">
                <td><input type="date" v-model="editForm.allocation_date" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit"></td>
                <td class="amount-cell"><input type="number" step="0.01" v-model="editForm.amount" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit"></td>
                <td>{{ getCategoryName(alloc.from_category_id) }}</td>
                <td>
                   <select v-model="editForm.to_category_id" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
                      <option v-for="cat in categories" :key="cat.category_id" :value="cat.category_id">{{ cat.name }}</option>
                   </select>
                </td>
                <td><input type="text" v-model="editForm.memo" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit"></td>
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
                <td class="amount-cell">{{ formatAmount(alloc.amount_minor) }}</td>
                <td>{{ getCategoryName(alloc.from_category_id) }}</td>
                <td>{{ getCategoryName(alloc.to_category_id) }}</td>
                <td>{{ alloc.memo || '—' }}</td>
                <td></td>
             </template>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, reactive, nextTick } from 'vue';
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query';
import { api } from '../../../static/services/api.js';
import { formatAmount, currentMonthStartISO, dollarsToMinor, minorToDollars, todayISO } from '../../../static/services/format.js';
import { filterUserFacingCategories } from '../../../static/components/categories/utils.js';

const queryClient = useQueryClient();
const monthStart = currentMonthStartISO();
const monthLabel = computed(() => new Date(`${monthStart}T00:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'long' }));

// Queries
const allocationsQuery = useQuery({
  queryKey: ['allocations', monthStart],
  queryFn: () => api.budgets.allocations(monthStart),
});

const referenceQuery = useQuery({
    queryKey: ['reference-data'],
    queryFn: api.reference.load
});

// Categories for select
const categories = computed(() => {
    const raw = referenceQuery.data.value?.categories || [];
    return filterUserFacingCategories(raw).sort((a, b) => a.name.localeCompare(b.name));
});

const isLoading = computed(() => allocationsQuery.isPending.value || allocationsQuery.isFetching.value);
const allocations = computed(() => allocationsQuery.data.value?.allocations ?? []);
const inflowMinor = computed(() => allocationsQuery.data.value?.inflow_minor ?? 0);
const readyToAssignMinor = computed(() => allocationsQuery.data.value?.ready_to_assign_minor ?? 0);

const getCategoryName = (id) => {
    if (!id) return 'Ready to Assign';
    const cat = categories.value.find(c => c.category_id === id);
    return cat ? cat.name : id;
};

// Form Logic
const form = reactive({
    allocation_date: todayISO(),
    from_category_id: '',
    to_category_id: '',
    memo: '',
    amount: ''
});
const formError = ref('');

const createAllocationMutation = useMutation({
    mutationFn: api.budgets.createAllocation,
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['allocations'] });
        queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
        queryClient.invalidateQueries({ queryKey: ['budget-categories'] }); // Update available amounts in budget page
    }
});

const isSubmitting = computed(() => createAllocationMutation.isPending.value);

const submitAllocation = async () => {
    formError.value = '';
    const amountMinor = Math.abs(dollarsToMinor(form.amount));
    if (!form.to_category_id) {
        formError.value = "Choose the destination category.";
        return;
    }
    if (form.from_category_id && form.from_category_id === form.to_category_id) {
        formError.value = "Source and destination categories must differ.";
        return;
    }
    if (amountMinor === 0) {
        formError.value = "Amount must be greater than zero.";
        return;
    }
    // TODO: Client-side validation for available funds? 
    // Legacy code does: if (fromCategoryId) getCategoryAvailableMinor... 
    // This requires budget-categories data which is not fetched here yet (only reference data).
    // I could fetch budget-categories or just let the backend fail/validate.
    // Given legacy code does it, maybe I should useQuery budget-categories too?
    // Let's rely on backend or simple check against RTA if from is empty.
    if (!form.from_category_id && readyToAssignMinor.value < amountMinor) {
         formError.value = "Ready-to-Assign is insufficient for this allocation.";
         return;
    }

    try {
        await createAllocationMutation.mutateAsync({
            allocation_date: form.allocation_date,
            to_category_id: form.to_category_id,
            from_category_id: form.from_category_id || null,
            amount_minor: amountMinor,
            memo: form.memo || null
        });
        form.amount = '';
        form.memo = '';
        // Date and cats stay? Legacy clears amount, keeps others? 
        // Legacy: amountInput.value = ""; amountInput.focus();
    } catch (e) {
        formError.value = e.message || "Allocation failed";
    }
};

// Inline Edit
const editingId = ref(null);
const editForm = reactive({
    concept_id: null,
    allocation_date: '',
    to_category_id: '',
    amount: '',
    memo: ''
});
const updateAllocationMutation = useMutation({
    mutationFn: ({ id, payload }) => api.budgets.updateAllocation(id, payload),
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['allocations'] });
        queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
        queryClient.invalidateQueries({ queryKey: ['budget-categories'] });
    }
});

const deleteAllocationMutation = useMutation({
    mutationFn: api.budgets.deleteAllocation,
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['allocations'] });
        queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
        queryClient.invalidateQueries({ queryKey: ['budget-categories'] });
    }
});

const deleteAllocation = async (id) => {
    try {
        await deleteAllocationMutation.mutateAsync(id);
        editingId.value = null;
    } catch (e) {
        alert(e.message || "Failed to delete allocation");
    }
};

const startEditing = (alloc) => {
    if (editingId.value === alloc.concept_id) return;
    editingId.value = alloc.concept_id;
    editForm.concept_id = alloc.concept_id;
    editForm.allocation_date = alloc.allocation_date;
    editForm.to_category_id = alloc.to_category_id;
    editForm.amount = minorToDollars(alloc.amount_minor);
    editForm.memo = alloc.memo || '';
};

const cancelEdit = () => { editingId.value = null; };

const saveEdit = async () => {
    try {
         await updateAllocationMutation.mutateAsync({
             id: editForm.concept_id,
             payload: {
                 allocation_date: editForm.allocation_date,
                 to_category_id: editForm.to_category_id,
                 amount_minor: Math.abs(dollarsToMinor(editForm.amount)),
                 memo: editForm.memo
             }
         });
         editingId.value = null;
    } catch (e) {
        alert(e.message || "Failed to update allocation");
    }
};

</script>