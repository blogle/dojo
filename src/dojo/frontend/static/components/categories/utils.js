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
	const referenceCategories = Array.isArray(state.reference.categories)
		? state.reference.categories
		: [];
	const budgetCategories = Array.isArray(state.budgets.rawCategories)
		? state.budgets.rawCategories
		: [];
	const groups = Array.isArray(state.budgets.groups) ? state.budgets.groups : [];
	const groupIds = new Set(groups.map((group) => group.group_id));

	const applyLabel = (category) => {
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
	};

	const systemCategories = includeSystem
		? referenceCategories.filter((category) =>
				category && systemCategoryIds.has(category.category_id),
			)
		: [];

	const userSource = budgetCategories.length
		? budgetCategories
		: referenceCategories.filter(
				(category) => category && !systemCategoryIds.has(category.category_id),
			);

	const userCategories = filterUserFacingCategories(userSource).filter(
		(category) => category && !groupIds.has(category.category_id),
	);

	if (!budgetCategories.length) {
		const orderedUsers = userCategories
			.slice()
			.sort((a, b) => a.name.localeCompare(b.name))
			.map(applyLabel);
		const orderedSystems = systemCategories
			.map(applyLabel)
			.sort((a, b) => a.name.localeCompare(b.name));
		return includeSystem ? [...orderedSystems, ...orderedUsers] : orderedUsers;
	}

	const buckets = new Map();
	const UNCATEGORIZED_KEY = "uncategorized";
	userCategories.forEach((category) => {
		const groupId = category.group_id || UNCATEGORIZED_KEY;
		if (!buckets.has(groupId)) {
			buckets.set(groupId, []);
		}
		buckets.get(groupId).push(category);
	});

	const orderedUsers = [];
	groups.forEach((group) => {
		const bucket = buckets.get(group.group_id) || [];
		bucket.forEach((category) => orderedUsers.push(applyLabel(category)));
		buckets.delete(group.group_id);
	});

	buckets.forEach((bucket, key) => {
		if (key === UNCATEGORIZED_KEY) {
			return;
		}
		bucket.forEach((category) => orderedUsers.push(applyLabel(category)));
	});

	(buckets.get(UNCATEGORIZED_KEY) || []).forEach((category) =>
		orderedUsers.push(applyLabel(category)),
	);

	const orderedSystems = systemCategories
		.map(applyLabel)
		.sort((a, b) => a.name.localeCompare(b.name));

	return includeSystem ? [...orderedSystems, ...orderedUsers] : orderedUsers;
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
