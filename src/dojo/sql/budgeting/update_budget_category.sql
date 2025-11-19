UPDATE budget_categories
SET
    name = ?,
    group_id = ?,
    is_active = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE category_id = ?;
