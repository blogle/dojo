<template>
  <section
    class="route-page route-page--active transactions-page"
    id="transactions-page"
    data-route="transactions"
    data-testid="transactions-page"
  >
    <header class="transactions-page__header">
      <p class="page-label">Transactions</p>
      <div class="transactions-page__stats">
        <article class="stat-card">
          <span class="stat-card__label">Spent this month</span>
          <span id="month-spend" class="stat-card__value">{{ monthSpend }}</span>
          <p class="u-muted u-small-note">
            Month-to-date spending from posted ledger activity.
          </p>
        </article>
        <article class="stat-card">
          <span class="stat-card__label">Budgeted this month</span>
          <span id="month-budgeted" class="stat-card__value">{{ monthBudgeted }}</span>
          <p class="u-muted u-small-note">Allocations applied to envelopes this month.</p>
        </article>
      </div>
      <p v-if="isLoadingAllocations" class="u-muted" aria-live="polite">Loading budget data…</p>
    </header>

    <div
      v-if="referenceError || allocationsError"
      class="form-panel__error"
      data-testid="reference-error"
      aria-live="polite"
    >
      <p v-if="referenceError">{{ referenceError }}</p>
      <p v-if="allocationsError" data-testid="allocations-error">{{ allocationsError }}</p>
    </div>

    <TransactionForm
      :accounts="accounts"
      :categories="categories"
      :isSubmitting="isCreating"
      :isLoadingReference="isLoadingReference"
      :referenceError="referenceError"
      @submit="handleCreateTransaction"
    />

    <div class="ledger-card">
      <TransactionTable
        :transactions="transactions"
        :accounts="accounts"
        :categories="categories"
        :isLoading="isLoadingTransactions"
        :isLoadingReference="isLoadingReference"
        :referenceError="referenceError"
        :error="transactionsError"
        tbodyId="transactions-body"
        @update="handleUpdateTransaction"
        @delete="handleDeleteTransaction"
      />
    </div>
  </section>
</template>

<script setup>
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed } from "vue";
import TransactionForm from "../components/TransactionForm.vue";
import TransactionTable from "../components/TransactionTable.vue";
import { api } from "../services/api.js";
import { currentMonthStartISO, formatAmount } from "../services/format.js";

const queryClient = useQueryClient();
const monthStart = currentMonthStartISO();

const invalidateLedgerQueries = async () => {
	await Promise.all([
		queryClient.invalidateQueries({ queryKey: ["transactions"] }),
		queryClient.invalidateQueries({ queryKey: ["budget-allocations"] }),
		queryClient.invalidateQueries({ queryKey: ["ready-to-assign"] }),
		queryClient.invalidateQueries({ queryKey: ["accounts"] }),
		queryClient.invalidateQueries({ queryKey: ["budget-categories"] }),
	]);
};

const referenceQuery = useQuery({
	queryKey: ["reference-data"],
	queryFn: () => api.reference.load(),
});

const transactionsQuery = useQuery({
	queryKey: ["transactions"],
	queryFn: () => api.transactions.list(100),
	refetchOnWindowFocus: false,
});

const allocationsQuery = useQuery({
	queryKey: ["budget-allocations", monthStart],
	queryFn: () => api.budgets.allocations(monthStart),
	refetchOnWindowFocus: false,
});

const referenceError = computed(
	() => referenceQuery.error.value?.message || "",
);
const transactionsError = computed(
	() => transactionsQuery.error.value?.message || "",
);
const allocationsError = computed(
	() => allocationsQuery.error.value?.message || "",
);

const isLoadingReference = computed(
	() => referenceQuery.isPending.value || referenceQuery.isFetching.value,
);
const isLoadingAllocations = computed(
	() => allocationsQuery.isPending.value || allocationsQuery.isFetching.value,
);

const createTransaction = useMutation({
	mutationFn: (payload) => api.transactions.create(payload),
	onSuccess: () => invalidateLedgerQueries(),
});

const updateTransaction = useMutation({
	mutationFn: ({ concept_id: conceptId, ...payload }) =>
		api.transactions.update(conceptId, payload),
	onMutate: async (payload) => {
		await queryClient.cancelQueries({ queryKey: ["transactions"] });
		const previous = queryClient.getQueryData(["transactions"]) ?? [];
		const updated = previous.map((tx) =>
			tx?.concept_id === payload.concept_id
				? {
						...tx,
						...payload,
						amount_minor: payload.amount_minor,
						transaction_date: payload.transaction_date,
						account_id: payload.account_id,
						category_id: payload.category_id,
						memo: payload.memo,
						status: payload.status,
					}
				: tx,
		);
		queryClient.setQueryData(["transactions"], updated);
		return { previous };
	},
	onError: (_error, _payload, context) => {
		if (context?.previous) {
			queryClient.setQueryData(["transactions"], context.previous);
		}
	},
	onSettled: () => invalidateLedgerQueries(),
});

const accounts = computed(() => referenceQuery.data.value?.accounts ?? []);
const categories = computed(() => referenceQuery.data.value?.categories ?? []);
const transactions = computed(() => transactionsQuery.data.value ?? []);

const monthSpendMinor = computed(() => {
	const now = new Date();
	const month = now.getMonth();
	const year = now.getFullYear();
	return transactions.value.reduce((total, tx) => {
		if (!tx?.transaction_date) return total;
		const date = new Date(`${tx.transaction_date}T00:00:00`);
		if (
			date.getMonth() === month &&
			date.getFullYear() === year &&
			tx.amount_minor < 0
		) {
			return total + Math.abs(tx.amount_minor);
		}
		return total;
	}, 0);
});

const monthSpend = computed(() => formatAmount(monthSpendMinor.value));
const monthBudgetedMinor = computed(() => {
	const allocations = allocationsQuery.data.value?.allocations ?? [];
	return allocations.reduce((total, entry) => {
		if (!entry?.from_category_id) {
			return total + (entry.amount_minor || 0);
		}
		return total;
	}, 0);
});
const monthBudgeted = computed(() => formatAmount(monthBudgetedMinor.value));

const isCreating = computed(() => createTransaction.isPending.value);
const isLoadingTransactions = computed(
	() => transactionsQuery.isPending.value || transactionsQuery.isFetching.value,
);

const handleCreateTransaction = async (payload, resolve, reject) => {
	try {
		await createTransaction.mutateAsync(payload);
		resolve();
	} catch (error) {
		reject(error);
	}
};

const handleUpdateTransaction = async (payload, resolve, reject) => {
	try {
		await updateTransaction.mutateAsync(payload);
		resolve();
	} catch (error) {
		reject(error);
	}
};

const handleDeleteTransaction = async (tx, resolve, reject) => {
	try {
		await api.transactions.delete(tx.concept_id);
		resolve();
	} catch (error) {
		reject(error);
	}
};
</script>
