SELECT
    category_id,
    name,
    0 AS available_minor
FROM budget_categories
WHERE
    is_active = TRUE
    AND (
        COALESCE(allow_transactions, TRUE) = TRUE
        OR (
            $include_payment = TRUE
            AND COALESCE(is_payment, FALSE) = TRUE
        )
    )
ORDER BY name;
