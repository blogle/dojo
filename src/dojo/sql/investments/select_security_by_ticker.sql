SELECT
    security_id,
    ticker,
    name,
    type,
    currency
FROM securities
WHERE ticker = $ticker;
