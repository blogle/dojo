INSERT INTO accessible_asset_details (
    detail_id,
    account_id,
    term_end_date,
    interest_rate_apy,
    early_withdrawal_penalty
)
SELECT
    $detail_id,
    $account_id,
    $term_end_date,
    $interest_rate_apy,
    $early_withdrawal_penalty
WHERE NOT EXISTS (
    SELECT 1 FROM accessible_asset_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
