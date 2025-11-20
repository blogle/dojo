SELECT
    category_id,
    name,
    is_active,
    COALESCE(is_system, FALSE) AS is_system
FROM budget_categories
WHERE category_id = ?;
