INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    recorded_at,
    valid_from,
    valid_to,
    is_active,
    source
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '9999-12-31 00:00:00', TRUE, ?);
