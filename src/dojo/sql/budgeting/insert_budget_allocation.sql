INSERT INTO budget_allocations (
    allocation_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo
) VALUES (
    $allocation_id,
    $allocation_date,
    $month_start,
    $from_category_id,
    $to_category_id,
    $amount_minor,
    $memo
);
