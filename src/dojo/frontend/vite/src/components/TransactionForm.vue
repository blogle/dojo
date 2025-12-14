<template>
  <section :class="wrapperClasses">
    <form
      id="transaction-form"
      data-testid="transaction-form"
      aria-describedby="transaction-form-hint"
      @submit.prevent="handleSubmit"
    >
      <div class="segmented-control" role="group" aria-label="Transaction type">
        <span class="segmented-control__label">Type</span>
        <label class="segmented-control__option">
          <input
            type="radio"
            name="transaction-flow"
            value="outflow"
            data-transaction-flow
            v-model="transactionForm.flow"
            :disabled="isDisabled"
          />
          <span>Outflow</span>
        </label>
        <label class="segmented-control__option">
          <input
            type="radio"
            name="transaction-flow"
            value="inflow"
            data-transaction-flow
            v-model="transactionForm.flow"
            :disabled="isDisabled"
          />
          <span>Inflow</span>
        </label>
      </div>
      <div class="form-panel__grid form-panel__grid--compact">
        <label class="form-panel__field">
          <span>Date</span>
          <input
            type="date"
            name="transaction_date"
            v-model="transactionForm.transaction_date"
            required
            :disabled="isDisabled"
          />
        </label>
        <label class="form-panel__field">
          <span>Account</span>
          <select
            name="account_id"
            required
            data-transaction-account
            v-model="transactionForm.account_id"
            :disabled="isAccountDisabled"
          >
            <option value="" disabled>Select account</option>
            <option v-for="account in accountOptions" :key="account.account_id" :value="account.account_id">
              {{ account.name }}
            </option>
          </select>
        </label>
        <label class="form-panel__field">
          <span>Category</span>
          <select
            name="category_id"
            required
            data-transaction-category
            v-model="transactionForm.category_id"
            :disabled="isDisabled || isLoadingReference || !!referenceError"
          >
            <option value="" disabled>Select category</option>
            <option v-for="category in categories" :key="category.category_id" :value="category.category_id">
              {{ category.name }}
            </option>
          </select>
        </label>
        <label class="form-panel__field">
          <span>Memo</span>
          <input
            type="text"
            name="memo"
            placeholder="e.g. Grocery run"
            v-model="transactionForm.memo"
            :disabled="isDisabled"
          />
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
            v-model="transactionForm.amount"
            :disabled="isDisabled"
          />
        </label>
      </div>
      <div class="form-panel__actions">
        <button
          type="submit"
          :class="submitButtonClass"
          data-transaction-submit
          :disabled="isDisabled || isLoadingReference || !!referenceError"
        >
          {{ isSubmitting ? submittingLabel : submitLabel }}
        </button>
      </div>
    </form>
    <p class="form-panel__error" data-testid="transaction-error" aria-live="polite">{{ formError }}</p>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { todayISO } from "../services/format.js";
import {
	isValidDateInput,
	resolveSignedAmountFromFlow,
} from "../utils/transactions.js";

const props = defineProps({
	accounts: { type: Array, default: () => [] },
	categories: { type: Array, default: () => [] },
	lockedAccountId: { type: String, default: "" },
	lockedAccountName: { type: String, default: "" },
	isSubmitting: { type: Boolean, default: false },
	isLoadingReference: { type: Boolean, default: false },
	referenceError: { type: String, default: "" },
	submitButtonClass: {
		type: String,
		default: "button button--primary",
	},
	submitLabel: { type: String, default: "Save transaction" },
	submittingLabel: { type: String, default: "Saving…" },
	wrapperClass: { type: String, default: "" },
	resetMode: { type: String, default: "full" },
});

const emit = defineEmits(["submit"]);

const emitAsync = (eventName, ...args) =>
	new Promise((resolve, reject) => {
		emit(eventName, ...args, resolve, reject);
	});

const transactionForm = reactive({
	transaction_date: todayISO(),
	account_id: props.lockedAccountId || "",
	category_id: "",
	memo: "",
	amount: "",
	flow: "outflow",
});

const formError = ref("");

const isDisabled = computed(() => props.isSubmitting);
const isAccountDisabled = computed(
	() =>
		isDisabled.value ||
		props.isLoadingReference ||
		!!props.referenceError ||
		!!props.lockedAccountId,
);

const wrapperClasses = computed(() => {
	const base = "form-panel transactions-page__form";
	if (!props.wrapperClass) {
		return base;
	}
	return `${base} ${props.wrapperClass}`;
});

const accountOptions = computed(() => {
	if (!props.lockedAccountId) {
		return props.accounts;
	}
	const matching = props.accounts.filter(
		(account) => account.account_id === props.lockedAccountId,
	);
	if (matching.length) {
		return matching;
	}
	if (!props.lockedAccountName) {
		return [];
	}
	return [{ account_id: props.lockedAccountId, name: props.lockedAccountName }];
});

const resetForm = () => {
	if (props.resetMode === "partial") {
		transactionForm.memo = "";
		transactionForm.amount = "";
		return;
	}
	transactionForm.transaction_date = todayISO();
	transactionForm.account_id = props.lockedAccountId || "";
	transactionForm.category_id = "";
	transactionForm.memo = "";
	transactionForm.amount = "";
	transactionForm.flow = "outflow";
};

const handleSubmit = async () => {
	if (props.isSubmitting) {
		return;
	}

	formError.value = "";
	if (!isValidDateInput(transactionForm.transaction_date)) {
		formError.value = "Enter a valid date (YYYY-MM-DD).";
		return;
	}
	if (!transactionForm.account_id || !transactionForm.category_id) {
		formError.value = "Account and category are required.";
		return;
	}
	const amountResult = resolveSignedAmountFromFlow(
		transactionForm.amount,
		transactionForm.flow,
	);
	if (amountResult.error) {
		formError.value = amountResult.error;
		return;
	}
	const payload = {
		transaction_date: transactionForm.transaction_date || todayISO(),
		account_id: transactionForm.account_id,
		category_id: transactionForm.category_id,
		memo: transactionForm.memo?.trim() || null,
		amount_minor: amountResult.signedAmount,
		status: "pending",
	};

	try {
		await emitAsync("submit", payload);
		resetForm();
	} catch (error) {
		formError.value = error?.message || "Failed to save transaction.";
	}
};

watch(
	() => props.lockedAccountId,
	(value) => {
		if (value) {
			transactionForm.account_id = value;
		}
	},
);
</script>
