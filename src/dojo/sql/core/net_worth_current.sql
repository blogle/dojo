WITH asset_totals AS (
    SELECT COALESCE(SUM(current_balance_minor), 0) AS assets_minor
    FROM accounts
    WHERE
        is_active = TRUE
        AND account_type = 'asset'
        AND account_class != 'investment'
),

liability_totals AS (
    SELECT COALESCE(SUM(current_balance_minor), 0) AS liabilities_minor
    FROM accounts
    WHERE
        is_active = TRUE
        AND account_type = 'liability'
),

investment_accounts AS (
    SELECT
        a.account_id,
        a.current_balance_minor AS ledger_cash_minor
    FROM accounts AS a
    WHERE
        a.is_active = TRUE
        AND a.account_type = 'asset'
        AND a.account_class = 'investment'
),

investment_cash_by_account AS (
    SELECT
        ia.account_id,
        COALESCE(iad.uninvested_cash_minor, 0) AS uninvested_cash_minor
    FROM investment_accounts AS ia
    LEFT JOIN investment_account_details AS iad
        ON
            ia.account_id = iad.account_id
            AND iad.is_active = TRUE
),

latest_prices AS (
    SELECT
        mp.security_id,
        mp.close_minor
    FROM market_prices AS mp
    QUALIFY
        ROW_NUMBER() OVER (
            PARTITION BY mp.security_id
            ORDER BY mp.market_date DESC, mp.recorded_at DESC
        ) = 1
),

investment_holdings_by_account AS (
    SELECT
        p.account_id,
        COALESCE(
            SUM(CAST(ROUND(p.quantity * COALESCE(lp.close_minor, 0)) AS BIGINT)),
            0
        ) AS holdings_value_minor
    FROM positions AS p
    LEFT JOIN latest_prices AS lp
        ON p.security_id = lp.security_id
    WHERE p.is_active = TRUE
    GROUP BY p.account_id
),

investment_values AS (
    SELECT
        ia.account_id,
        ia.ledger_cash_minor,
        COALESCE(c.uninvested_cash_minor, 0) AS uninvested_cash_minor,
        COALESCE(h.holdings_value_minor, 0) AS holdings_value_minor
    FROM investment_accounts AS ia
    LEFT JOIN investment_cash_by_account AS c
        ON ia.account_id = c.account_id
    LEFT JOIN investment_holdings_by_account AS h
        ON ia.account_id = h.account_id
),

position_totals AS (
    SELECT
        COALESCE(
            SUM(
                CASE
                    WHEN
                        investment_values.uninvested_cash_minor != 0
                        OR investment_values.holdings_value_minor != 0
                        THEN
                            investment_values.uninvested_cash_minor
                            + investment_values.holdings_value_minor
                    ELSE investment_values.ledger_cash_minor
                END
            ),
            0
        ) AS positions_minor
    FROM investment_values
),

tangible_totals AS (
    SELECT COALESCE(SUM(current_fair_value_minor), 0) AS tangibles_minor
    FROM tangible_assets
    WHERE is_active = TRUE
)

SELECT
    asset_totals.assets_minor,
    liability_totals.liabilities_minor,
    position_totals.positions_minor,
    tangible_totals.tangibles_minor,
    asset_totals.assets_minor
    + liability_totals.liabilities_minor
    + position_totals.positions_minor
    + tangible_totals.tangibles_minor AS net_worth_minor
FROM asset_totals
CROSS JOIN liability_totals
CROSS JOIN position_totals
CROSS JOIN tangible_totals;
