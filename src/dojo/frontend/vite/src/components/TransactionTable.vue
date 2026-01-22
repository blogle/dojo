<template>
  <div ref="tableWrapper">
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
      <tbody :id="tbodyId || undefined">
        <tr v-if="effectiveError">
          <td
            colspan="7"
            class="form-panel__error"
            data-testid="transactions-error"
            aria-live="polite"
            style="text-align: center"
          >
            {{ effectiveError }}
          </td>
        </tr>
        <tr v-else-if="isLoading">
          <td colspan="7" class="u-muted" style="text-align: center">{{ loadingMessage }}</td>
        </tr>
        <tr v-else-if="!sortedTransactions.length">
          <td colspan="7" class="u-muted" style="text-align: center">{{ emptyMessage }}</td>
        </tr>
        <template v-else>
          <tr
            v-for="tx in sortedTransactions"
            :key="tx.transaction_version_id"
            :class="{ 'is-editing': isEditing(tx), 'is-saving': isSavingInline(tx), 'is-deleting': deletingIds.has(tx.transaction_version_id) }"
            tabindex="0"
            @click="handleRowClick(tx)"
            @keydown.enter.prevent="handleRowClick(tx)"
            @keydown.escape.prevent="cancelInlineEdit"
          >
            <template v-if="isEditing(tx)">
              <td>
                <input type="date" data-inline-date v-model="inlineForm.transaction_date" :disabled="inlineSubmitting" />
              </td>
              <td>
                <select
                  data-inline-account
                  v-model="inlineForm.account_id"
                  :disabled="inlineSubmitting || isLoadingReference || !!referenceError || isAccountLocked"
                >
                  <option value="" disabled>Select account</option>
                  <option v-for="account in accountOptions" :key="account.account_id" :value="account.account_id">
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
                    v-for="category in inlineCategoryOptions"
                    :key="category.category_id"
                    :value="category.category_id"
                    :disabled="category._ephemeral === true"
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
                <div class="cell-actions">
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
                  <button
                    type="button"
                    class="action-button"
                    data-inline-delete
                    title="Delete transaction"
                    :disabled="inlineSubmitting"
                    @click.stop="handleDelete(tx)"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                  </button>
                </div>
              </td>
            </template>
            <template v-else>
              <td data-testid="transaction-col-date">{{ tx.transaction_date || "N/A" }}</td>
              <td data-testid="transaction-col-account">{{ accountName(tx) }}</td>
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
                  role="switch"
                  :aria-checked="tx.status === 'cleared' ? 'true' : 'false'"
                  @click.stop="toggleRowStatus(tx)"
                  v-html="statusIcons"
                ></button>
              </td>
            </template>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import {
	computed,
	nextTick,
	onBeforeUnmount,
	onMounted,
	reactive,
	ref,
	watch,
} from "vue";
import { statusToggleIcons } from "../constants.js";
import { formatAmount, todayISO } from "../services/format.js";
import {
	amountMinorToInlineFields,
	isValidDateInput,
	resolveInlineSignedAmountMinor,
} from "../utils/transactions.js";

const props = defineProps({
	transactions: { type: Array, default: () => [] },
	accounts: { type: Array, default: () => [] },
	categories: { type: Array, default: () => [] },
	lockedAccountId: { type: String, default: "" },
	lockedAccountName: { type: String, default: "" },
	isLoading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	emptyMessage: { type: String, default: "No transactions found." },
	loadingMessage: { type: String, default: "Loading transactions…" },
	isLoadingReference: { type: Boolean, default: false },
	referenceError: { type: String, default: "" },
	tbodyId: { type: String, default: "" },
	deleteAnimationMs: { type: Number, default: 500 },
});

const emit = defineEmits(["update", "delete"]);

const statusIcons = statusToggleIcons;

const tableWrapper = ref(null);

const editingId = ref(null);
const inlineSubmitting = ref(false);
const inlineError = ref("");
const localError = ref("");

const deletingIds = reactive(new Set());

const inlineForm = reactive({
	transaction_date: todayISO(),
	account_id: "",
	category_id: "",
	memo: "",
	inflow: "",
	outflow: "",
	status: "pending",
});

const isAccountLocked = computed(() => !!props.lockedAccountId);

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

const inlineCategoryOptions = computed(() => {
	const base = Array.isArray(props.categories) ? props.categories : [];
	const currentId = inlineForm.category_id;
	if (!currentId) {
		return base;
	}
	if (base.some((c) => c?.category_id === currentId)) {
		return base;
	}
	const currentTx = (props.transactions ?? []).find(
		(tx) => tx?.transaction_version_id === editingId.value,
	);
	const label = currentTx?.category_name || currentId;
	return [...base, { category_id: currentId, name: label, _ephemeral: true }];
});

const sortedTransactions = computed(() => {
	const data = props.transactions ?? [];
	return [...data].sort((a, b) => {
		const aDate = a?.transaction_date
			? new Date(`${a.transaction_date}T00:00:00`).getTime()
			: 0;
		const bDate = b?.transaction_date
			? new Date(`${b.transaction_date}T00:00:00`).getTime()
			: 0;
		return bDate - aDate;
	});
});

const effectiveError = computed(() => props.error || localError.value);

const formatAmountDisplay = (minor) => formatAmount(minor);

const accountName = (tx) => {
	if (props.lockedAccountName) {
		return props.lockedAccountName;
	}
	if (props.lockedAccountId) {
		return tx.account_name || "N/A";
	}
	return tx.account_name || "N/A";
};

