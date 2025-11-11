SELECT
    category_id,
    name,
    is_active
FROM budget_categories
WHERE category_id = ?;
