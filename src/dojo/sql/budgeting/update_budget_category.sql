UPDATE budget_categories
SET
    name = ?,
    is_active = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE category_id = ?;
