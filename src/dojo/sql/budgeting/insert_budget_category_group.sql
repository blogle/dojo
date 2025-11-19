INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES (?, ?, ?)
RETURNING group_id, name, sort_order, is_active, created_at, updated_at;
