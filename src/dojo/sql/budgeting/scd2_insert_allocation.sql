-- Insert a new version of a budget allocation
INSERT INTO budget_allocations (
    allocation_id,
    concept_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo,
    is_active,
    valid_from,
    valid_to,
    recorded_at
) VALUES (
    uuid(),
    $concept_id,
    $allocation_date,
    $month_start,
    $from_category_id,
    $to_category_id,
    $amount_minor,
    $memo,
    TRUE,
    current_timestamp,
    cast('9999-12-31 00:00:00' AS TIMESTAMP),
    current_timestamp
);
