WITH asset_totals AS (
    SELECT COALESCE(SUM(current_balance_minor), 0) AS assets_minor
    FROM accounts
    WHERE is_active = TRUE
      AND account_type = 'asset'
),
liability_totals AS (
    SELECT COALESCE(SUM(current_balance_minor), 0) AS liabilities_minor
    FROM accounts
    WHERE is_active = TRUE
      AND account_type = 'liability'
),
position_totals AS (
    SELECT COALESCE(SUM(market_value_minor), 0) AS positions_minor
    FROM positions
    WHERE is_active = TRUE
)
SELECT
    asset_totals.assets_minor,
    liability_totals.liabilities_minor,
    position_totals.positions_minor,
    asset_totals.assets_minor
        - liability_totals.liabilities_minor
        + position_totals.positions_minor AS net_worth_minor
FROM asset_totals
CROSS JOIN liability_totals
CROSS JOIN position_totals;
