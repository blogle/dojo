UPDATE budget_categories
SET
    name = $name,
    group_id = $group_id,
    is_active = $is_active,
    goal_type = $goal_type,
    goal_amount_minor = $goal_amount_minor,
    goal_target_date = $goal_target_date,
    goal_frequency = $goal_frequency,
    updated_at = CURRENT_TIMESTAMP
WHERE category_id = $category_id;
