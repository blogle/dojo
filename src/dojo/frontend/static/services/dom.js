export const qs = (selector, root = document) => root.querySelector(selector);
export const qsa = (selector, root = document) =>
	Array.from(root.querySelectorAll(selector));

export const populateSelect = (
	selectEl,
	items,
	{ valueKey, labelKey },
	placeholder,
) => {
	if (!selectEl) {
		return;
	}
	const previous = selectEl.value;
	const fragment = document.createDocumentFragment();
	if (placeholder) {
		const option = document.createElement("option");
		option.value = "";
		option.disabled = true;
		option.selected = !previous || previous === "";
		option.textContent = placeholder;
		fragment.appendChild(option);
	}
	items.forEach((item) => {
		const option = document.createElement("option");
		option.value = item[valueKey];
		option.textContent = item[labelKey];
		fragment.appendChild(option);
	});
	selectEl.innerHTML = "";
	selectEl.appendChild(fragment);
	if (items.some((item) => item[valueKey] === previous)) {
		selectEl.value = previous;
	}
};

export const setFormError = (element, message) => {
	if (!element) {
		return;
	}
	element.textContent = message || "";
};

export const setButtonBusy = (button, busy) => {
	if (!button) {
		return;
	}
	button.disabled = Boolean(busy);
	button.setAttribute("aria-busy", busy ? "true" : "false");
};
