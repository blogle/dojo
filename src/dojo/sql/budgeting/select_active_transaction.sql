SELECT
    transaction_version_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    status
FROM transactions
WHERE
    concept_id = $concept_id
    AND is_active = TRUE
ORDER BY recorded_at DESC
LIMIT 1;
