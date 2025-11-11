SELECT
    category_id,
    name,
    0 AS available_minor
FROM budget_categories
WHERE is_active = TRUE
ORDER BY name;
