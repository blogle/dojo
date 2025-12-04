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

    <section class="form-panel transactions-page__form">
      <form
        id="transaction-form"
        data-testid="transaction-form"
        aria-describedby="transaction-form-hint"
        @submit.prevent="handleTransactionSubmit"
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
            />
            <span>Inflow</span>
          </label>
        </div>
        <div class="form-panel__grid form-panel__grid--compact">
          <label class="form-panel__field">
            <span>Date</span>
            <input type="date" name="transaction_date" v-model="transactionForm.transaction_date" required />
          </label>
          <label class="form-panel__field">
            <span>Account</span>
            <select
              name="account_id"
              required
              data-transaction-account
              v-model="transactionForm.account_id"
              :disabled="isLoadingReference || !!referenceError"
            >
              <option value="" disabled>Select account</option>
              <option
                v-for="account in accounts"
                :key="account.account_id"
                :value="account.account_id"
              >
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
              :disabled="isLoadingReference || !!referenceError"
            >
              <option value="" disabled>Select category</option>
              <option
                v-for="category in categories"
                :key="category.category_id"
                :value="category.category_id"
              >
                {{ category.name }}
              </option>
            </select>
          </label>
          <label class="form-panel__field">
            <span>Memo</span>
            <input type="text" name="memo" placeholder="e.g. Grocery run" v-model="transactionForm.memo" />
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
            />
          </label>
        </div>
        <div class="form-panel__actions">
          <button
            type="submit"
            class="button button--primary"
            data-transaction-submit
            :disabled="isCreating || isLoadingReference || !!referenceError"
          >
            {{ isCreating ? "Saving…" : "Save transaction" }}
          </button>
        </div>
      </form>
      <p class="form-panel__error" data-testid="transaction-error" aria-live="polite">{{ formError }}</p>
    </section>

    <div class="ledger-card">
      <table class="ledger-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Account</th>
            <th>Category</th>
            <th>Memo</th>
            <th class="ledger-table__amount">Outflow</th>
            <th class="ledger-table__amount">Inflow</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="transactions-body">
          <tr v-if="transactionsError">
            <td
              colspan="7"
              class="form-panel__error"
              data-testid="transactions-error"
              aria-live="polite"
              style="text-align: center"
            >
              {{ transactionsError }}
            </td>
          </tr>
          <tr v-else-if="isLoadingTransactions">
            <td colspan="7" class="u-muted" style="text-align: center">Loading transactions…</td>
          </tr>
          <tr v-else-if="!transactions.length">
            <td colspan="7" class="u-muted" style="text-align: center">No transactions found.</td>
          </tr>
          <template v-else>
            <tr
              v-for="tx in transactions"
              :key="tx.transaction_version_id"
              :class="{ 'is-editing': isEditing(tx), 'is-saving': isSavingInline(tx) }"
              @click="handleRowClick(tx)"
            >
              <template v-if="isEditing(tx)">
                <td>
                  <input type="date" data-inline-date v-model="inlineForm.transaction_date" :disabled="inlineSubmitting" />
                </td>
                <td>
                   <select
                     data-inline-account
                     v-model="inlineForm.account_id"
                     :disabled="inlineSubmitting || isLoadingReference || !!referenceError"
                   >

                    <option value="" disabled>Select account</option>
                    <option
                      v-for="account in accounts"
                      :key="account.account_id"
                      :value="account.account_id"
                    >
                      {{ account.name }}
                    </option>
                  </select>
                </td>
                <td>
                   <select
                     data-inline-category
                     v-model="inlineForm.category_id"
                     :disabled="inlineSubmitting || isLoadingReference || !!referenceError"
                   >

                    <option value="" disabled>Select category</option>
                    <option
                      v-for="category in categories"
                      :key="category.category_id"
                      :value="category.category_id"
                    >
                      {{ category.name }}
                    </option>
                  </select>
                </td>
                <td>
                  <input
                    type="text"
                    class="table-input"
                    data-inline-memo
                    placeholder="Optional memo"
                    v-model="inlineForm.memo"
                    :disabled="inlineSubmitting"
                    @keydown.enter.prevent="saveInlineEdit(tx)"
                  />
                  <p class="inline-row-feedback" data-inline-error aria-live="polite">{{ inlineError }}</p>
                </td>
                <td class="amount-cell">
                  <input
                    type="number"
                    data-inline-outflow
                    step="0.01"
                    inputmode="decimal"
                    placeholder="0.00"
                    :disabled="inlineSubmitting"
                    v-model="inlineForm.outflow"
                    @keydown.enter.prevent="saveInlineEdit(tx)"
                  />
                </td>
                <td class="amount-cell">
                  <input
                    type="number"
                    data-inline-inflow
                    step="0.01"
                    inputmode="decimal"
                    placeholder="0.00"
                    :disabled="inlineSubmitting"
                    v-model="inlineForm.inflow"
                    @keydown.enter.prevent="saveInlineEdit(tx)"
                  />
                </td>
                <td>
                  <button
                    type="button"
                    class="status-toggle-badge"
                    data-inline-status-toggle
                    :data-state="inlineForm.status"
                    role="switch"
                    :aria-checked="inlineForm.status === 'cleared' ? 'true' : 'false'"
                    :disabled="inlineSubmitting"
                    @click.stop="toggleInlineStatus"
                    v-html="statusIcons"
                  ></button>
                </td>
              </template>
              <template v-else>
                <td data-testid="transaction-col-date">{{ tx.transaction_date || "N/A" }}</td>
                <td data-testid="transaction-col-account">{{ tx.account_name || "N/A" }}</td>
                <td data-testid="transaction-col-category">{{ tx.category_name || "N/A" }}</td>
                <td data-testid="transaction-col-memo">{{ tx.memo || "—" }}</td>
                <td class="amount-cell" data-testid="transaction-col-outflow">
                  {{ tx.amount_minor < 0 ? formatAmountDisplay(Math.abs(tx.amount_minor)) : "—" }}
                </td>
                <td class="amount-cell" data-testid="transaction-col-inflow">
                  {{ tx.amount_minor >= 0 ? formatAmountDisplay(Math.abs(tx.amount_minor)) : "—" }}
                </td>
                <td data-testid="transaction-col-status">
                  <button
                    type="button"
                    class="status-toggle-badge"
                    data-status-display
                    :data-state="tx.status === 'cleared' ? 'cleared' : 'pending'"
                    role="status"
                    aria-disabled="true"
                    tabindex="-1"
                    v-html="statusIcons"
                  ></button>
                </td>
              </template>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue';
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import { api } from '../../../static/services/api.js';
import { currentMonthStartISO, dollarsToMinor, formatAmount, todayISO } from '../../../static/services/format.js';
import { statusToggleIcons } from '../../../static/constants.js';

