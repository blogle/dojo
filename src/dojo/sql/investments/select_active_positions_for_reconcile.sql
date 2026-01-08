SELECT
    p.position_id,
    p.concept_id,
    p.account_id,
    p.security_id,
    p.quantity,
    p.avg_cost_minor,
    s.ticker
FROM positions AS p
INNER JOIN securities AS s
    ON p.security_id = s.security_id
WHERE
    p.account_id = $account_id
    AND p.is_active = TRUE
ORDER BY s.ticker;
