UPDATE accounts
SET
    is_active = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = ?;
