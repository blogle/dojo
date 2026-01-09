SELECT
    a.account_id,
    a.name,
    a.account_type,
    a.account_class,
    a.account_role,
    a.current_balance_minor,
    a.currency,
    a.institution_name,
    a.opened_on,
    a.is_active,
    cash.interest_rate_apy AS cash_interest_rate_apy,
    accessible.term_end_date AS accessible_term_end_date,
    accessible.interest_rate_apy AS accessible_interest_rate_apy,
    accessible.early_withdrawal_penalty AS accessible_early_withdrawal_penalty,
    credit.apr AS credit_apr,
    credit.card_type AS credit_card_type,
    credit.cash_advance_apr AS credit_cash_advance_apr,
    loan.initial_principal_minor AS loan_initial_principal_minor,
    loan.interest_rate_apy AS loan_interest_rate_apy,
    loan.mortgage_escrow_details AS loan_mortgage_escrow_details,
    tangible.asset_name AS tangible_asset_name,
    tangible.acquisition_cost_minor AS tangible_acquisition_cost_minor,
    investment.risk_free_sweep_rate AS investment_risk_free_sweep_rate,
    investment.is_self_directed AS investment_is_self_directed,
    investment.tax_classification AS investment_tax_classification
FROM accounts AS a
LEFT JOIN cash_account_details AS cash
    ON a.account_id = cash.account_id
    AND cash.is_active = TRUE
LEFT JOIN accessible_asset_details AS accessible
    ON a.account_id = accessible.account_id
    AND accessible.is_active = TRUE
LEFT JOIN credit_account_details AS credit
    ON a.account_id = credit.account_id
    AND credit.is_active = TRUE
LEFT JOIN loan_account_details AS loan
    ON a.account_id = loan.account_id
    AND loan.is_active = TRUE
LEFT JOIN tangible_asset_details AS tangible
    ON a.account_id = tangible.account_id
    AND tangible.is_active = TRUE
LEFT JOIN investment_account_details AS investment
    ON a.account_id = investment.account_id
    AND investment.is_active = TRUE
WHERE
    a.account_id = $account_id
    AND a.is_active = TRUE;
