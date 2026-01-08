INSERT INTO market_prices (
    security_id,
    market_date,
    open_minor,
    high_minor,
    low_minor,
    close_minor,
    adj_close_minor,
    volume,
    recorded_at
)
VALUES (
    $security_id,
    $market_date,
    $open_minor,
    $high_minor,
    $low_minor,
    $close_minor,
    $adj_close_minor,
    $volume,
    $recorded_at
)
ON CONFLICT (security_id, market_date) DO UPDATE
    SET
        open_minor = excluded.open_minor,
        high_minor = excluded.high_minor,
        low_minor = excluded.low_minor,
        close_minor = excluded.close_minor,
        adj_close_minor = excluded.adj_close_minor,
        volume = excluded.volume,
        recorded_at = excluded.recorded_at;
