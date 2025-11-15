UPDATE budget_categories
SET
    is_active = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE category_id = ?;
