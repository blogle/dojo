INSERT INTO securities (
    security_id,
    ticker,
    name,
    type,
    currency,
    created_at,
    updated_at
)
VALUES (
    $security_id,
    $ticker,
    $name,
    $type,
    $currency,
    $recorded_at,
    $recorded_at
)
ON CONFLICT (ticker) DO NOTHING;
