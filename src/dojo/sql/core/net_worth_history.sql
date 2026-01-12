WITH params AS (
    SELECT
        CAST($start_date AS DATE) AS start_date,
        CAST($end_date AS DATE) AS end_date
),

calendar AS (
    SELECT
        as_of_date,
        (CAST(as_of_date AS TIMESTAMP) + INTERVAL 1 DAY - INTERVAL '1 microsecond') AS as_of_ts
    FROM generate_series(
        (SELECT start_date FROM params),
        (SELECT end_date FROM params),
        INTERVAL 1 DAY
    ) AS series(as_of_date)
),

asset_accounts AS (
    SELECT account_id
    FROM accounts
    WHERE
        is_active = TRUE
        AND account_type = 'asset'
        AND account_class != 'investment'
),

liability_accounts AS (
    SELECT account_id
    FROM accounts
    WHERE
        is_active = TRUE
        AND account_type = 'liability'
),

investment_accounts AS (
    SELECT account_id
    FROM accounts
    WHERE
        is_active = TRUE
        AND account_type = 'asset'
        AND account_class = 'investment'
),

asset_baseline AS (
    SELECT COALESCE(SUM(amount_minor), 0) AS baseline_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id IN (SELECT account_id FROM asset_accounts)
        AND transaction_date < (SELECT start_date FROM params)
),

asset_flows AS (
    SELECT
        transaction_date AS as_of_date,
        SUM(amount_minor) AS flow_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id IN (SELECT account_id FROM asset_accounts)
        AND transaction_date BETWEEN (SELECT start_date FROM params) AND (SELECT end_date FROM params)
    GROUP BY transaction_date
),

assets_by_day AS (
    SELECT
        c.as_of_date,
        (ab.baseline_minor + SUM(COALESCE(af.flow_minor, 0)) OVER (ORDER BY c.as_of_date)) AS assets_minor
    FROM calendar AS c
    CROSS JOIN asset_baseline AS ab
    LEFT JOIN asset_flows AS af
        ON c.as_of_date = af.as_of_date
),

liability_baseline AS (
    SELECT COALESCE(SUM(amount_minor), 0) AS baseline_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id IN (SELECT account_id FROM liability_accounts)
        AND transaction_date < (SELECT start_date FROM params)
),

liability_flows AS (
    SELECT
        transaction_date AS as_of_date,
        SUM(amount_minor) AS flow_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id IN (SELECT account_id FROM liability_accounts)
        AND transaction_date BETWEEN (SELECT start_date FROM params) AND (SELECT end_date FROM params)
    GROUP BY transaction_date
),

liabilities_by_day AS (
    SELECT
        c.as_of_date,
        (lb.baseline_minor + SUM(COALESCE(lf.flow_minor, 0)) OVER (ORDER BY c.as_of_date)) AS liabilities_minor
    FROM calendar AS c
    CROSS JOIN liability_baseline AS lb
    LEFT JOIN liability_flows AS lf
        ON c.as_of_date = lf.as_of_date
),

investment_ledger_baseline AS (
    SELECT
        account_id,
        COALESCE(SUM(amount_minor), 0) AS baseline_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id IN (SELECT account_id FROM investment_accounts)
        AND transaction_date < (SELECT start_date FROM params)
    GROUP BY account_id
),

investment_ledger_flows AS (
    SELECT
        account_id,
        transaction_date AS as_of_date,
        SUM(amount_minor) AS flow_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id IN (SELECT account_id FROM investment_accounts)
        AND transaction_date BETWEEN (SELECT start_date FROM params) AND (SELECT end_date FROM params)
    GROUP BY account_id, transaction_date
),

investment_ledger_calendar AS (
    SELECT
        ia.account_id,
        c.as_of_date
    FROM investment_accounts AS ia
    CROSS JOIN calendar AS c
),

investment_ledger_joined AS (
    SELECT
        ilc.account_id,
        ilc.as_of_date,
        COALESCE(ilb.baseline_minor, 0) AS baseline_minor,
        COALESCE(ilf.flow_minor, 0) AS flow_minor
    FROM investment_ledger_calendar AS ilc
    LEFT JOIN investment_ledger_baseline AS ilb
        ON ilc.account_id = ilb.account_id
    LEFT JOIN investment_ledger_flows AS ilf
        ON
            ilc.account_id = ilf.account_id
            AND ilc.as_of_date = ilf.as_of_date
),

