WITH params AS (
    SELECT
        CAST($account_id AS TEXT) AS account_id,
        CAST($start_date AS DATE) AS start_date,
        CAST($end_date AS DATE) AS end_date
),

daily AS (
    SELECT market_date
    FROM GENERATE_SERIES(
        (SELECT start_date FROM params),
        (SELECT end_date FROM params),
        INTERVAL 1 DAY
    ) AS t (market_date)
),

ledger_by_day AS (
    SELECT
        d.market_date,
        COALESCE(SUM(tx.amount_minor), 0) AS ledger_cash_minor
    FROM daily AS d
    LEFT JOIN transactions AS tx
        ON
            d.market_date >= tx.transaction_date
            AND tx.account_id = (SELECT account_id FROM params)
            AND tx.is_active = TRUE
    GROUP BY d.market_date
),

details_by_day AS (
    SELECT
        d.market_date,
        COALESCE(iad.uninvested_cash_minor, 0) AS uninvested_cash_minor
    FROM daily AS d
    LEFT JOIN investment_account_details AS iad
        ON
            (CAST(d.market_date AS TIMESTAMP) + INTERVAL 1 DAY - INTERVAL '1 microsecond') >= iad.valid_from
            AND (CAST(d.market_date AS TIMESTAMP) + INTERVAL 1 DAY - INTERVAL '1 microsecond') < iad.valid_to
            AND iad.account_id = (SELECT account_id FROM params)
),

positions_daily AS (
    SELECT
        d.market_date,
        p.security_id,
        p.quantity
    FROM daily AS d
    INNER JOIN positions AS p
        ON
            (CAST(d.market_date AS TIMESTAMP) + INTERVAL 1 DAY - INTERVAL '1 microsecond') >= p.valid_from
            AND (CAST(d.market_date AS TIMESTAMP) + INTERVAL 1 DAY - INTERVAL '1 microsecond') < p.valid_to
            AND p.account_id = (SELECT account_id FROM params)
),

positions_priced AS (
    SELECT
        pd.market_date,
        pd.security_id,
        pd.quantity,
        mp.close_minor
    FROM positions_daily AS pd
    ASOF LEFT JOIN market_prices AS mp
        ON
            pd.security_id = mp.security_id
            AND pd.market_date >= mp.market_date
),

holdings_by_day AS (
    SELECT
        market_date,
        COALESCE(
            SUM(CAST(ROUND(quantity * COALESCE(close_minor, 0)) AS BIGINT)),
            0
        ) AS holdings_value_minor
    FROM positions_priced
    GROUP BY market_date
),

combined AS (
    SELECT
        d.market_date,
        COALESCE(l.ledger_cash_minor, 0) AS ledger_cash_minor,
        COALESCE(det.uninvested_cash_minor, 0) AS uninvested_cash_minor,
        COALESCE(h.holdings_value_minor, 0) AS holdings_value_minor
    FROM daily AS d
    LEFT JOIN ledger_by_day AS l
        ON
            d.market_date = l.market_date
    LEFT JOIN details_by_day AS det
        ON
            d.market_date = det.market_date
    LEFT JOIN holdings_by_day AS h
        ON
            d.market_date = h.market_date
)

SELECT
    market_date,
    uninvested_cash_minor + holdings_value_minor AS nav_minor,
    COALESCE(ledger_cash_minor - LAG(ledger_cash_minor) OVER (ORDER BY market_date), 0) AS cash_flow_minor,
    (uninvested_cash_minor + holdings_value_minor) - ledger_cash_minor AS return_minor
FROM combined
ORDER BY market_date;
