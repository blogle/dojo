UPDATE budget_category_groups
SET name = $name, sort_order = $sort_order, updated_at = CURRENT_TIMESTAMP
WHERE group_id = $group_id
RETURNING group_id, name, sort_order, is_active, created_at, updated_at;
