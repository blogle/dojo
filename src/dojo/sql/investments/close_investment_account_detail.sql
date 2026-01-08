UPDATE investment_account_details
SET
    is_active = FALSE,
    valid_to = $valid_to,
    updated_at = $updated_at
WHERE
    detail_id = $detail_id
    AND is_active = TRUE;