const queryClient = useQueryClient();
const monthStart = currentMonthStartISO();

const invalidateLedgerQueries = async () => {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['transactions'] }),
    queryClient.invalidateQueries({ queryKey: ['budget-allocations'] }),
    queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] }),
    queryClient.invalidateQueries({ queryKey: ['accounts'] }),
    queryClient.invalidateQueries({ queryKey: ['budget-categories'] }),
  ]);
};

const transactionForm = reactive({
  transaction_date: todayISO(),
  account_id: '',
  category_id: '',
  memo: '',
  amount: '',
  flow: 'outflow',
});

const formError = ref('');
const inlineError = ref('');
const editingId = ref(null);
const inlineSubmitting = ref(false);
const inlineForm = reactive({
  transaction_date: todayISO(),
  account_id: '',
  category_id: '',
  memo: '',
  inflow: '',
  outflow: '',
  status: 'pending',
});

const statusIcons = statusToggleIcons;

const isValidDateInput = (value) => {
  if (!value) {
    return false;
  }
  const parsed = Date.parse(`${value}T00:00:00`);
  return Number.isFinite(parsed);
};

const toMinor = (value) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return dollarsToMinor(parsed);
};

const referenceQuery = useQuery({
  queryKey: ['reference-data'],
  queryFn: () => api.reference.load(),
});

