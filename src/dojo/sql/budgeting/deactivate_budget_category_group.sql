UPDATE budget_category_groups
SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
WHERE group_id = $group_id;
