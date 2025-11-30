-- Insert a new version of a transaction
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
    uuid(),
    $concept_id,
    $account_id,
    $category_id,
    $transaction_date,
    $amount_minor,
    $memo,
    'pending', -- Reset status on edit
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    CAST('9999-12-31 00:00:00' AS TIMESTAMP),
    TRUE,
    'user_edit'
);
