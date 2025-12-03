import { store } from "../../store.js";
import { SPECIAL_CATEGORY_LABELS, systemCategoryIds } from "../../constants.js";

export const filterUserFacingCategories = (categories = []) =>
	categories.filter(
		(category) =>
			category &&
			category.is_active !== false &&
			!systemCategoryIds.has(category.category_id),
	);

export const getCategoryOptions = ({ includeSystem = false } = {}) => {
	const state = store.getState();
	const merged = new Map();
	const reference = Array.isArray(state.reference.categories)
		? state.reference.categories
		: [];
	const budgeted = Array.isArray(state.budgets.rawCategories)
		? state.budgets.rawCategories
		: [];
	reference.forEach((category) => {
		if (!category || !category.category_id) {
			return;
		}
		merged.set(category.category_id, category);
	});
	budgeted.forEach((category) => {
		if (!category || !category.category_id) {
			return;
		}
		const existing = merged.get(category.category_id) || {};
		merged.set(category.category_id, { ...existing, ...category });
	});
	return Array.from(merged.values())
		.filter((category) => {
			if (!category) {
				return false;
			}
			const isSystem = systemCategoryIds.has(category.category_id);
			if (isSystem) {
				return includeSystem;
			}
			return category.is_active !== false;
		})
		.map((category) => {
			if (!category) {
				return category;
			}
			if (systemCategoryIds.has(category.category_id)) {
				const label =
					SPECIAL_CATEGORY_LABELS[category.category_id] || category.name;
				if (label && label !== category.name) {
					return { ...category, name: label };
				}
			}
			return category;
		})
		.sort((a, b) => a.name.localeCompare(b.name));
};

export const findBudgetCategory = (
	categoryId,
	{ includeHidden = false } = {},
) => {
	if (!categoryId) {
		return null;
	}
	const state = store.getState();
	const source =
		includeHidden && state.budgets.rawCategories?.length
			? state.budgets.rawCategories
			: state.budgets.categories;
	return source.find((category) => category.category_id === categoryId) || null;
};

export const getCategoryAvailableMinor = (categoryId) => {
	const category = findBudgetCategory(categoryId);
	return category ? (category.available_minor ?? 0) : 0;
};

export const getCategoryDisplayName = (categoryId) => {
	if (!categoryId) {
		return "Ready to Assign";
	}
	if (SPECIAL_CATEGORY_LABELS[categoryId]) {
		return SPECIAL_CATEGORY_LABELS[categoryId];
	}
	const state = store.getState();
	const category =
		findBudgetCategory(categoryId, { includeHidden: true }) ||
		state.reference.categories.find((cat) => cat.category_id === categoryId);
	return category ? category.name : categoryId;
};
