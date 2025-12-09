<template>
  <section class="route-page route-page--active transfers-page" id="transfers-page" data-route="transfers">
    <header class="transfers-page__header">
      <div>
        <p class="page-label">Categorized transfers</p>
        <p class="u-muted u-small-note">Move money between accounts while tagging the budget leg.</p>
      </div>
    </header>
    <section class="form-panel transfers-page__form">
      <form id="transfer-form" data-testid="transfer-form" @submit.prevent="submitTransfer">
        <div class="form-panel__grid">
          <label class="form-panel__field">
            <span>Date</span>
            <input type="date" name="transaction_date" required v-model="form.transaction_date" />
          </label>
          <label class="form-panel__field">
            <span>Source account</span>
            <select name="source_account_id" required data-transfer-source v-model="form.source_account_id">
              <option value="" disabled>Select source</option>
              <option v-for="acct in accounts" :key="acct.account_id" :value="acct.account_id">{{ acct.name }}</option>
            </select>
            <p v-if="sourceError" class="form-panel__helper" data-validation="source" aria-live="polite">{{ sourceError }}</p>
          </label>
          <label class="form-panel__field">
            <span>Destination account</span>
            <select name="destination_account_id" required data-transfer-destination v-model="form.destination_account_id">
              <option value="" disabled>Select destination</option>
              <option v-for="acct in accounts" :key="acct.account_id" :value="acct.account_id">{{ acct.name }}</option>
            </select>
            <p v-if="destinationError" class="form-panel__helper" data-validation="destination" aria-live="polite">{{ destinationError }}</p>
          </label>
          <label class="form-panel__field">
            <span>Category</span>
            <select name="category_id" required data-transfer-category v-model="form.category_id">
              <option value="" disabled>Select category</option>
              <option v-for="cat in categories" :key="cat.category_id" :value="cat.category_id">{{ cat.name }}</option>
            </select>
          </label>
          <label class="form-panel__field">
            <span>Memo</span>
            <input type="text" name="memo" placeholder="Optional context" v-model="form.memo" />
          </label>
          <label class="form-panel__field form-panel__field--amount">
            <span>Amount</span>
            <input type="number" name="amount" step="0.01" inputmode="decimal" placeholder="0.00" required v-model="form.amount" />
          </label>
        </div>
        <div class="form-panel__actions">
          <button type="submit" class="button button--primary" data-transfer-submit :disabled="!isValid || isSubmitting">{{ isSubmitting ? 'Posting...' : 'Post transfer' }}</button>
        </div>
      </form>
      <p v-if="formError" class="form-panel__error" data-testid="transfer-error" aria-live="polite">{{ formError }}</p>
    </section>
  </section>
</template>

<script setup>
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, reactive, ref } from "vue";
import { api } from "../../../static/services/api.js";
import { dollarsToMinor, todayISO } from "../../../static/services/format.js";

const queryClient = useQueryClient();

const referenceQuery = useQuery({
	queryKey: ["reference-data"],
	queryFn: api.reference.load,
});

const accounts = computed(() => referenceQuery.data.value?.accounts ?? []);
const categories = computed(() => referenceQuery.data.value?.categories ?? []);

const form = reactive({
	transaction_date: todayISO(),
	source_account_id: "",
	destination_account_id: "",
	category_id: "",
	memo: "",
	amount: "",
});

const formError = ref("");

const createTransferMutation = useMutation({
	mutationFn: api.transfers.create,
	onSuccess: () => {
		queryClient.invalidateQueries({ queryKey: ["transactions"] });
		queryClient.invalidateQueries({ queryKey: ["accounts"] });
		queryClient.invalidateQueries({ queryKey: ["budget-categories"] });
		queryClient.invalidateQueries({ queryKey: ["ready-to-assign"] });
	},
});

const isSubmitting = computed(() => createTransferMutation.isPending.value);

const sourceError = computed(() => {
	if (
		form.source_account_id &&
		form.destination_account_id &&
		form.source_account_id === form.destination_account_id
	) {
		return "Source and destination must differ.";
	}
	return "";
});

const destinationError = computed(() => sourceError.value); // Same error for both

const isValid = computed(() => {
	return (
		form.source_account_id &&
		form.destination_account_id &&
		form.category_id &&
		form.amount &&
		form.source_account_id !== form.destination_account_id &&
		Number(form.amount) > 0
	);
});

const submitTransfer = async () => {
	if (!isValid.value) return;
	formError.value = "";

	try {
		await createTransferMutation.mutateAsync({
			source_account_id: form.source_account_id,
			destination_account_id: form.destination_account_id,
			category_id: form.category_id,
			transaction_date: form.transaction_date,
			memo: form.memo || null,
			amount_minor: Math.abs(dollarsToMinor(form.amount)),
		});
		// Reset form but keep date?
		form.amount = "";
		form.memo = "";
		alert("Transfer posted successfully");
	} catch (e) {
		formError.value = e.message || "Transfer failed";
	}
};
</script>
