<template>
  <div
    v-if="open"
    class="modal-overlay is-visible"
    id="reconciliation-modal"
    style="display: flex;"
    @click.self="handleClose"
  >
    <div class="modal reconciliation-modal">
      <header class="modal__header">
        <div>
          <p class="stat-card__label">Reconcile account</p>
          <h2>{{ selectedAccount?.name || "Reconcile" }}</h2>
          <p class="u-muted u-small-note">
            Compare the statement to the ledger, edit any rows, then commit a checkpoint.
          </p>
        </div>
        <button
          class="modal__close"
          type="button"
          aria-label="Close reconciliation"
          @click="handleClose"
        >
          ×
        </button>
      </header>

      <div class="modal__body reconciliation-modal__body">
        <p v-if="step === 'loading'" class="u-muted">Loading reconciliation worksheet…</p>

        <section v-else-if="step === 'setup'" class="modal-add">
          <form class="modal-form" @submit.prevent="beginWorksheet">
            <label>
              Statement date
              <input type="date" v-model="statementForm.statementDate" required />
            </label>
            <label>
              Settled balance
              <input
                type="number"
                step="0.01"
                inputmode="decimal"
                placeholder="0.00"
                v-model="statementForm.statementSettled"
                required
              />
            </label>
            <label>
              Pending balance
              <input
                type="number"
                step="0.01"
                inputmode="decimal"
                placeholder="0.00"
                v-model="statementForm.statementPending"
                required
              />
            </label>
            <p class="u-muted u-small-note">Statement total: {{ statementTotalLabel }}</p>
            <p v-if="error" class="form-panel__error" aria-live="polite">{{ error }}</p>
            <div class="form-panel__actions form-panel__actions--split reconciliation-modal__actions">
              <button type="button" class="button button--secondary" @click="handleClose">Cancel</button>
              <button type="submit" class="button button--primary" :disabled="isStarting">
                {{ isStarting ? "Loading…" : "Continue" }}
              </button>
            </div>
          </form>
        </section>

        <section v-else-if="step === 'worksheet'" class="reconciliation-modal__worksheet">
          <div class="reconciliation-modal__summary">
            <table class="reconciliation-summary-table" aria-label="Reconciliation summary">
              <thead>
                <tr>
                  <th>Source</th>
                  <th class="reconciliation-summary-table__amount">Settled</th>
                  <th class="reconciliation-summary-table__amount">Pending</th>
                  <th class="reconciliation-summary-table__amount">Total</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Statement</td>
                  <td class="reconciliation-summary-table__amount">{{ formatMinor(statementSettledMinor) }}</td>
                  <td class="reconciliation-summary-table__amount">{{ formatMinor(statementPendingMinor) }}</td>
                  <td class="reconciliation-summary-table__amount">{{ formatMinor(statementTotalMinor) }}</td>
                </tr>
                <tr>
                  <td>Ledger</td>
                  <td class="reconciliation-summary-table__amount">{{ formatMinor(ledgerSettledMinor) }}</td>
                  <td class="reconciliation-summary-table__amount">{{ formatMinor(ledgerPendingMinor) }}</td>
                  <td class="reconciliation-summary-table__amount">{{ formatMinor(ledgerTotalMinor) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>Difference</td>
                  <td
                    class="reconciliation-summary-table__amount"
                    :class="differenceCellClasses(differenceSettledMinor)"
                  >
                    {{ formatMinor(differenceSettledMinor) }}
                  </td>
                  <td
                    class="reconciliation-summary-table__amount"
                    :class="differenceCellClasses(differencePendingMinor)"
                  >
                    {{ formatMinor(differencePendingMinor) }}
                  </td>
                  <td
                    class="reconciliation-summary-table__amount"
                    :class="differenceCellClasses(differenceTotalMinor)"
                  >
                    {{ formatMinor(differenceTotalMinor) }}
                  </td>
                </tr>
              </tfoot>
            </table>

            <p class="reconciliation-modal__summary-helper">
              <span class="reconciliation-modal__summary-dot" aria-hidden="true"></span>
              Summary is read-only. Resolve differences by editing ledger rows below.
            </p>
          </div>

          <div class="form-panel__actions reconciliation-modal__actions">
            <button type="button" class="button button--secondary" @click="backToSetup" :disabled="isFinishing">
              Back
            </button>
            <button type="button" class="button button--primary" @click="commit" :disabled="commitDisabled">
              {{ isFinishing ? "Committing…" : "Commit" }}
            </button>
          </div>

          <TransactionForm
            wrapperClass="reconciliation-modal__form"
            :accounts="lockedAccounts"
            :categories="categories"
            :lockedAccountId="selectedAccount?.account_id || ''"
            :lockedAccountName="selectedAccount?.name || ''"
            :isSubmitting="isCreatingTransaction"
            :isLoadingReference="isLoadingReference"
            :referenceError="referenceError"
            submitButtonClass="button button--secondary"
            submittingLabel="Adding…"
            resetMode="partial"
            @submit="handleCreateTransaction"
          />

          <div class="ledger-card reconciliation-modal__ledger">
            <TransactionTable
              :transactions="worksheetItems"
              :accounts="lockedAccounts"
              :categories="categories"
              :lockedAccountId="selectedAccount?.account_id || ''"
              :lockedAccountName="selectedAccount?.name || ''"
              :isLoading="isLoadingWorksheet"
              :isLoadingReference="isLoadingReference"
              :referenceError="referenceError"
              :error="tableError"
              emptyMessage="No transactions in worksheet."
              loadingMessage="Refreshing ledger…"
              @update="handleUpdateTransaction"
              @delete="handleDeleteTransaction"
            />
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMutation, useQuery } from "@tanstack/vue-query";
import { computed, reactive, ref, watch } from "vue";
import TransactionForm from "./TransactionForm.vue";
import TransactionTable from "./TransactionTable.vue";
import { api } from "../services/api.js";
import { dollarsToMinor, formatAmount, todayISO } from "../services/format.js";

const props = defineProps({
	open: { type: Boolean, default: false },
	account: { type: Object, default: null },
});

const emit = defineEmits(["close"]);

const selectedAccount = computed(() => props.account);
const accountId = computed(() => props.account?.account_id || "");

const step = ref("setup");
const error = ref("");

const statementForm = reactive({
	statementDate: todayISO(),
	statementSettled: "",
	statementPending: "",
});

const referenceQuery = useQuery({
	queryKey: ["reference-data"],
	queryFn: api.reference.load,
	enabled: computed(() => props.open),
	refetchOnWindowFocus: false,
});

const accountsQuery = useQuery({
	queryKey: ["accounts"],
	queryFn: api.accounts.list,
	enabled: computed(() => props.open),
	refetchOnWindowFocus: false,
});

const worksheetQuery = useQuery({
	queryKey: computed(() => ["reconciliation-worksheet", accountId.value]),
	queryFn: () => api.reconciliations.getWorksheet(accountId.value),
	enabled: computed(
		() =>
			props.open &&
			!!accountId.value &&
			(step.value === "loading" || step.value === "worksheet"),
	),
	refetchOnWindowFocus: false,
});

const categories = computed(() => referenceQuery.data.value?.categories ?? []);
const lockedAccounts = computed(() =>
	selectedAccount.value ? [selectedAccount.value] : [],
);
const worksheetItems = computed(() => worksheetQuery.data.value ?? []);

const referenceError = computed(
	() => referenceQuery.error.value?.message || "",
);
const worksheetError = computed(
	() => worksheetQuery.error.value?.message || "",
);

const isLoadingReference = computed(
	() => referenceQuery.isPending.value || referenceQuery.isFetching.value,
);
const isLoadingWorksheet = computed(
	() => worksheetQuery.isPending.value || worksheetQuery.isFetching.value,
);

const isStarting = computed(() => step.value === "loading");

const accountBalanceMinor = computed(() => {
	if (!accountId.value) {
		return null;
	}
	const refreshed = (accountsQuery.data.value ?? []).find(
		(acct) => acct.account_id === accountId.value,
	);
	return (
		refreshed?.current_balance_minor ??
		props.account?.current_balance_minor ??
		null
	);
});

function parseMinor(value) {
	if (value === null || value === undefined) {
		return null;
	}
	if (String(value).trim() === "") {
		return null;
	}
	return dollarsToMinor(value);
}

function formatMinor(minor) {
	if (minor === null || minor === undefined) {
		return "—";
	}
	return formatAmount(minor);
}

function differenceCellClasses(minor) {
	if (minor === null || minor === undefined) {
		return {};
	}
	return {
		"reconciliation-summary-table__balanced": minor === 0,
		"reconciliation-summary-table__unbalanced": minor !== 0,
	};
}

const statementSettledMinor = computed(() =>
	parseMinor(statementForm.statementSettled),
);
const statementPendingMinor = computed(() =>
	parseMinor(statementForm.statementPending),
);
const statementTotalMinor = computed(() => {
	if (
		statementSettledMinor.value === null ||
		statementPendingMinor.value === null
	) {
		return null;
	}
	return statementSettledMinor.value + statementPendingMinor.value;
});

const statementTotalLabel = computed(() =>
	formatMinor(statementTotalMinor.value),
);

const pendingSumMinor = computed(() =>
	worksheetItems.value
		.filter((item) => item.status !== "cleared")
		.reduce((sum, item) => sum + (item.amount_minor || 0), 0),
);

const ledgerTotalMinor = computed(() => accountBalanceMinor.value);
const ledgerSettledMinor = computed(() => {
	if (ledgerTotalMinor.value === null || ledgerTotalMinor.value === undefined) {
		return null;
	}
	return ledgerTotalMinor.value - pendingSumMinor.value;
});
const ledgerPendingMinor = computed(() => pendingSumMinor.value);

const differenceSettledMinor = computed(() => {
	if (
		statementSettledMinor.value === null ||
		ledgerSettledMinor.value === null
	) {
		return null;
	}
	return statementSettledMinor.value - ledgerSettledMinor.value;
});

const differencePendingMinor = computed(() => {
	if (
		statementPendingMinor.value === null ||
		ledgerPendingMinor.value === null
	) {
		return null;
	}
	return statementPendingMinor.value - ledgerPendingMinor.value;
});

const differenceTotalMinor = computed(() => {
	if (statementTotalMinor.value === null || ledgerTotalMinor.value === null) {
		return null;
	}
	return statementTotalMinor.value - ledgerTotalMinor.value;
});

const createTransactionMutation = useMutation({
	mutationFn: (payload) => api.transactions.create(payload),
});

const updateTransactionMutation = useMutation({
	mutationFn: ({ concept_id: conceptId, ...payload }) =>
		api.transactions.update(conceptId, payload),
});

const deleteTransactionMutation = useMutation({
	mutationFn: (conceptId) => api.transactions.delete(conceptId),
});

const commitReconciliationMutation = useMutation({
	mutationFn: ({ accountId: id, payload }) =>
		api.reconciliations.create(id, payload),
});

const isCreatingTransaction = computed(
	() => createTransactionMutation.isPending.value,
);
const isFinishing = computed(
	() => commitReconciliationMutation.isPending.value,
);

const commitDisabled = computed(() => {
	if (isFinishing.value || isLoadingWorksheet.value) {
		return true;
	}
	if (
		differenceSettledMinor.value === null ||
		differencePendingMinor.value === null
	) {
		return true;
	}
	return (
		differenceSettledMinor.value !== 0 || differencePendingMinor.value !== 0
	);
});

const tableError = computed(() => error.value || worksheetError.value || "");

const handleCreateTransaction = async (payload, resolve, reject) => {
	try {
		await createTransactionMutation.mutateAsync(payload);
		resolve();
	} catch (err) {
		reject(err);
	}
};

const handleUpdateTransaction = async (payload, resolve, reject) => {
	try {
		await updateTransactionMutation.mutateAsync(payload);
		resolve();
	} catch (err) {
		reject(err);
	}
};

const handleDeleteTransaction = async (tx, resolve, reject) => {
	try {
		await deleteTransactionMutation.mutateAsync(tx.concept_id);
		resolve();
	} catch (err) {
		reject(err);
	}
};

async function beginWorksheet() {
	error.value = "";

	if (!accountId.value) {
		error.value = "Select an account to reconcile.";
		return;
	}
	if (statementSettledMinor.value === null) {
		error.value = "Enter a settled balance.";
		return;
	}
	if (statementPendingMinor.value === null) {
		error.value = "Enter a pending balance.";
		return;
	}

	step.value = "loading";
	try {
		await Promise.all([
			referenceQuery.refetch(),
			accountsQuery.refetch(),
			worksheetQuery.refetch(),
		]);
	} catch (err) {
		error.value = err?.message || "Failed to load worksheet.";
	} finally {
		step.value = "worksheet";
	}
}

function backToSetup() {
	step.value = "setup";
	error.value = "";
}

async function commit() {
	error.value = "";
	if (!accountId.value) {
		return;
	}
	if (commitDisabled.value) {
		return;
	}

	try {
		await commitReconciliationMutation.mutateAsync({
			accountId: accountId.value,
			payload: {
				statement_date: statementForm.statementDate,
				statement_balance_minor: statementSettledMinor.value,
			},
		});
		handleClose();
	} catch (err) {
		error.value = err?.message || "Failed to commit reconciliation.";
	}
}

function resetState() {
	step.value = "setup";
	error.value = "";

	statementForm.statementDate = todayISO();
	statementForm.statementSettled = "";
	statementForm.statementPending = "";
}

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) {
			resetState();
		}
	},
);

