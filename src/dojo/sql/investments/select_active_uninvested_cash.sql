SELECT uninvested_cash_minor
FROM investment_account_details
WHERE
    account_id = $account_id
    AND is_active = TRUE;
