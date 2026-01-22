<template>
  <div
    v-if="open"
    class="modal-overlay is-visible"
    id="allocation-modal"
    style="display: flex;"
    @click.self="handleClose"
  >
    <div class="modal">
      <header class="modal__header">
        <div>
          <p class="stat-card__label">Allocation</p>
          <h2>Add allocation</h2>
          <p class="u-muted u-small-note">Move funds from Ready-to-Assign (or a category) into another category.</p>
        </div>
        <button class="modal__close" type="button" @click="handleClose">×</button>
      </header>
      <form class="modal-form" data-testid="allocation-form" @submit.prevent="submitAllocation">
        <div class="form-panel__grid form-panel__grid--compact">
          <label class="form-panel__field">
            <span>Date</span>
            <input
              type="date"
              name="allocation_date"
              required
              data-allocation-date
              v-model="allocationForm.allocation_date"
            />
          </label>
          <label class="form-panel__field">
            <span>From category</span>
            <select
              name="from_category_id"
              required
              data-allocation-from
              v-model="allocationForm.from_category_id"
            >
              <option v-for="cat in allocationCategories" :key="cat.category_id" :value="cat.category_id">
                {{ cat.name }}
              </option>
            </select>
          </label>
          <label class="form-panel__field">
            <span>To category</span>
            <select name="to_category_id" required data-allocation-to v-model="allocationForm.to_category_id">
              <option value="" disabled>Select category</option>
              <option v-for="cat in allocationCategories" :key="cat.category_id" :value="cat.category_id">
                {{ cat.name }}
              </option>
            </select>
          </label>
          <label class="form-panel__field">
            <span>Memo</span>
            <input type="text" name="memo" placeholder="Optional note" v-model="allocationForm.memo" />
          </label>
          <label class="form-panel__field form-panel__field--amount">
            <span>Amount</span>
            <input
              type="number"
              name="amount"
              step="0.01"
              inputmode="decimal"
              placeholder="0.00"
              required
              v-model="allocationForm.amount"
            />
          </label>
        </div>
        <p class="form-panel__error" data-testid="allocation-error" aria-live="polite">{{ allocationFormError }}</p>
        <div class="form-panel__actions">
          <button
            type="submit"
            class="button button--primary"
            data-allocation-submit
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? 'Saving...' : 'Save allocation' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useMutation } from "@tanstack/vue-query";
import { api } from "../services/api.js";
import { SPECIAL_CATEGORY_IDS } from "../constants.js";
import { dollarsToMinor, todayISO } from "../services/format.js";

const props = defineProps({
	open: { type: Boolean, default: false },
	allocationCategories: { type: Array, default: () => [] },
	readyToAssignMinor: { type: Number, default: 0 },
	refreshBudgetData: { type: Function, required: true },
});

const emit = defineEmits(["close"]);

const allocationForm = reactive({
	allocation_date: todayISO(),
	from_category_id: SPECIAL_CATEGORY_IDS.availableToBudget,
	to_category_id: "",
	memo: "",
	amount: "",
});
const allocationFormError = ref("");

const createAllocationMutation = useMutation({
	mutationFn: api.budgets.createAllocation,
	onSuccess: () => {
		props.refreshBudgetData();
	},
});

const isSubmitting = computed(() => createAllocationMutation.isPending.value);

const resetForm = () => {
	allocationForm.allocation_date = todayISO();
	allocationForm.from_category_id = SPECIAL_CATEGORY_IDS.availableToBudget;
	allocationForm.to_category_id = "";
	allocationForm.memo = "";
	allocationForm.amount = "";
	allocationFormError.value = "";
};

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) {
			resetForm();
		}
	},
);

const handleClose = () => {
	allocationFormError.value = "";
	emit("close");
};

const submitAllocation = async () => {
	allocationFormError.value = "";
	const amountMinor = Math.abs(dollarsToMinor(allocationForm.amount));

	if (!allocationForm.to_category_id) {
		allocationFormError.value = "Choose the destination category.";
		return;
	}
	if (
		allocationForm.from_category_id &&
		allocationForm.from_category_id === allocationForm.to_category_id
	) {
		allocationFormError.value =
			"Source and destination categories must differ.";
		return;
	}
	if (amountMinor === 0) {
		allocationFormError.value = "Amount must be greater than zero.";
		return;
	}

	if (allocationForm.from_category_id) {
		const sourceCategory = props.allocationCategories.find(
			(cat) => cat.category_id === allocationForm.from_category_id,
		);
		const availableMinor = sourceCategory?.available_minor ?? 0;
		if (availableMinor < amountMinor) {
			allocationFormError.value =
				"Source category has insufficient available funds.";
			return;
		}
	}

	try {
		await createAllocationMutation.mutateAsync({
			allocation_date: allocationForm.allocation_date,
			to_category_id: allocationForm.to_category_id,
			from_category_id: allocationForm.from_category_id,
			amount_minor: amountMinor,
			memo: allocationForm.memo || null,
		});
		resetForm();
		handleClose();
	} catch (e) {
		allocationFormError.value = e.message || "Allocation failed";
	}
};
</script>
