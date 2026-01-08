WITH latest_prices AS (
    SELECT
        mp.security_id,
        mp.close_minor
    FROM market_prices AS mp
    QUALIFY
        ROW_NUMBER() OVER (
            PARTITION BY mp.security_id
            ORDER BY mp.market_date DESC, mp.recorded_at DESC
        ) = 1
)

SELECT
    p.position_id,
    p.concept_id,
    p.account_id,
    p.security_id,
    p.quantity,
    p.avg_cost_minor,
    p.valid_from,
    p.valid_to,
    p.is_active,
    p.recorded_at,
    s.ticker,
    s.name,
    lp.close_minor
FROM positions AS p
INNER JOIN securities AS s
    ON p.security_id = s.security_id
LEFT JOIN latest_prices AS lp
    ON p.security_id = lp.security_id
WHERE
    p.account_id = $account_id
    AND p.is_active = TRUE
ORDER BY s.ticker;
