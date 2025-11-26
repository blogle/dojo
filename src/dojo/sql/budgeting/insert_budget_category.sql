INSERT INTO budget_categories (
    category_id,
    group_id,
    name,
    is_active,
    goal_type,
    goal_amount_minor,
    goal_target_date,
    goal_frequency,
    created_at,
    updated_at
)
VALUES (
    $category_id,
    $group_id,
    $name,
    $is_active,
    $goal_type,
    $goal_amount_minor,
    $goal_target_date,
    $goal_frequency,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
