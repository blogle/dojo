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
    COALESCE(s.allocated_minor, 0) AS allocated_minor,
    COALESCE(prev.allocated_minor, 0) AS last_month_allocated_minor,
    COALESCE(prev.activity_minor, 0) AS last_month_activity_minor
FROM budget_categories AS c
LEFT JOIN budget_category_monthly_state AS s
    ON s.category_id = c.category_id
    AND s.month_start = ?
LEFT JOIN budget_category_monthly_state AS prev
    ON prev.category_id = c.category_id
    AND prev.month_start = ?
WHERE c.is_system IS NOT TRUE
ORDER BY c.created_at ASC;
