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
WHERE
    t.is_active = TRUE
    AND t.account_id = $account_id
    AND ($start_date IS NULL OR t.transaction_date >= $start_date)
    AND ($end_date IS NULL OR t.transaction_date <= $end_date)
    AND ($status = 'all' OR t.status = 'cleared')
ORDER BY t.transaction_date DESC, t.recorded_at DESC
LIMIT $limit_count;
