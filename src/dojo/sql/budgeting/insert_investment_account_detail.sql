INSERT INTO investment_account_details (
    detail_id,
    account_id,
    risk_free_sweep_rate,
    is_self_directed,
    tax_classification
)
SELECT
    $detail_id,
    $account_id,
    $risk_free_sweep_rate,
    $is_self_directed,
    $tax_classification
WHERE NOT EXISTS (
    SELECT 1 FROM investment_account_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
