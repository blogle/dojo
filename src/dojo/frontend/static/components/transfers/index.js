import { selectors } from "../../constants.js";
import { api } from "../../services/api.js";
import { setButtonBusy, setFormError } from "../../services/dom.js";
import { dollarsToMinor, todayISO } from "../../services/format.js";
import { store } from "../../store.js";
import { refreshSelectOptions } from "../reference/index.js";
import { showToast } from "../toast.js";

let refreshTransactions = async () => {};
let refreshAccountsPage = async () => {};
let refreshBudgetsData = async () => {};
let renderBudgetsPage = () => {};

const validateTransferForm = () => {
	const form = document.querySelector(selectors.transferForm);
	if (!form) {
		return false;
	}
	const state = store.getState();
	const sourceSelect = document.querySelector(selectors.transferSourceSelect);
	const destinationSelect = document.querySelector(
		selectors.transferDestinationSelect,
	);
	const categorySelect = document.querySelector(
		selectors.transferCategorySelect,
	);
	const amountInput = form.querySelector("input[name='amount']");
	const source = sourceSelect?.value;
	const destination = destinationSelect?.value;
	const categoryId = categorySelect?.value;
	const amountMinor = Math.abs(dollarsToMinor(amountInput?.value));
	const sourceHelper = form.querySelector('[data-validation="source"]');
	const destinationHelper = form.querySelector(
		'[data-validation="destination"]',
	);
	const identical = source && destination && source === destination;
	if (sourceHelper) {
		sourceHelper.textContent = identical
			? "Source and destination must differ."
			: "";
	}
	if (destinationHelper) {
		destinationHelper.textContent = identical
			? "Source and destination must differ."
			: "";
	}
	const valid = Boolean(
		source && destination && categoryId && !identical && amountMinor > 0,
	);
	const submitButton = document.querySelector(selectors.transferSubmit);
	if (submitButton) {
		submitButton.disabled = !valid || state.forms.transfer.submitting;
	}
	return valid;
};

const handleTransferSubmit = async (event) => {
	event.preventDefault();
	if (!validateTransferForm() || store.getState().forms.transfer.submitting) {
		return;
	}
	const form = event.currentTarget;
	const errorEl = document.querySelector(selectors.transferError);
	setFormError(errorEl, "");
	const formData = new FormData(form);
	const payload = {
		source_account_id: formData.get("source_account_id"),
		destination_account_id: formData.get("destination_account_id"),
		category_id: formData.get("category_id"),
		transaction_date: formData.get("transaction_date") || todayISO(),
		memo: (formData.get("memo") || "").toString().trim() || null,
		amount_minor: Math.abs(dollarsToMinor(formData.get("amount"))),
	};
	const submitButton = document.querySelector(selectors.transferSubmit);
	try {
		store.setState((prev) => ({
			...prev,
			forms: {
				...prev.forms,
				transfer: { ...prev.forms.transfer, submitting: true },
			},
		}));
		setButtonBusy(submitButton, true);
		const response = await api.transfers.create(payload);
		const amountInput = form.querySelector("input[name='amount']");
		if (amountInput) {
			amountInput.value = "";
		}
		const memoInput = form.querySelector("input[name='memo']");
		if (memoInput) {
			memoInput.value = "";
		}
		setFormError(errorEl, "");
		await Promise.all([
			refreshTransactions(),
			refreshAccountsPage(),
			refreshBudgetsData(),
		]);
		renderBudgetsPage();
		refreshSelectOptions();
		showToast(
			`Transfer ${response.concept_id} posted (${response.budget_leg.transaction_version_id} & ${response.transfer_leg.transaction_version_id})`,
		);
	} catch (error) {
		console.error(error);
		setFormError(errorEl, error.message || "Transfer failed.");
	} finally {
		store.setState((prev) => ({
			...prev,
			forms: {
				...prev.forms,
				transfer: { ...prev.forms.transfer, submitting: false },
			},
		}));
		setButtonBusy(submitButton, false);
		validateTransferForm();
	}
};

export const initTransfers = ({
	onTransactionsRefresh,
	onAccountsRefresh,
	onBudgetsRefresh,
	onBudgetsRender,
} = {}) => {
	refreshTransactions = onTransactionsRefresh || (() => Promise.resolve());
	refreshAccountsPage = onAccountsRefresh || (() => Promise.resolve());
	refreshBudgetsData = onBudgetsRefresh || (() => Promise.resolve());
	renderBudgetsPage = onBudgetsRender || (() => {});

	const form = document.querySelector(selectors.transferForm);
	if (!form) {
		return;
	}
	const dateInput = form.querySelector("input[name='transaction_date']");
	if (dateInput) {
		dateInput.value = todayISO();
	}
	form.addEventListener("submit", handleTransferSubmit);
	[
		selectors.transferSourceSelect,
		selectors.transferDestinationSelect,
		selectors.transferCategorySelect,
	].forEach((selector) => {
		document
			.querySelector(selector)
			?.addEventListener("change", validateTransferForm);
	});
	form
		.querySelector("input[name='amount']")
		?.addEventListener("input", validateTransferForm);
	validateTransferForm();
};
