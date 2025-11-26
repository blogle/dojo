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
    $allocated_delta,
    0,
    0,
    $available_delta
)
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        allocated_minor = budget_category_monthly_state.allocated_minor + excluded.allocated_minor,
        available_minor = budget_category_monthly_state.available_minor + excluded.available_minor,
        updated_at = NOW();
