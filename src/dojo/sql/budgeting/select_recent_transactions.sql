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
JOIN accounts AS a ON a.account_id = t.account_id
JOIN budget_categories AS c ON c.category_id = t.category_id
WHERE t.is_active = TRUE
ORDER BY t.recorded_at DESC
LIMIT ?;