const transactionsQuery = useQuery({
  queryKey: ['transactions'],
  queryFn: () => api.transactions.list(100),
  refetchOnWindowFocus: false,
});

const allocationsQuery = useQuery({
  queryKey: ['budget-allocations', monthStart],
  queryFn: () => api.budgets.allocations(monthStart),
  refetchOnWindowFocus: false,
});

const referenceError = computed(() => referenceQuery.error?.message || '');
const transactionsError = computed(() => transactionsQuery.error?.message || '');
const allocationsError = computed(() => allocationsQuery.error?.message || '');

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
    await queryClient.cancelQueries({ queryKey: ['transactions'] });
    const previous = queryClient.getQueryData(['transactions']) ?? [];
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
    queryClient.setQueryData(['transactions'], updated);
    return { previous };
  },
  onError: (_error, _payload, context) => {
    if (context?.previous) {
      queryClient.setQueryData(['transactions'], context.previous);
    }
  },
  onSettled: () => invalidateLedgerQueries(),
});

const accounts = computed(() => referenceQuery.data?.accounts ?? []);
const categories = computed(() => referenceQuery.data?.categories ?? []);
const transactions = computed(() => {
  const data = transactionsQuery.data ?? [];
  return [...data].sort((a, b) => {
    const aDate = a?.transaction_date ? new Date(`${a.transaction_date}T00:00:00`) : 0;
    const bDate = b?.transaction_date ? new Date(`${b.transaction_date}T00:00:00`) : 0;
    return bDate - aDate;
  });
});

const monthSpendMinor = computed(() => {
  const now = new Date();
  const month = now.getMonth();
  const year = now.getFullYear();
  return transactions.value.reduce((total, tx) => {
    if (!tx?.transaction_date) return total;
    const date = new Date(`${tx.transaction_date}T00:00:00`);
    if (date.getMonth() === month && date.getFullYear() === year && tx.amount_minor < 0) {
      return total + Math.abs(tx.amount_minor);
    }
    return total;
  }, 0);
});

const monthSpend = computed(() => formatAmount(monthSpendMinor.value));
const monthBudgetedMinor = computed(() => {
  const allocations = allocationsQuery.data?.allocations ?? [];
  return allocations.reduce((total, entry) => {
    if (!entry?.from_category_id) {
      return total + (entry.amount_minor || 0);
    }
    return total;
  }, 0);
});
const monthBudgeted = computed(() => formatAmount(monthBudgetedMinor.value));

const isCreating = computed(() => createTransaction.isPending.value);
const isLoadingTransactions = computed(() => transactionsQuery.isPending.value || transactionsQuery.isFetching.value);

const resetForm = () => {
  transactionForm.transaction_date = todayISO();
  transactionForm.account_id = '';
  transactionForm.category_id = '';
  transactionForm.memo = '';
  transactionForm.amount = '';
  transactionForm.flow = 'outflow';
};

const formatAmountDisplay = (minor) => formatAmount(minor);

const handleTransactionSubmit = async () => {
  formError.value = '';
  const amountMinor = toMinor(transactionForm.amount);
  if (!isValidDateInput(transactionForm.transaction_date)) {
    formError.value = 'Enter a valid date (YYYY-MM-DD).';
    return;
  }
  if (!transactionForm.account_id || !transactionForm.category_id) {
    formError.value = 'Account and category are required.';
    return;
  }
  if (amountMinor === null) {
    formError.value = 'Enter a valid amount.';
    return;
  }
  const normalizedAmount = Math.abs(amountMinor);
  if (normalizedAmount === 0) {
    formError.value = 'Amount must be non-zero.';
    return;
  }
  const signedAmount = transactionForm.flow === 'outflow' ? -normalizedAmount : normalizedAmount;
  const payload = {
    transaction_date: transactionForm.transaction_date || todayISO(),
    account_id: transactionForm.account_id,
    category_id: transactionForm.category_id,
    memo: transactionForm.memo?.trim() || null,
    amount_minor: signedAmount,
    status: 'pending',
  };
  try {
    await createTransaction.mutateAsync(payload);
    resetForm();
  } catch (error) {
    formError.value = error?.message || 'Failed to save transaction.';
  }
};

