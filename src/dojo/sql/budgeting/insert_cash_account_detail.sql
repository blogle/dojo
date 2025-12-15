INSERT INTO cash_account_details (
    detail_id,
    account_id,
    interest_rate_apy
)
SELECT
    $detail_id,
    $account_id,
    $interest_rate_apy
WHERE NOT EXISTS (
    SELECT 1 FROM cash_account_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
