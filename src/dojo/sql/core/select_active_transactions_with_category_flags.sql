SELECT
    t.account_id,
    t.category_id,
    t.transaction_date,
    t.amount_minor,
    COALESCE(c.is_system, FALSE) AS is_system
FROM transactions AS t
INNER JOIN budget_categories AS c ON t.category_id = c.category_id
WHERE t.is_active = TRUE;
