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
    $inflow_delta,
    0,
    $available_delta
)
ON CONFLICT (category_id, month_start) DO UPDATE
    SET
        inflow_minor = budget_category_monthly_state.inflow_minor + excluded.inflow_minor,
        available_minor = budget_category_monthly_state.available_minor + excluded.available_minor,
        updated_at = NOW();
