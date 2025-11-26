SELECT
    group_id,
    name,
    sort_order,
    is_active,
    created_at,
    updated_at
FROM budget_category_groups
WHERE group_id = $group_id;
