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
    recorded_at
) VALUES (
    $allocation_id,
    $allocation_id, -- concept_id defaults to allocation_id for new entries
    $allocation_date,
    $month_start,
    $from_category_id,
    $to_category_id,
    $amount_minor,
    $memo,
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
