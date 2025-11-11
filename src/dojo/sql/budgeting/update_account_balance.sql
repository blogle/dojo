UPDATE accounts
SET current_balance_minor = CASE
        WHEN account_type = 'liability' THEN current_balance_minor - ?
        ELSE current_balance_minor + ?
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE account_id = ?;
