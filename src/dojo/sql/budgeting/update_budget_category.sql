UPDATE budget_categories
SET
    name = ?,
    group_id = ?,
    is_active = ?,
    goal_type = ?,
    goal_amount_minor = ?,
    goal_target_date = ?,
    goal_frequency = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE category_id = ?;
