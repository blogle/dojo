INSERT INTO loan_account_details (
    detail_id,
    account_id,
    initial_principal_minor,
    interest_rate_apy,
    mortgage_escrow_details,
    loan_start_date,
    original_term_months,
    payment_mode
)
SELECT
    $detail_id,
    $account_id,
    $initial_principal_minor,
    $interest_rate_apy,
    $mortgage_escrow_details,
    $loan_start_date,
    $original_term_months,
    $payment_mode
WHERE NOT EXISTS (
    SELECT 1 FROM loan_account_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
