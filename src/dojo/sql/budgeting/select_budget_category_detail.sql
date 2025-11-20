SELECT
    c.category_id,
    c.group_id,
    c.name,
    c.is_active,
    c.created_at,
    c.updated_at,
    c.goal_type,
    c.goal_amount_minor,
    c.goal_target_date,
    c.goal_frequency,
    COALESCE(s.available_minor, 0) AS available_minor,
    COALESCE(s.activity_minor, 0) AS activity_minor,
    COALESCE(s.allocated_minor, 0) AS allocated_minor
FROM budget_categories AS c
LEFT JOIN budget_category_monthly_state AS s
    ON s.category_id = c.category_id
   AND s.month_start = ?
WHERE c.category_id = ?;
