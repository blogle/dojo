SELECT
    account_id,
    current_balance_minor
FROM accounts
WHERE
    account_id = $account_id
    AND is_active = TRUE
    AND account_class = 'investment';
