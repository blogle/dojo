import { selectors } from "../../constants.js";
import { api } from "../../services/api.js";
import { populateSelect } from "../../services/dom.js";
import { store } from "../../store.js";
import { getCategoryOptions } from "../categories/utils.js";

const updateAccountSelects = () => {
	const state = store.getState();
	const sorted = [...state.reference.accounts].sort((a, b) =>
		a.name.localeCompare(b.name),
	);
	populateSelect(
		document.querySelector(selectors.transactionAccountSelect),
		sorted,
		{ valueKey: "account_id", labelKey: "name" },
		"Select account",
	);
	populateSelect(
		document.querySelector(selectors.transferSourceSelect),
		sorted,
		{ valueKey: "account_id", labelKey: "name" },
		"Select source",
	);
	populateSelect(
		document.querySelector(selectors.transferDestinationSelect),
		sorted,
		{ valueKey: "account_id", labelKey: "name" },
		"Select destination",
	);
};

const updateAllocationFromSelect = (userCategories) => {
	const fromSelect = document.querySelector(selectors.allocationFromSelect);
	if (!fromSelect) {
		return;
	}
	const previous = fromSelect.value;
	const fragment = document.createDocumentFragment();
	const defaultOption = document.createElement("option");
	defaultOption.value = "";
	defaultOption.textContent = "Ready to Assign";
	fragment.appendChild(defaultOption);
	userCategories.forEach((category) => {
		const option = document.createElement("option");
		option.value = category.category_id;
		option.textContent = category.name;
		fragment.appendChild(option);
	});
	fromSelect.innerHTML = "";
	fromSelect.appendChild(fragment);
	if (
		previous &&
		userCategories.some((category) => category.category_id === previous)
	) {
		fromSelect.value = previous;
	} else {
		fromSelect.value = "";
	}
};

const updateCategorySelects = () => {
	const userCategories = getCategoryOptions();
	const transactionCategories = getCategoryOptions({ includeSystem: true });
	populateSelect(
		document.querySelector(selectors.transactionCategorySelect),
		transactionCategories,
		{ valueKey: "category_id", labelKey: "name" },
		"Select category",
	);
	populateSelect(
		document.querySelector(selectors.transferCategorySelect),
		userCategories,
		{ valueKey: "category_id", labelKey: "name" },
		"Select category",
	);
	populateSelect(
		document.querySelector(selectors.allocationToSelect),
		userCategories,
		{ valueKey: "category_id", labelKey: "name" },
		"Select category",
	);
	updateAllocationFromSelect(userCategories);
};

export const loadReferenceData = async () => {
	try {
		const reference = await api.reference.load();
		store.setState((prev) => ({
			...prev,
			reference: {
				accounts: reference?.accounts ?? [],
				categories: reference?.categories ?? [],
			},
		}));
		updateAccountSelects();
		updateCategorySelects();
	} catch (error) {
		console.error("Failed to load reference data", error);
	}
};

export const refreshSelectOptions = () => {
	updateAccountSelects();
	updateCategorySelects();
};
