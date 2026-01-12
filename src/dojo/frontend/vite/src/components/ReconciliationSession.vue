<template>
  <div
    v-if="open"
    class="modal-overlay is-visible"
    id="reconciliation-session"
    style="display: flex;"
    @click.self="handleClose"
  >
    <div class="modal reconciliation-session">
      <header class="modal__header">
        <div>
          <p class="stat-card__label">{{ modeLabel }}</p>
          <h2>{{ title }}</h2>
          <p class="u-muted u-small-note">
            {{ subtitle }}
          </p>
        </div>
        <button
          class="modal__close"
          type="button"
          :aria-label="`Close ${modeLabel}`"
          @click="handleClose"
        >
          ×
        </button>
      </header>

      <div class="modal__body reconciliation-session__body">
        <p v-if="isLoading" class="u-muted">Loading reconciliation session…</p>

        <template v-else>
          <section
            v-if="error"
            class="reconciliation-session__error"
            aria-live="polite"
          >
            {{ error }}
          </section>

          <component
            :is="adapterComponent"
            v-if="adapterComponent"
            :account="account"
            :accounts="accounts"
            :categories="categories"
            @ready="handleAdapterReady"
            @close="handleClose"
          />

          <div
            v-if="showActions"
            class="form-panel__actions reconciliation-session__actions"
            data-testid="reconcile-session-actions"
          >
            <button
              type="button"
              class="button button--secondary"
              data-testid="reconcile-session-cancel"
              @click="handleClose"
              :disabled="isCommitting"
            >
              Cancel
            </button>
            <button
              v-if="commitLabel"
              type="button"
              class="button button--primary"
              data-testid="reconcile-session-commit"
              @click="handleCommit"
              :disabled="commitDisabled || isCommitting"
            >
              {{ isCommitting ? "Committing…" : commitLabel }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import LedgerReconciliationAdapter from "./reconciliation/LedgerReconciliationAdapter.vue";
import InvestmentReconciliationAdapter from "./reconciliation/InvestmentReconciliationAdapter.vue";
import TangibleReconciliationAdapter from "./reconciliation/TangibleReconciliationAdapter.vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	account: { type: Object, default: null },
	accounts: { type: Array, default: () => [] },
	categories: { type: Array, default: () => [] },
});

const emit = defineEmits(["close", "commit"]);

const error = ref("");
const isLoading = ref(false);
const isCommitting = ref(false);
const commitLabel = ref("");
const commitDisabled = ref(true);

const accountClass = computed(() => props.account?.account_class);

const modeLabel = computed(() => {
	const cls = accountClass.value;
	if (
		cls === "cash" ||
		cls === "credit" ||
		cls === "accessible" ||
		cls === "loan"
	) {
		return "Reconcile statement";
	}
	if (cls === "investment") {
		return "Verify holdings";
	}
	if (cls === "tangible") {
		return "Update valuation";
	}
	return "Reconcile";
});

const title = computed(() => props.account?.name || modeLabel.value);
const subtitle = computed(() => {
	const cls = accountClass.value;
	if (
		cls === "cash" ||
		cls === "credit" ||
		cls === "accessible" ||
		cls === "loan"
	) {
		return "Compare the statement to the ledger, edit any rows, then commit a checkpoint.";
	}
	if (cls === "investment") {
		return "Reconcile ticker, quantity, cost basis, and cash balance.";
	}
	if (cls === "tangible") {
		return "Update the current value for this tangible asset.";
	}
	return "";
});

const adapterComponent = computed(() => {
	const cls = accountClass.value;
	if (
		cls === "cash" ||
		cls === "credit" ||
		cls === "accessible" ||
		cls === "loan"
	) {
		return LedgerReconciliationAdapter;
	}
	if (cls === "investment") {
		return InvestmentReconciliationAdapter;
	}
	if (cls === "tangible") {
		return TangibleReconciliationAdapter;
	}
	return null;
});

const showActions = computed(() => {
	const cls = accountClass.value;
	if (
		cls === "cash" ||
		cls === "credit" ||
		cls === "accessible" ||
		cls === "loan"
	) {
		return true;
	}
	if (cls === "tangible") {
		return true;
	}
	return false;
});

function handleAdapterReady({ commitLabel: label, commitDisabled: disabled }) {
	commitLabel.value = label || "";
	commitDisabled.value = disabled ?? true;
	isLoading.value = false;
}

function handleClose() {
	emit("close");
}

async function handleCommit() {
	if (commitDisabled.value || isCommitting.value) {
		return;
	}
	isCommitting.value = true;
	try {
		await emit("commit");
		handleClose();
	} finally {
		isCommitting.value = false;
	}
}

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) {
			error.value = "";
			isLoading.value = true;
			commitLabel.value = "";
			commitDisabled.value = true;
			isCommitting.value = false;
		}
	},
);
</script>

<style scoped>
.reconciliation-session {
  width: min(1600px, 96vw);
  height: 90vh;
  max-width: 96vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.reconciliation-session__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.reconciliation-session__error {
  padding: 1rem;
  margin-bottom: 1rem;
  background-color: var(--danger-bg);
  border: 1px solid var(--danger);
  border-radius: 4px;
  color: var(--danger);
  font-family: var(--font-sans);
}

.reconciliation-session__actions {
  justify-content: flex-end;
  gap: 12px;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

@media (max-width: 900px) {
  .reconciliation-session {
    width: 98vw;
    height: 92vh;
    max-height: 92vh;
  }
}
</style>
