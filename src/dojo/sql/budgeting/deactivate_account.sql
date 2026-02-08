UPDATE accounts
SET
    is_active = FALSE,
    include_in_net_worth = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = $account_id;
