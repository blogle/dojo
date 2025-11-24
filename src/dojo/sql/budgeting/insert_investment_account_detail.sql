INSERT INTO investment_account_details (
    detail_id,
    account_id
)
SELECT ?, ?
WHERE NOT EXISTS (
    SELECT 1 FROM investment_account_details
    WHERE account_id = ?
      AND is_active = TRUE
);
