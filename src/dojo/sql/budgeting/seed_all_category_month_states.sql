INSERT INTO budget_category_monthly_state (
    category_id,
    month_start,
    allocated_minor,
    inflow_minor,
    activity_minor,
    available_minor
)
SELECT
    c.category_id,
    $month_start AS month_start,
    0 AS allocated_minor,
    0 AS inflow_minor,
    0 AS activity_minor,
    COALESCE(prev.available_minor, 0) AS available_minor
FROM budget_categories AS c
LEFT JOIN budget_category_monthly_state AS prev
    ON
        c.category_id = prev.category_id
        AND prev.month_start = $previous_month
WHERE c.is_system IS NOT TRUE
ON CONFLICT (category_id, month_start) DO NOTHING;
