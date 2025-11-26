SELECT
    group_id,
    name,
    sort_order,
    is_active,
    created_at,
    updated_at
FROM budget_category_groups
WHERE is_active = TRUE
ORDER BY sort_order ASC, name ASC;
