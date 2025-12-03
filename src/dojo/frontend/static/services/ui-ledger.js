import { minorToDollars } from "./format.js";
import { populateSelect } from "./dom.js";

export const renderMoneyInput = (valueMinor, name) => {
	const dollars = valueMinor ? minorToDollars(Math.abs(valueMinor)) : "";
	return `<input type="number" step="0.01" name="${name}" value="${dollars}" class="table-input money" />`;
};

export const renderDateInput = (isoDate, name) => {
	return `<input type="date" name="${name}" value="${isoDate || ""}" class="table-input" />`;
};

export const renderTextInput = (value, name, placeholder = "") => {
	return `<input type="text" name="${name}" value="${value || ""}" placeholder="${placeholder}" class="table-input" />`;
};

/**
 * Transforms a static row into an editable row based on config.
 * @param {HTMLElement} row - The TR element
 * @param {Object} data - The raw data object for this row
 * @param {Array} config - Definition of columns
 */
export const makeRowEditable = (row, data, config) => {
	row.classList.add("is-editing");
	row.innerHTML = ""; // Clear content

	config.forEach((col) => {
		const td = document.createElement("td");

		if (col.class) {
			td.className = col.class;
		}

		if (col.type === "money") {
			let val = data[col.key];
			if (col.getValue) {
				val = col.getValue(data);
			}
			td.innerHTML = renderMoneyInput(val, col.name);
			const input = td.querySelector("input");
			if (col.attrs) {
				Object.entries(col.attrs).forEach(([k, v]) => {
					input.setAttribute(k, v);
				});
			}
		} else if (col.type === "date") {
			            td.innerHTML = renderDateInput(data[col.key], col.name);
			            const input = td.querySelector("input");
			            if (col.attrs) {
			                Object.entries(col.attrs).forEach(([k, v]) => {
			                    input.setAttribute(k, v);
			                });
			            }		} else if (col.type === "select") {
			const select = document.createElement("select");
			select.name = col.name;
			select.classList.add("table-input");
			// Populate
			if (col.options) {
				populateSelect(
					select,
					col.options,
					{
						valueKey: col.valueKey || "value",
						labelKey: col.labelKey || "label",
					},
					col.placeholder,
				);
			}
			select.value = data[col.key] || "";

			if (col.attrs) {
				Object.entries(col.attrs).forEach(([k, v]) => {
					select.setAttribute(k, v);
				});
			}
			td.appendChild(select);
		} else if (col.type === "text") {
			td.innerHTML = renderTextInput(data[col.key], col.name, col.placeholder);
			const input = td.querySelector("input");
			if (col.attrs) {
				Object.entries(col.attrs).forEach(([k, v]) => {
					input.setAttribute(k, v);
				});
			}
		} else if (col.type === "custom") {
			td.innerHTML = col.render(data);
		} else if (col.type === "html") {
			td.innerHTML = col.html;
		}

		row.appendChild(td);
	});

	// Focus first input
	const firstInput = row.querySelector("input, select");
	if (firstInput) firstInput.focus();
};
