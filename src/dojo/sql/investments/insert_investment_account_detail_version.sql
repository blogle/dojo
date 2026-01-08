INSERT INTO investment_account_details (
    detail_id,
    account_id,
    risk_free_sweep_rate,
    manager,
    is_self_directed,
    tax_classification,
    uninvested_cash_minor,
    valid_from,
    valid_to,
    is_active,
    created_at,
    updated_at
)
VALUES (
    $detail_id,
    $account_id,
    $risk_free_sweep_rate,
    $manager,
    $is_self_directed,
    $tax_classification,
    $uninvested_cash_minor,
    $valid_from,
    $valid_to,
    TRUE,
    $created_at,
    $updated_at
);
