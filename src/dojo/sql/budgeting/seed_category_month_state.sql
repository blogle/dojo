INSERT INTO budget_category_monthly_state (
    category_id,
    month_start,
    allocated_minor,
    inflow_minor,
    activity_minor,
    available_minor
)
VALUES (
    $category_id,
    $month_start,
    0,
    0,
    0,
    COALESCE(
        (
            SELECT available_minor
            FROM budget_category_monthly_state
            WHERE category_id = $category_id
              AND month_start = $previous_month
        ),
        0
    )
)
ON CONFLICT (category_id, month_start) DO NOTHING;