investment_ledger_by_day AS (
    SELECT
        account_id,
        as_of_date,
        baseline_minor + SUM(flow_minor) OVER (PARTITION BY account_id ORDER BY as_of_date) AS ledger_cash_minor
    FROM investment_ledger_joined
),

investment_details_by_day AS (
    SELECT
        ia.account_id,
        c.as_of_date,
        COALESCE(iad.uninvested_cash_minor, 0) AS uninvested_cash_minor
    FROM investment_accounts AS ia
    CROSS JOIN calendar AS c
    LEFT JOIN investment_account_details AS iad
        ON
            c.as_of_ts >= iad.valid_from
            AND c.as_of_ts < iad.valid_to
            AND iad.account_id = ia.account_id
),

positions_daily AS (
    SELECT
        p.account_id,
        c.as_of_date,
        p.security_id,
        p.quantity
    FROM calendar AS c
    INNER JOIN positions AS p
        ON
            c.as_of_ts >= p.valid_from
            AND c.as_of_ts < p.valid_to
            AND p.account_id IN (SELECT account_id FROM investment_accounts)
),

positions_priced AS (
    SELECT
        pd.account_id,
        pd.as_of_date,
        pd.security_id,
        pd.quantity,
        mp.close_minor
    FROM positions_daily AS pd
    ASOF LEFT JOIN market_prices AS mp
        ON
            pd.security_id = mp.security_id
            AND pd.as_of_date >= mp.market_date
),

holdings_by_day AS (
    SELECT
        account_id,
        as_of_date,
        COALESCE(
            SUM(CAST(ROUND(quantity * COALESCE(close_minor, 0)) AS BIGINT)),
            0
        ) AS holdings_value_minor
    FROM positions_priced
    GROUP BY account_id, as_of_date
),

investment_values_by_day AS (
    SELECT
        c.as_of_date,
        ia.account_id,
        COALESCE(l.ledger_cash_minor, 0) AS ledger_cash_minor,
        COALESCE(d.uninvested_cash_minor, 0) AS uninvested_cash_minor,
        COALESCE(h.holdings_value_minor, 0) AS holdings_value_minor,
        CASE
            WHEN
                COALESCE(d.uninvested_cash_minor, 0) != 0
                OR COALESCE(h.holdings_value_minor, 0) != 0
                THEN
                    COALESCE(d.uninvested_cash_minor, 0)
                    + COALESCE(h.holdings_value_minor, 0)
            ELSE COALESCE(l.ledger_cash_minor, 0)
        END AS account_value_minor
    FROM calendar AS c
    CROSS JOIN investment_accounts AS ia
    LEFT JOIN investment_ledger_by_day AS l
        ON
            l.account_id = ia.account_id
            AND l.as_of_date = c.as_of_date
    LEFT JOIN investment_details_by_day AS d
        ON
            d.account_id = ia.account_id
            AND d.as_of_date = c.as_of_date
    LEFT JOIN holdings_by_day AS h
        ON
            h.account_id = ia.account_id
            AND h.as_of_date = c.as_of_date
),

positions_total_by_day AS (
    SELECT
        as_of_date,
        COALESCE(SUM(account_value_minor), 0) AS positions_minor
    FROM investment_values_by_day
    GROUP BY as_of_date
),

tangibles_by_day AS (
    SELECT
        c.as_of_date,
        COALESCE(SUM(t.current_fair_value_minor), 0) AS tangibles_minor
    FROM calendar AS c
    LEFT JOIN tangible_assets AS t
        ON
            c.as_of_ts >= t.valid_from
            AND c.as_of_ts < t.valid_to
    GROUP BY c.as_of_date
)

SELECT
    c.as_of_date,
    COALESCE(a.assets_minor, 0)
    + COALESCE(l.liabilities_minor, 0)
    + COALESCE(p.positions_minor, 0)
    + COALESCE(t.tangibles_minor, 0) AS net_worth_minor
FROM calendar AS c
LEFT JOIN assets_by_day AS a
    ON c.as_of_date = a.as_of_date
LEFT JOIN liabilities_by_day AS l
    ON c.as_of_date = l.as_of_date
LEFT JOIN positions_total_by_day AS p
    ON c.as_of_date = p.as_of_date
LEFT JOIN tangibles_by_day AS t
    ON c.as_of_date = t.as_of_date
ORDER BY c.as_of_date;
