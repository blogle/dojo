INSERT INTO tangible_asset_details (
    detail_id,
    account_id,
    asset_name,
    acquisition_cost_minor,
    acquisition_date,
    valuation_source,
    notes
)
SELECT
    $detail_id,
    $account_id,
    $asset_name,
    $acquisition_cost_minor,
    $acquisition_date,
    $valuation_source,
    $notes
WHERE NOT EXISTS (
    SELECT 1 FROM tangible_asset_details
    WHERE
        account_id = $account_id
        AND is_active = TRUE
);