const isEditing = (tx) => editingId.value === tx.transaction_version_id;
const isSavingInline = (tx) => updateTransaction.isPending.value && isEditing(tx);

const populateInlineForm = (tx) => {
  inlineForm.transaction_date = tx.transaction_date || todayISO();
  inlineForm.account_id = tx.account_id || '';
  inlineForm.category_id = tx.category_id || '';
  inlineForm.memo = tx.memo || '';
  inlineForm.status = tx.status === 'cleared' ? 'cleared' : 'pending';
  if (tx.amount_minor < 0) {
    inlineForm.outflow = (Math.abs(tx.amount_minor) / 100).toFixed(2);
    inlineForm.inflow = '';
  } else {
    inlineForm.inflow = (Math.abs(tx.amount_minor) / 100).toFixed(2);
    inlineForm.outflow = '';
  }
  inlineError.value = '';
};

const handleRowClick = async (tx) => {
  if (isEditing(tx)) {
    return;
  }
  editingId.value = tx.transaction_version_id;
  populateInlineForm(tx);
  await nextTick();
};

const validateInlinePayload = () => {
  if (!isValidDateInput(inlineForm.transaction_date)) {
    inlineError.value = 'Enter a valid date (YYYY-MM-DD).';
    return null;
  }
  if (!inlineForm.account_id || !inlineForm.category_id) {
    inlineError.value = 'Account and category are required.';
    return null;
  }
  const inflowMinor = toMinor(inlineForm.inflow);
  const outflowMinor = toMinor(inlineForm.outflow);
  const hasInflow = inflowMinor !== null && inflowMinor !== 0;
  const hasOutflow = outflowMinor !== null && outflowMinor !== 0;

  if (hasInflow && hasOutflow) {
    inlineError.value = 'Enter either an inflow or an outflow, not both.';
    return null;
  }

  const pickedMinor = hasInflow ? Math.abs(inflowMinor) : hasOutflow ? Math.abs(outflowMinor) : null;

  if (!pickedMinor) {
    inlineError.value = 'Amount must be non-zero.';
    return null;
  }

  const signedAmount = hasInflow ? pickedMinor : -pickedMinor;
  return { signedAmount };
};

const saveInlineEdit = async (tx) => {
  if (!tx || !isEditing(tx)) {
    return;
  }
  inlineError.value = '';
  const validation = validateInlinePayload();
  if (!validation) {
    return;
  }
  const payload = {
    concept_id: tx.concept_id,
    transaction_date: inlineForm.transaction_date || todayISO(),
    account_id: inlineForm.account_id,
    category_id: inlineForm.category_id,
    memo: inlineForm.memo?.trim() || null,
    amount_minor: validation.signedAmount,
    status: inlineForm.status,
  };
  try {
    inlineSubmitting.value = true;
    await updateTransaction.mutateAsync(payload);
    editingId.value = null;
  } catch (error) {
    inlineError.value = error?.message || 'Failed to save changes.';
  } finally {
    inlineSubmitting.value = false;
  }
};

const toggleInlineStatus = () => {
  inlineForm.status = inlineForm.status === 'cleared' ? 'pending' : 'cleared';
};

watch(
  () => inlineForm.inflow,
  (value) => {
    if (value && Number.parseFloat(value) !== 0) {
      inlineForm.outflow = '';
    }
  },
);

watch(
  () => inlineForm.outflow,
  (value) => {
    if (value && Number.parseFloat(value) !== 0) {
      inlineForm.inflow = '';
    }
  },
);
</script>
