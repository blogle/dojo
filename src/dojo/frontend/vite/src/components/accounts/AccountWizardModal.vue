<template>
  <div
    v-if="open"
    class="modal-overlay is-visible"
    id="account-wizard-modal"
    style="display: flex;"
    @click.self="handleClose"
  >
    <div class="modal account-wizard" role="dialog" aria-modal="true">
      <header class="modal__header account-wizard__header">
        <div>
          <p class="stat-card__label">Account onboarding</p>
          <h2>{{ stepTitle }}</h2>
          <p class="u-muted u-small-note">{{ stepHint }}</p>
        </div>
        <button class="modal__close" type="button" :disabled="pending" @click="handleClose">
          ×
        </button>
      </header>

      <div class="modal__body">
        <datalist id="account-wizard-institutions">
          <option v-for="institution in institutionOptions" :key="institution" :value="institution"></option>
        </datalist>

        <section v-if="step === 1" class="account-wizard__step">
          <div class="account-wizard__type-grid">
            <button
              v-for="option in typeOptions"
              :key="option.id"
              type="button"
              class="account-wizard__type-card"
              :class="{ 'account-wizard__type-card--selected': selectedType === option.id }"
              @click="selectedType = option.id"
            >
              <strong>{{ option.label }}</strong>
              <span>{{ option.description }}</span>
            </button>
          </div>
        </section>

        <section v-else-if="step === 2" class="account-wizard__step">
          <form class="modal-form" @submit.prevent>
            <div class="form-panel__grid account-wizard__grid">
              <label class="form-panel__field account-wizard__field account-wizard__field--full">
                <span>Account name</span>
                <input v-model.trim="form.name" type="text" placeholder="e.g. Primary checking" required />
              </label>

              <label class="form-panel__field account-wizard__field">
                <span>Institution</span>
                <input
                  v-model.trim="form.institution_name"
                  type="text"
                  list="account-wizard-institutions"
                  placeholder="Optional"
                />
              </label>

              <label
                v-if="selectedSchema?.id === 'investment'"
                class="form-panel__field account-wizard__field"
              >
                <span>Tax classification</span>
                <select v-model="form.tax_classification" required>
                  <option value="" disabled>Select classification</option>
                  <option v-for="option in investmentTaxOptions" :key="option" :value="option">{{ option }}</option>
                </select>
              </label>

              <label
                v-if="selectedSchema?.id === 'loan'"
                class="form-panel__field account-wizard__field"
              >
                <span>Interest rate (APY %)</span>
                <input
                  v-model="form.interest_rate_apy"
                  type="number"
                  step="0.01"
                  inputmode="decimal"
                  placeholder="Optional"
                />
              </label>
            </div>

            <details v-if="selectedSchema" class="account-wizard__optional-details">
              <summary>Optional planning details</summary>

              <div class="form-panel__grid account-wizard__grid account-wizard__grid--optional">
                <template v-if="selectedSchema.id === 'cash'">
                  <label class="form-panel__field account-wizard__field">
                    <span>Interest rate (APY %)</span>
                    <input
                      v-model="form.interest_rate_apy"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>
                </template>

                <template v-else-if="selectedSchema.id === 'credit'">
                  <label class="form-panel__field account-wizard__field">
                    <span>Network</span>
                    <select v-model="form.card_type">
                      <option value="">Optional</option>
                      <option v-for="option in cardTypeOptions" :key="option" :value="option">{{ option }}</option>
                    </select>
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Purchase APR (%)</span>
                    <input v-model="form.apr" type="number" step="0.01" inputmode="decimal" placeholder="Optional" />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Cash advance APR (%)</span>
                    <input
                      v-model="form.cash_advance_apr"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>
                </template>

                <template v-else-if="selectedSchema.id === 'accessible'">
                  <label class="form-panel__field account-wizard__field">
                    <span>Interest rate (APY %)</span>
                    <input
                      v-model="form.interest_rate_apy"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Term end date</span>
                    <input v-model="form.term_end_date" type="date" />
                  </label>
                  <label class="account-wizard__checkbox-field account-wizard__field account-wizard__field--full">
                    <input v-model="form.early_withdrawal_penalty" type="checkbox" />
                    <div>
                      <span>Early withdrawal penalty</span>
                      <small class="u-muted">Use this for CDs or restricted savings products.</small>
                    </div>
                  </label>
                </template>

                <template v-else-if="selectedSchema.id === 'investment'">
                  <label class="account-wizard__checkbox-field account-wizard__field account-wizard__field--full">
                    <input v-model="form.is_self_directed" type="checkbox" />
                    <div>
                      <span>Self-directed</span>
                      <small class="u-muted">Check this if you choose the investments yourself.</small>
                    </div>
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Sweep fund rate (%)</span>
                    <input
                      v-model="form.risk_free_sweep_rate"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>
                </template>

                <template v-else-if="selectedSchema.id === 'loan'">
                  <label class="form-panel__field account-wizard__field">
                    <span>Original principal</span>
                    <input
                      v-model="form.initial_principal_input"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Loan start date</span>
                    <input v-model="form.loan_start_date" type="date" />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Original term (months)</span>
                    <input
                      v-model="form.original_term_months"
                      type="number"
                      min="1"
                      step="1"
                      inputmode="numeric"
                      placeholder="Optional"
                    />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Payment tracking</span>
                    <select v-model="form.payment_mode">
                      <option value="statement_principal">Statement principal</option>
                      <option value="split_payments">Split payments</option>
                    </select>
                  </label>
                  <label class="form-panel__field account-wizard__field account-wizard__field--full">
                    <span>Escrow or servicing notes</span>
                    <textarea
                      v-model.trim="form.mortgage_escrow_details"
                      rows="3"
                      placeholder="Optional tax, insurance, or servicing notes"
                    ></textarea>
                  </label>
                </template>

                <template v-else-if="selectedSchema.id === 'tangible'">
                  <label class="form-panel__field account-wizard__field">
                    <span>Acquisition date</span>
                    <input v-model="form.acquisition_date" type="date" />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Acquisition cost</span>
                    <input
                      v-model="form.acquisition_cost_input"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>
                </template>
              </div>
            </details>
          </form>
        </section>

        <section v-else-if="step === 3" class="account-wizard__step">
          <form class="modal-form" @submit.prevent>
            <div class="form-panel__grid account-wizard__grid">
              <label class="form-panel__field account-wizard__field">
                <span>As-of date</span>
                <input v-model="form.as_of_date" type="date" required />
              </label>

              <label
                v-if="selectedSchema && selectedSchema.id !== 'investment'"
                class="form-panel__field account-wizard__field"
              >
                <span>{{ selectedSchema.startingLabel }}</span>
                <input
                  v-model="form.starting_balance_input"
                  type="number"
                  step="0.01"
                  inputmode="decimal"
                  :placeholder="selectedSchema.startingPlaceholder || '0.00'"
                  required
                />
                <small v-if="selectedSchema.startingHelper" class="u-muted">{{ selectedSchema.startingHelper }}</small>
              </label>

              <template v-if="selectedSchema?.id === 'tangible'">
                <label class="form-panel__field account-wizard__field">
                  <span>Valuation source</span>
                  <input
                    v-model.trim="form.valuation_source"
                    type="text"
                    placeholder="Optional"
                  />
                </label>
                <label class="form-panel__field account-wizard__field account-wizard__field--full">
                  <span>Valuation note</span>
                  <textarea
                    v-model.trim="form.notes"
                    rows="3"
                    placeholder="Optional appraisal, comps, or estimate note"
                  ></textarea>
                </label>
              </template>
            </div>

            <template v-if="selectedSchema?.id === 'investment'">
              <div class="form-panel__grid account-wizard__grid account-wizard__grid--investment">
                <label class="form-panel__field account-wizard__field">
                  <span>Statement cash</span>
                  <input
                    v-model="form.statement_cash_input"
                    type="number"
                    step="0.01"
                    inputmode="decimal"
                    placeholder="0.00"
                  />
                </label>

                <div class="account-wizard__holding-metrics">
                  <div>
                    <span>Holdings value</span>
                    <strong>{{ formatAmount(holdingsValueMinor) }}</strong>
                  </div>
                  <div>
                    <span>Modeled opening value</span>
                    <strong>{{ formatAmount(investmentOpeningValueMinor) }}</strong>
                  </div>
                </div>
              </div>

              <div class="account-wizard__holdings-header">
                <div>
                  <p class="account-wizard__section-title">Holdings</p>
                  <p class="u-muted u-small-note">
                    Add each ticker once with total quantity and average cost basis.
                  </p>
                </div>
                <div class="account-wizard__holdings-actions">
                  <span v-if="quoteLookupPending" class="u-muted u-small-note">Updating prices...</span>
                  <button type="button" class="button button--secondary" @click="addHolding">
                    + Add holding
                  </button>
                </div>
              </div>

              <div v-if="!form.holdings.length" class="account-wizard__empty-state u-muted u-small-note">
                No holdings yet. Cash-only accounts are okay.
              </div>

              <div
                v-for="(holding, index) in form.holdings"
                :key="holding.id"
                class="account-wizard__holding-card"
              >
                <div class="account-wizard__holding-head">
                  <strong>{{ holding.ticker || `Holding ${index + 1}` }}</strong>
                  <button type="button" class="button button--tertiary" @click="removeHolding(index)">
                    Remove
                  </button>
                </div>

                <div class="account-wizard__holding-grid">
                  <label class="form-panel__field account-wizard__field">
                    <span>Ticker</span>
                    <input
                      v-model.trim="holding.ticker"
                      type="text"
                      placeholder="VTI"
                      @input="queueQuoteRefresh()"
                      @blur="queueQuoteRefresh({ immediate: true })"
                    />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Quantity</span>
                    <input
                      v-model="holding.quantity"
                      type="number"
                      step="0.0001"
                      inputmode="decimal"
                      placeholder="0"
                    />
                  </label>
                  <label class="form-panel__field account-wizard__field">
                    <span>Avg cost basis</span>
                    <input
                      v-model="holding.avg_cost_input"
                      type="number"
                      step="0.01"
                      inputmode="decimal"
                      placeholder="Optional"
                    />
                  </label>

                  <div class="account-wizard__holding-metric">
                    <span>Market price</span>
                    <strong>{{ holding.current_price_dollars ? formatAmount(dollarsToMinor(holding.current_price_dollars)) : '—' }}</strong>
                  </div>
                  <div class="account-wizard__holding-metric">
                    <span>Position value</span>
                    <strong>{{ formatAmount(holdingValueMinor(holding)) }}</strong>
                  </div>
                </div>
              </div>
            </template>
          </form>
        </section>

        <section v-else class="account-wizard__step">
          <div class="account-wizard__review-grid">
            <div class="account-wizard__review-card">
              <p class="account-wizard__section-title">Static details</p>
              <dl class="account-wizard__review-list">
                <div v-for="row in staticReviewRows" :key="row.label">
                  <dt>{{ row.label }}</dt>
                  <dd>{{ row.value }}</dd>
                </div>
              </dl>
            </div>

            <div class="account-wizard__review-card">
              <p class="account-wizard__section-title">Starting state</p>
              <dl class="account-wizard__review-list">
                <div v-for="row in startingReviewRows" :key="row.label">
                  <dt>{{ row.label }}</dt>
                  <dd>{{ row.value }}</dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        <p v-if="localError || errorMessage" class="form-panel__error" aria-live="polite">
          {{ localError || errorMessage }}
        </p>

        <div class="form-panel__actions form-panel__actions--split account-wizard__actions">
          <button type="button" class="button button--secondary" :disabled="pending" @click="backOrClose">
            {{ step === 1 ? 'Cancel' : 'Back' }}
          </button>
          <button
            v-if="step < 4"
            type="button"
            class="button button--primary"
            :disabled="pending"
            @click="goToNextStep"
          >
            Next
          </button>
          <button
            v-else
            type="button"
            class="button button--primary"
            :disabled="pending"
            @click="submit"
          >
            {{ pending ? 'Creating...' : submitLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { api } from "../../services/api.js";
import {
	dollarsToMinor,
	formatAmount,
	minorToDollars,
	todayISO,
} from "../../services/format.js";

const investmentTaxOptions = [
	"Taxable Brokerage",
	"Traditional IRA",
	"Roth IRA",
	"401k",
	"403b",
	"529",
	"HSA",
];

const cardTypeOptions = ["Visa", "Mastercard", "American Express", "Discover"];

const typeOptions = [
	{
		id: "cash",
		label: "Cash",
		description: "Checking and savings used inside the budget.",
		account_class: "cash",
		account_type: "asset",
		account_role: "on_budget",
		startingLabel: "Opening balance",
		startingHelper: "Use a signed value if the account is overdrawn.",
	},
	{
		id: "credit",
		label: "Credit card",
		description: "On-budget liabilities paid from your cash accounts.",
		account_class: "credit",
		account_type: "liability",
		account_role: "on_budget",
		startingLabel: "Amount owed",
		startingHelper: "Enter the current amount owed as a positive number.",
	},
	{
		id: "accessible",
		label: "Accessible asset",
		description: "Savings, CDs, and other tracking assets outside the budget.",
		account_class: "accessible",
		account_type: "asset",
		account_role: "tracking",
		startingLabel: "Opening balance",
	},
	{
		id: "investment",
		label: "Investment",
		description: "Brokerage, retirement, and HSA accounts with holdings.",
		account_class: "investment",
		account_type: "asset",
		account_role: "tracking",
	},
	{
		id: "loan",
		label: "Loan",
		description: "Mortgages, student loans, and other amortizing debt.",
		account_class: "loan",
		account_type: "liability",
		account_role: "tracking",
		startingLabel: "Current principal",
		startingHelper: "Enter the remaining principal as a positive number.",
	},
	{
		id: "tangible",
		label: "Tangible asset",
		description: "Homes, vehicles, and other physical assets.",
		account_class: "tangible",
		account_type: "asset",
		account_role: "tracking",
		startingLabel: "Current fair value",
	},
];

const props = defineProps({
	open: { type: Boolean, default: false },
	pending: { type: Boolean, default: false },
	errorMessage: { type: String, default: "" },
	submitLabel: { type: String, default: "Create account" },
	institutionOptions: { type: Array, default: () => [] },
	initialType: { type: String, default: "" },
	initialValues: { type: Object, default: null },
});

const emit = defineEmits(["close", "submit"]);

const step = ref(1);
const selectedType = ref("");
const localError = ref("");
const quoteLookupPending = ref(false);
let quoteRefreshTimeoutId = null;

const blankHolding = () => ({
	id: `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
	ticker: "",
	quantity: "",
	avg_cost_input: "",
	current_price_dollars: "",
});

const form = reactive({
	name: "",
	institution_name: "",
	interest_rate_apy: "",
	card_type: "",
	apr: "",
	cash_advance_apr: "",
	term_end_date: "",
	early_withdrawal_penalty: false,
	tax_classification: "",
	is_self_directed: false,
	risk_free_sweep_rate: "",
	initial_principal_input: "",
	mortgage_escrow_details: "",
	loan_start_date: "",
	original_term_months: "",
	payment_mode: "statement_principal",
	acquisition_date: "",
	acquisition_cost_input: "",
	as_of_date: todayISO(),
	starting_balance_input: "",
	statement_cash_input: "0.00",
	valuation_source: "",
	notes: "",
	holdings: [],
});

const selectedSchema = computed(
	() => typeOptions.find((option) => option.id === selectedType.value) || null,
);

const stepTitle = computed(() => {
	switch (step.value) {
		case 1:
			return "Select account type";
		case 2:
			return "Static details";
		case 3:
			return "Starting state";
		default:
			return "Review";
	}
});

const stepHint = computed(() => {
	switch (step.value) {
		case 1:
			return "Choose the account shape first so the rest of the form stays focused.";
		case 2:
			return "Capture identity and slow-changing details for this account.";
		case 3:
			return "Enter what was true on the creation or cutover date.";
		default:
			return "Review the account metadata and starting state before saving.";
	}
});

const statementCashMinor = computed(() =>
	Math.max(0, dollarsToMinor(form.statement_cash_input || "0")),
);

const holdingValueMinor = (holding) => {
	const quantity = Number.parseFloat(holding.quantity || "0");
	if (!Number.isFinite(quantity) || quantity <= 0) {
		return 0;
	}
	const priceMinor = holding.current_price_dollars
		? dollarsToMinor(holding.current_price_dollars)
		: 0;
	const fallbackMinor = holding.avg_cost_input
		? dollarsToMinor(holding.avg_cost_input)
		: 0;
	const unitMinor = priceMinor > 0 ? priceMinor : fallbackMinor;
	return Math.round(quantity * unitMinor);
};

const holdingsValueMinor = computed(() =>
	form.holdings.reduce((sum, holding) => sum + holdingValueMinor(holding), 0),
);

const investmentOpeningValueMinor = computed(
	() => statementCashMinor.value + holdingsValueMinor.value,
);

const resetForm = () => {
	step.value = 1;
	selectedType.value = props.initialType || "";
	localError.value = "";
	form.name = props.initialValues?.name || "";
	form.institution_name = props.initialValues?.institution_name || "";
	form.interest_rate_apy =
		props.initialValues?.interest_rate_apy?.toString() || "";
	form.card_type = props.initialValues?.card_type || "";
	form.apr = props.initialValues?.apr?.toString() || "";
	form.cash_advance_apr =
		props.initialValues?.cash_advance_apr?.toString() || "";
	form.term_end_date = props.initialValues?.term_end_date || "";
	form.early_withdrawal_penalty = Boolean(
		props.initialValues?.early_withdrawal_penalty,
	);
	form.tax_classification = props.initialValues?.tax_classification || "";
	form.is_self_directed = Boolean(props.initialValues?.is_self_directed);
	form.risk_free_sweep_rate =
		props.initialValues?.risk_free_sweep_rate?.toString() || "";
	form.initial_principal_input =
		props.initialValues?.initial_principal_minor !== undefined &&
		props.initialValues?.initial_principal_minor !== null
			? minorToDollars(props.initialValues.initial_principal_minor)
			: "";
	form.mortgage_escrow_details =
		props.initialValues?.mortgage_escrow_details || "";
	form.loan_start_date = props.initialValues?.loan_start_date || "";
	form.original_term_months =
		props.initialValues?.original_term_months?.toString() || "";
	form.payment_mode =
		props.initialValues?.payment_mode || "statement_principal";
	form.acquisition_date = props.initialValues?.acquisition_date || "";
	form.acquisition_cost_input =
		props.initialValues?.acquisition_cost_minor !== undefined &&
		props.initialValues?.acquisition_cost_minor !== null
			? minorToDollars(props.initialValues.acquisition_cost_minor)
			: "";
	form.as_of_date = props.initialValues?.as_of_date || todayISO();
	form.starting_balance_input =
		props.initialValues?.starting_balance_minor !== undefined &&
		props.initialValues?.starting_balance_minor !== null
			? minorToDollars(props.initialValues.starting_balance_minor)
			: "";
	form.statement_cash_input =
		props.initialValues?.statement_cash_minor !== undefined &&
		props.initialValues?.statement_cash_minor !== null
			? minorToDollars(props.initialValues.statement_cash_minor)
			: "0.00";
	form.valuation_source = props.initialValues?.valuation_source || "";
	form.notes = props.initialValues?.notes || "";
	form.holdings = Array.isArray(props.initialValues?.holdings)
		? props.initialValues.holdings.map((holding, index) => ({
				id: holding.id || `${index}_${Date.now().toString(36)}`,
				ticker: holding.ticker || "",
				quantity: holding.quantity?.toString() || "",
				avg_cost_input:
					holding.avg_cost_minor !== undefined &&
					holding.avg_cost_minor !== null
						? minorToDollars(holding.avg_cost_minor)
						: "",
				current_price_dollars:
					holding.current_price_minor !== undefined &&
					holding.current_price_minor !== null
						? minorToDollars(holding.current_price_minor)
						: "",
			}))
		: [];
};

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) {
			resetForm();
		}
	},
);

const hasText = (value) => String(value || "").trim().length > 0;

const validateStaticDetails = () => {
	if (!selectedSchema.value) {
		throw new Error("Choose an account type before continuing.");
	}
	if (!hasText(form.name)) {
		throw new Error("Enter an account name before continuing.");
	}
	if (
		selectedSchema.value.id === "investment" &&
		!hasText(form.tax_classification)
	) {
		throw new Error("Select a tax classification for the investment account.");
	}
};

const validateStartingState = async () => {
	if (!form.as_of_date) {
		throw new Error("Enter the as-of date before continuing.");
	}

	if (selectedSchema.value?.id === "investment") {
		await refreshHoldingQuotes();
		for (const holding of form.holdings) {
			const ticker = String(holding.ticker || "")
				.trim()
				.toUpperCase();
			const quantity = Number.parseFloat(holding.quantity || "0");
			const rowTouched = ticker || quantity || holding.avg_cost_input;
			if (!rowTouched) {
				continue;
			}
			if (!ticker || !Number.isFinite(quantity) || quantity <= 0) {
				throw new Error("Each holding needs a ticker and a positive quantity.");
			}
			if (holdingValueMinor(holding) <= 0) {
				throw new Error(
					`Add a cost basis or use a ticker with a market price for ${ticker}.`,
				);
			}
		}
		return;
	}

	if (!hasText(form.starting_balance_input)) {
		throw new Error("Enter the starting value before continuing.");
	}
};

const buildAccountData = () => {
	const schema = selectedSchema.value;
	return {
		name: form.name.trim(),
		account_type: schema.account_type,
		account_class: schema.account_class,
		account_role: schema.account_role,
		current_balance_minor: 0,
		currency: "USD",
		institution_name: form.institution_name.trim() || null,
		opened_on: form.as_of_date || null,
		interest_rate_apy: form.interest_rate_apy
			? Number(form.interest_rate_apy)
			: null,
		card_type: form.card_type || null,
		apr: form.apr ? Number(form.apr) : null,
		cash_advance_apr: form.cash_advance_apr
			? Number(form.cash_advance_apr)
			: null,
		term_end_date: form.term_end_date || null,
		early_withdrawal_penalty: Boolean(form.early_withdrawal_penalty),
		risk_free_sweep_rate: form.risk_free_sweep_rate
			? Number(form.risk_free_sweep_rate)
			: null,
		is_self_directed:
			schema.id === "investment" ? Boolean(form.is_self_directed) : null,
		tax_classification:
			schema.id === "investment"
				? form.tax_classification.trim() || null
				: null,
		initial_principal_minor: form.initial_principal_input
			? Math.abs(dollarsToMinor(form.initial_principal_input))
			: null,
		mortgage_escrow_details: form.mortgage_escrow_details.trim() || null,
		loan_start_date: form.loan_start_date || null,
		original_term_months: form.original_term_months
			? Number.parseInt(form.original_term_months, 10)
			: null,
		payment_mode: schema.id === "loan" ? form.payment_mode : null,
		asset_name: schema.id === "tangible" ? form.name.trim() : null,
		acquisition_cost_minor: form.acquisition_cost_input
			? Math.abs(dollarsToMinor(form.acquisition_cost_input))
			: null,
		acquisition_date: form.acquisition_date || null,
		valuation_source:
			schema.id === "tangible" ? form.valuation_source.trim() || null : null,
		notes: schema.id === "tangible" ? form.notes.trim() || null : null,
	};
};

const buildStartingState = () => {
	const schema = selectedSchema.value;
	if (schema.id === "investment") {
		return {
			as_of_date: form.as_of_date,
			opening_balance_minor: investmentOpeningValueMinor.value,
			reconcile_portfolio: {
				uninvested_cash_minor: statementCashMinor.value,
				positions: form.holdings
					.filter((holding) => hasText(holding.ticker))
					.map((holding) => ({
						ticker: holding.ticker.trim().toUpperCase(),
						quantity: Number.parseFloat(holding.quantity || "0"),
						avg_cost_minor: holding.avg_cost_input
							? Math.max(0, dollarsToMinor(holding.avg_cost_input))
							: 0,
					})),
			},
		};
	}

	const signedMinor = dollarsToMinor(form.starting_balance_input);
	const normalizedMinor =
		schema.id === "credit" || schema.id === "loan"
			? Math.abs(signedMinor)
			: signedMinor;

	return {
		as_of_date: form.as_of_date,
		opening_balance_minor: normalizedMinor,
		reconcile_portfolio: null,
	};
};

const staticReviewRows = computed(() => {
	if (!selectedSchema.value) {
		return [];
	}

	const rows = [
		{ label: "Type", value: selectedSchema.value.label },
		{ label: "Account name", value: form.name || "—" },
		{ label: "Institution", value: form.institution_name || "—" },
	];

	if (selectedSchema.value.id === "investment") {
		rows.push({
			label: "Tax classification",
			value: form.tax_classification || "—",
		});
		rows.push({
			label: "Self-directed",
			value: form.is_self_directed ? "Yes" : "No",
		});
		if (form.risk_free_sweep_rate) {
			rows.push({
				label: "Sweep fund rate",
				value: `${form.risk_free_sweep_rate}%`,
			});
		}
	}

	if (selectedSchema.value.id === "loan") {
		rows.push({
			label: "Interest rate",
			value: form.interest_rate_apy ? `${form.interest_rate_apy}%` : "—",
		});
		rows.push({
			label: "Original principal",
			value: form.initial_principal_input
				? formatAmount(dollarsToMinor(form.initial_principal_input))
				: "—",
		});
		rows.push({ label: "Loan start", value: form.loan_start_date || "—" });
		rows.push({
			label: "Original term",
			value: form.original_term_months || "—",
		});
		rows.push({
			label: "Payment tracking",
			value:
				form.payment_mode === "split_payments"
					? "Split payments"
					: "Statement principal",
		});
	}

	if (selectedSchema.value.id === "tangible") {
		rows.push({
			label: "Acquisition date",
			value: form.acquisition_date || "—",
		});
		rows.push({
			label: "Acquisition cost",
			value: form.acquisition_cost_input
				? formatAmount(dollarsToMinor(form.acquisition_cost_input))
				: "—",
		});
	}

	if (selectedSchema.value.id === "accessible") {
		rows.push({
			label: "Interest rate",
			value: form.interest_rate_apy ? `${form.interest_rate_apy}%` : "—",
		});
		rows.push({ label: "Term end", value: form.term_end_date || "—" });
		rows.push({
			label: "Early withdrawal penalty",
			value: form.early_withdrawal_penalty ? "Yes" : "No",
		});
	}

	if (selectedSchema.value.id === "cash" && form.interest_rate_apy) {
		rows.push({ label: "Interest rate", value: `${form.interest_rate_apy}%` });
	}

	if (selectedSchema.value.id === "credit") {
		rows.push({ label: "Network", value: form.card_type || "—" });
		rows.push({
			label: "Purchase APR",
			value: form.apr ? `${form.apr}%` : "—",
		});
		rows.push({
			label: "Cash advance APR",
			value: form.cash_advance_apr ? `${form.cash_advance_apr}%` : "—",
		});
	}

	return rows;
});

const startingReviewRows = computed(() => {
	if (!selectedSchema.value) {
		return [];
	}

	const rows = [{ label: "As-of date", value: form.as_of_date || "—" }];

	if (selectedSchema.value.id === "investment") {
		rows.push({
			label: "Statement cash",
			value: formatAmount(statementCashMinor.value),
		});
		rows.push({
			label: "Holdings count",
			value: String(
				form.holdings.filter((holding) => hasText(holding.ticker)).length,
			),
		});
		rows.push({
			label: "Modeled opening value",
			value: formatAmount(investmentOpeningValueMinor.value),
		});
		return rows;
	}

	rows.push({
		label: selectedSchema.value.startingLabel,
		value: hasText(form.starting_balance_input)
			? formatAmount(buildStartingState().opening_balance_minor)
			: "—",
	});

	if (selectedSchema.value.id === "tangible") {
		rows.push({
			label: "Valuation source",
			value: form.valuation_source || "—",
		});
		rows.push({ label: "Valuation note", value: form.notes || "—" });
	}

	return rows;
});

const addHolding = () => {
	form.holdings.push(blankHolding());
};

const removeHolding = (index) => {
	form.holdings.splice(index, 1);
	queueQuoteRefresh();
};

const refreshHoldingQuotes = async () => {
	const tickers = form.holdings
		.map((holding) =>
			String(holding.ticker || "")
				.trim()
				.toUpperCase(),
		)
		.filter(Boolean);
	if (!tickers.length) {
		return;
	}
	quoteLookupPending.value = true;
	try {
		const quotes = await api.investments.lookupQuotes(tickers);
		const byTicker = new Map(
			(quotes || []).map((quote) => [
				String(quote.ticker || "").toUpperCase(),
				quote,
			]),
		);
		for (const holding of form.holdings) {
			const ticker = String(holding.ticker || "")
				.trim()
				.toUpperCase();
			if (!ticker) {
				continue;
			}
			const quote = byTicker.get(ticker);
			if (quote?.price_minor !== undefined && quote?.price_minor !== null) {
				holding.current_price_dollars = minorToDollars(quote.price_minor);
			}
		}
	} finally {
		quoteLookupPending.value = false;
	}
};

const queueQuoteRefresh = ({ immediate = false } = {}) => {
	if (quoteRefreshTimeoutId !== null) {
		window.clearTimeout(quoteRefreshTimeoutId);
		quoteRefreshTimeoutId = null;
	}
	if (selectedSchema.value?.id !== "investment") {
		return;
	}
	if (immediate) {
		refreshHoldingQuotes().catch(() => {});
		return;
	}
	quoteRefreshTimeoutId = window.setTimeout(() => {
		quoteRefreshTimeoutId = null;
		refreshHoldingQuotes().catch(() => {});
	}, 300);
};

const handleClose = () => {
	localError.value = "";
	emit("close");
};

const backOrClose = () => {
	localError.value = "";
	if (step.value === 1) {
		handleClose();
		return;
	}
	step.value -= 1;
};

const goToNextStep = async () => {
	localError.value = "";
	try {
		if (step.value === 1 && !selectedSchema.value) {
			throw new Error("Choose an account type before continuing.");
		}
		if (step.value === 2) {
			validateStaticDetails();
		}
		if (step.value === 3) {
			await validateStartingState();
		}
		step.value += 1;
	} catch (error) {
		localError.value =
			error?.message || "Complete the current step before continuing.";
	}
};

const submit = async () => {
	localError.value = "";
	try {
		validateStaticDetails();
		await validateStartingState();
		emit("submit", {
			selectedType: selectedType.value,
			accountData: buildAccountData(),
			startingState: buildStartingState(),
		});
	} catch (error) {
		localError.value =
			error?.message || "Unable to submit the account right now.";
	}
};
</script>

<style scoped>
.account-wizard {
  width: min(860px, calc(100vw - 2rem));
}

.account-wizard__header {
  border-bottom: 1px solid var(--border);
}

.account-wizard__step {
  display: grid;
  gap: 1rem;
}

.account-wizard__type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.account-wizard__type-card {
  display: grid;
  gap: 0.35rem;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  text-align: left;
}

.account-wizard__type-card strong {
  font-size: 1rem;
}

.account-wizard__type-card span {
  color: var(--muted);
  line-height: 1.45;
}

.account-wizard__type-card--selected {
  border-color: var(--text);
  background: #f5f0e8;
}

.account-wizard__grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.account-wizard__field {
  display: grid;
  gap: 0.35rem;
}

.account-wizard__field--full {
  grid-column: 1 / -1;
}

.account-wizard__optional-details {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.9rem 1rem;
  background: #fcfbf8;
}

.account-wizard__optional-details summary {
  cursor: pointer;
  font-weight: 700;
  color: var(--text);
}

.account-wizard__grid--optional {
  margin-top: 1rem;
}

.account-wizard__checkbox-field {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: start;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
}

.account-wizard__checkbox-field span,
.account-wizard__checkbox-field small {
  display: block;
}

.account-wizard__grid--investment {
  margin-bottom: 1rem;
}

.account-wizard__holding-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  grid-column: 1 / -1;
}

.account-wizard__holding-metrics div,
.account-wizard__holding-metric {
  display: grid;
  gap: 0.2rem;
  padding: 0.85rem 0.95rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}

.account-wizard__holding-metrics span,
.account-wizard__holding-metric span {
  color: var(--muted);
  font-size: 0.85rem;
}

.account-wizard__holdings-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.account-wizard__holdings-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.account-wizard__section-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}

.account-wizard__empty-state {
  padding: 1rem;
  border: 1px dashed var(--border);
  border-radius: 8px;
  background: #fcfbf8;
}

.account-wizard__holding-card {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  margin-bottom: 0.85rem;
}

.account-wizard__holding-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.account-wizard__holding-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.75rem;
}

.account-wizard__review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.account-wizard__review-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  background: var(--surface);
}

.account-wizard__review-list {
  display: grid;
  gap: 0.8rem;
  margin: 0.85rem 0 0 0;
}

.account-wizard__review-list div {
  display: grid;
  gap: 0.2rem;
}

.account-wizard__review-list dt {
  color: var(--muted);
  font-size: 0.85rem;
}

.account-wizard__review-list dd {
  margin: 0;
  color: var(--text);
  font-weight: 600;
}

.account-wizard__actions {
  margin-top: 1.5rem;
}

@media (max-width: 760px) {
  .account-wizard {
    width: min(100vw - 1rem, 680px);
  }

  .account-wizard__type-grid,
  .account-wizard__grid,
  .account-wizard__review-grid,
  .account-wizard__holding-grid,
  .account-wizard__holding-metrics {
    grid-template-columns: 1fr;
  }

  .account-wizard__holdings-header,
  .account-wizard__holding-head,
  .account-wizard__holdings-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
