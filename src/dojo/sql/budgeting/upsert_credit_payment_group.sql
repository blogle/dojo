INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES (?, ?, ?)
ON CONFLICT (group_id) DO UPDATE
SET name = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE,
    updated_at = NOW();
