INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    status,
    recorded_at,
    valid_from,
    valid_to,
    is_active,
    source
)
VALUES (
    $transaction_version_id,
    $concept_id,
    $account_id,
    $category_id,
    $transaction_date,
    $amount_minor,
    $memo,
    $status,
    $recorded_at,
    $valid_from,
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    $source
);
