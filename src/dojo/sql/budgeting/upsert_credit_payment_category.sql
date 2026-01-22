INSERT INTO budget_categories (
    category_id,
    group_id,
    name,
    is_active,
    is_system,
    allow_transactions,
    allow_allocations,
    is_envelope,
    is_payment
)
VALUES (
    $category_id,
    $group_id,
    $name,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    TRUE,
    TRUE
)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        group_id = excluded.group_id,
        is_active = TRUE,
        is_system = FALSE,
        allow_transactions = FALSE,
        allow_allocations = TRUE,
        is_envelope = TRUE,
        is_payment = TRUE,
        updated_at = NOW();
