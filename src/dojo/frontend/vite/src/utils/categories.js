import { systemCategoryIds } from "../constants.js";

export const filterUserFacingCategories = (categories = []) =>
	categories.filter(
		(category) =>
			category &&
			category.is_active !== false &&
			!systemCategoryIds.has(category.category_id),
	);
