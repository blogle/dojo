<template>
  <section class="investments-holdings">
    <header class="investments-holdings__header">
      <div>
        <p class="investments-holdings__title">Holdings</p>
        <p class="u-muted u-small-note">Reconcile ticker, quantity, and cost basis.</p>
      </div>
      <button
        type="button"
        class="button button--secondary"
        data-testid="investment-add-position-toggle"
        @click="showForm = !showForm"
      >
        {{ showForm ? "Cancel" : "+ Add position" }}
      </button>
    </header>

    <form v-if="showForm" class="investments-holdings__form" @submit.prevent="addPosition">
      <label>
        Ticker
        <input v-model.trim="form.ticker" placeholder="AAPL" autocomplete="off" />
      </label>
      <label>
        Quantity
        <input v-model="form.quantity" inputmode="decimal" placeholder="10" />
      </label>
      <label>
        Avg cost
        <input v-model="form.avgCost" inputmode="decimal" placeholder="100.00" />
      </label>
      <label>
        Current price
        <input :value="currentPriceLabel" disabled />
      </label>
      <button class="button button--primary" type="submit" :disabled="pending">Save</button>
    </form>

    <BaseTable variant="investments" data-testid="investment-holdings-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th class="ledger-table__amount">Qty</th>
          <th class="ledger-table__amount">Price</th>
          <th class="ledger-table__amount">Avg cost</th>
          <th class="ledger-table__amount">Market value</th>
          <th class="ledger-table__amount">Return</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!positions.length">
          <td colspan="7" class="u-muted" style="padding: 1rem;">No holdings yet.</td>
        </tr>
        <tr
          v-for="position in positions"
          :key="position.ticker"
          class="investments-holdings__row"
        >
          <td>{{ position.ticker }}</td>
          <td class="ledger-table__amount">{{ formatQty(position.quantity) }}</td>
          <td class="ledger-table__amount">{{ formatMinor(position.price_minor) }}</td>
          <td class="ledger-table__amount">{{ formatAmount(position.avg_cost_minor) }}</td>
          <td class="ledger-table__amount">{{ formatAmount(position.market_value_minor) }}</td>
          <td class="ledger-table__amount" :class="gainClass(position.gain_minor)">
            {{ formatAmount(position.gain_minor) }}
          </td>
          <td class="ledger-table__amount">
            <button
              type="button"
              class="button button--tertiary"
              :disabled="pending"
              @click="removePosition(position.ticker)"
            >
              Remove
            </button>
          </td>
        </tr>
      </tbody>
    </BaseTable>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import BaseTable from "../BaseTable.vue";
import { dollarsToMinor, formatAmount } from "../../services/format.js";

const props = defineProps({
	positions: {
		type: Array,
		required: true,
	},
	pending: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["reconcile"]);

const showForm = ref(false);
const form = reactive({
	ticker: "",
	quantity: "",
	avgCost: "",
});

const formatQty = (value) => {
	if (value === undefined || value === null) {
		return "—";
	}
	const numeric = Number(value);
	if (Number.isNaN(numeric)) {
		return String(value);
	}
	return numeric.toLocaleString(undefined, { maximumFractionDigits: 6 });
};

const formatMinor = (value) =>
	value === undefined || value === null ? "—" : formatAmount(value);

const gainClass = (gainMinor) => {
	if (gainMinor === undefined || gainMinor === null) {
		return "";
	}
	return gainMinor >= 0
		? "investments-holdings__gain--up"
		: "investments-holdings__gain--down";
};

const currentPriceLabel = computed(() => {
	const ticker = form.ticker.trim().toUpperCase();
	if (!ticker) {
		return "—";
	}
	const match = props.positions.find((p) => p.ticker === ticker);
	if (!match) {
		return "—";
	}
	return formatMinor(match.price_minor);
});

const addPosition = async () => {
	if (props.pending) {
		return;
	}
	const ticker = form.ticker.trim().toUpperCase();
	const quantity = Number.parseFloat(form.quantity);
	const avgCostMinor = dollarsToMinor(form.avgCost);

	if (!ticker || Number.isNaN(quantity) || quantity <= 0) {
		return;
	}

	const next = [
		...props.positions.map((p) => ({
			ticker: p.ticker,
			quantity: p.quantity,
			avg_cost_minor: p.avg_cost_minor,
		})),
	];

	const existingIndex = next.findIndex((p) => p.ticker === ticker);
	if (existingIndex >= 0) {
		next[existingIndex] = { ticker, quantity, avg_cost_minor: avgCostMinor };
	} else {
		next.push({ ticker, quantity, avg_cost_minor: avgCostMinor });
	}

	emit("reconcile", {
		positions: next,
	});

	form.ticker = "";
	form.quantity = "";
	form.avgCost = "";
	showForm.value = false;
};

const removePosition = (ticker) => {
	if (props.pending) {
		return;
	}
	const next = props.positions
		.filter((p) => p.ticker !== ticker)
		.map((p) => ({
			ticker: p.ticker,
			quantity: p.quantity,
			avg_cost_minor: p.avg_cost_minor,
		}));

	emit("reconcile", {
		positions: next,
	});
};
</script>
