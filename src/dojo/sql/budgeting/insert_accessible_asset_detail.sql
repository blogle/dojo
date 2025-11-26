INSERT INTO accessible_asset_details (
    detail_id,
    account_id
)
SELECT
    $detail_id,
    $account_id
WHERE NOT EXISTS (
    SELECT 1 FROM accessible_asset_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
