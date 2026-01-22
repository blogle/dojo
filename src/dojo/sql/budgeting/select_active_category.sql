SELECT
    category_id,
    name,
    is_active,
    COALESCE(is_system, FALSE) AS is_system,
    COALESCE(allow_transactions, TRUE) AS allow_transactions,
    COALESCE(allow_allocations, TRUE) AS allow_allocations,
    COALESCE(is_envelope, TRUE) AS is_envelope,
    COALESCE(is_payment, FALSE) AS is_payment
FROM budget_categories
WHERE category_id = $category_id;
