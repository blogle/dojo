SELECT
    s.security_id,
    s.ticker,
    MAX(mp.market_date) AS last_market_date
FROM securities AS s
INNER JOIN positions AS p
    ON
        s.security_id = p.security_id
        AND p.is_active = TRUE
LEFT JOIN market_prices AS mp
    ON
        s.security_id = mp.security_id
GROUP BY s.security_id, s.ticker
ORDER BY s.ticker;
