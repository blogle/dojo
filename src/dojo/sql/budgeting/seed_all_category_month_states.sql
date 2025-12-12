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
    $month_start,
    0,
    0,
    0,
    COALESCE(prev.available_minor, 0)
FROM budget_categories AS c
LEFT JOIN budget_category_monthly_state AS prev
    ON prev.category_id = c.category_id
    AND prev.month_start = $previous_month
WHERE c.is_system IS NOT TRUE
ON CONFLICT (category_id, month_start) DO NOTHING;
