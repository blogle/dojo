SELECT
    account_id,
    name,
    current_balance_minor
FROM accounts
WHERE is_active = TRUE
ORDER BY name;