watch(
	() => props.account?.account_id,
	() => {
		if (props.open) {
			resetState();
		}
	},
);

function handleClose() {
	emit("close");
}
</script>

<style scoped>
.reconciliation-modal {
  width: min(1600px, 96vw);
  height: 90vh;
  max-width: 96vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.reconciliation-modal__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.reconciliation-modal__worksheet {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reconciliation-modal__summary {
  overflow-x: auto;
}

.reconciliation-summary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
  border-top: 2px solid var(--text);
  border-bottom: 2px solid var(--text);
}

.reconciliation-summary-table th {
  text-align: right;
  font-family: var(--font-sans);
  font-weight: 700;
  padding: 0.75rem 0.75rem 0.5rem;
  border-bottom: 1px solid var(--text);
  white-space: nowrap;
}

.reconciliation-summary-table th:first-child {
  text-align: left;
}

.reconciliation-summary-table td {
  padding: 0.6rem 0.75rem;
  vertical-align: middle;
  white-space: nowrap;
}

.reconciliation-summary-table td:first-child {
  text-align: left;
  font-family: var(--font-sans);
  font-weight: 500;
}

.reconciliation-summary-table__amount {
  text-align: right;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.reconciliation-summary-table tfoot td {
  font-weight: 700;
  border-top: 1px solid var(--text);
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

.reconciliation-summary-table tfoot td:first-child {
  font-family: var(--font-sans);
  color: var(--muted);
  text-transform: uppercase;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
}

.reconciliation-summary-table__balanced {
  color: var(--success);
}

.reconciliation-summary-table__unbalanced {
  color: var(--danger);
}

.reconciliation-modal__summary-helper {
  margin-top: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--muted);
}

.reconciliation-modal__summary-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: var(--accent);
  border-radius: 50%;
  flex: 0 0 auto;
}

.reconciliation-modal__actions {
  justify-content: flex-end;
  gap: 12px;
}

.reconciliation-modal__form {
  margin: 0;
}

.reconciliation-modal__ledger {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
}

@media (max-width: 900px) {
  .reconciliation-modal {
    width: 98vw;
    height: 92vh;
    max-height: 92vh;
  }

  .reconciliation-summary-table {
    font-size: 0.9rem;
  }
}
</style>