const emitAsync = (eventName, ...args) =>
	new Promise((resolve, reject) => {
		emit(eventName, ...args, resolve, reject);
	});

const isEditing = (tx) => editingId.value === tx.transaction_version_id;
const isSavingInline = (tx) => inlineSubmitting.value && isEditing(tx);

const populateInlineForm = (tx) => {
	inlineForm.transaction_date = tx.transaction_date || todayISO();
	inlineForm.account_id = props.lockedAccountId || tx.account_id || "";
	inlineForm.category_id = tx.category_id || "";
	inlineForm.memo = tx.memo || "";
	inlineForm.status = tx.status === "cleared" ? "cleared" : "pending";

	if (typeof tx.amount_minor === "number") {
		const fields = amountMinorToInlineFields(tx.amount_minor);
		inlineForm.inflow = fields.inflow;
		inlineForm.outflow = fields.outflow;
	} else {
		inlineForm.inflow = "";
		inlineForm.outflow = "";
	}

	inlineError.value = "";
	localError.value = "";
};

const handleRowClick = async (tx) => {
	if (inlineSubmitting.value || deletingIds.has(tx.transaction_version_id)) {
		return;
	}
	if (isEditing(tx)) {
		return;
	}
	editingId.value = tx.transaction_version_id;
	populateInlineForm(tx);
	await nextTick();
};

const cancelInlineEdit = () => {
	editingId.value = null;
	inlineError.value = "";
	localError.value = "";
};

const validateInlinePayload = () => {
	if (!isValidDateInput(inlineForm.transaction_date)) {
		inlineError.value = "Enter a valid date (YYYY-MM-DD).";
		return null;
	}
	if (!inlineForm.account_id || !inlineForm.category_id) {
		inlineError.value = "Account and category are required.";
		return null;
	}
	const amountResult = resolveInlineSignedAmountMinor(
		inlineForm.inflow,
		inlineForm.outflow,
	);
	if (amountResult.error) {
		inlineError.value = amountResult.error;
		return null;
	}
	return { signedAmount: amountResult.signedAmount };
};

const saveInlineEdit = async (tx) => {
	if (!tx || !isEditing(tx)) {
		return;
	}
	inlineError.value = "";
	localError.value = "";
	const validation = validateInlinePayload();
	if (!validation) {
		return;
	}
	if (!tx.concept_id) {
		inlineError.value = "Missing transaction id.";
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
		await emitAsync("update", payload);
		editingId.value = null;
	} catch (error) {
		inlineError.value = error?.message || "Failed to save changes.";
	} finally {
		inlineSubmitting.value = false;
	}
};

const toggleInlineStatus = () => {
	inlineForm.status = inlineForm.status === "cleared" ? "pending" : "cleared";
};

const toggleRowStatus = async (tx) => {
	if (!tx?.concept_id) {
		localError.value = "Missing transaction id.";
		return;
	}
	if (inlineSubmitting.value) {
		return;
	}

	const nextStatus = tx.status === "cleared" ? "pending" : "cleared";
	try {
		inlineSubmitting.value = true;
		await emitAsync("update", {
			concept_id: tx.concept_id,
			transaction_date: tx.transaction_date || todayISO(),
			account_id: tx.account_id,
			category_id: tx.category_id,
			memo: tx.memo || null,
			amount_minor: tx.amount_minor,
			status: nextStatus,
		});
	} catch (error) {
		localError.value = error?.message || "Failed to update status.";
	} finally {
		inlineSubmitting.value = false;
	}
};

const handleDelete = async (tx) => {
	if (!tx?.concept_id) {
		inlineError.value = "Missing transaction id.";
		return;
	}

	deletingIds.add(tx.transaction_version_id);
	localError.value = "";
	try {
		if (props.deleteAnimationMs > 0) {
			await new Promise((resolve) =>
				setTimeout(resolve, props.deleteAnimationMs),
			);
		}
		await emitAsync("delete", tx);
		editingId.value = null;
		// Keep the row collapsed until parent data removes it.
	} catch (error) {
		deletingIds.delete(tx.transaction_version_id);
		inlineError.value = error?.message || "Failed to delete transaction.";
		localError.value = inlineError.value;
	}
};

watch(
	() => props.transactions,
	(transactions) => {
		const present = new Set(
			(transactions ?? []).map((tx) => tx.transaction_version_id),
		);
		for (const id of Array.from(deletingIds)) {
			if (!present.has(id)) {
				deletingIds.delete(id);
			}
		}
		if (editingId.value && !present.has(editingId.value)) {
			editingId.value = null;
		}
	},
	{ immediate: true },
);

watch(
	() => inlineForm.inflow,
	(value) => {
		if (value && Number.parseFloat(value) !== 0) {
			inlineForm.outflow = "";
		}
	},
);

watch(
	() => inlineForm.outflow,
	(value) => {
		if (value && Number.parseFloat(value) !== 0) {
			inlineForm.inflow = "";
		}
	},
);

const handlePointerDownOutside = (event) => {
	if (!editingId.value) {
		return;
	}
	const wrapper = tableWrapper.value;
	if (!wrapper) {
		return;
	}
	if (wrapper.contains(event.target)) {
		return;
	}
	cancelInlineEdit();
};

onMounted(() => {
	document.addEventListener("pointerdown", handlePointerDownOutside, true);
});

onBeforeUnmount(() => {
	document.removeEventListener("pointerdown", handlePointerDownOutside, true);
});
</script>
