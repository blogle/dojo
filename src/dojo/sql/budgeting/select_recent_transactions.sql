SELECT
    t.transaction_version_id,
    t.concept_id,
    t.transaction_date,
    t.account_id,
    a.name AS account_name,
    t.category_id,
    c.name AS category_name,
    t.amount_minor,
    t.status,
    t.memo,
    t.recorded_at
FROM transactions AS t
INNER JOIN accounts AS a ON t.account_id = a.account_id
INNER JOIN budget_categories AS c ON t.category_id = c.category_id
WHERE t.is_active = TRUE
ORDER BY t.recorded_at DESC
LIMIT $limit_count;
