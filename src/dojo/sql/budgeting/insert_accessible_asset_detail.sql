INSERT INTO accessible_asset_details (
    detail_id,
    account_id
)
SELECT ?, ?
WHERE NOT EXISTS (
    SELECT 1 FROM accessible_asset_details
    WHERE account_id = ?
      AND is_active = TRUE
);
