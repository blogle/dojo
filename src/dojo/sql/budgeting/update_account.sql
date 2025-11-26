UPDATE accounts
SET
    name = $name,
    account_type = $account_type,
    account_class = $account_class,
    account_role = $account_role,
    current_balance_minor = $current_balance_minor,
    currency = $currency,
    opened_on = $opened_on,
    is_active = $is_active,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = $account_id;
