SELECT
    category_id,
    name,
    is_active,
    created_at,
    updated_at
FROM budget_categories
WHERE category_id = ?;
