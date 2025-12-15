INSERT INTO credit_account_details (
    detail_id,
    account_id,
    apr,
    card_type,
    cash_advance_apr
)
SELECT
    $detail_id,
    $account_id,
    $apr,
    $card_type,
    $cash_advance_apr
WHERE NOT EXISTS (
    SELECT 1 FROM credit_account_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
