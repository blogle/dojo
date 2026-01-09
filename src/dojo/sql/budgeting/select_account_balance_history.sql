WITH baseline AS (
    SELECT
        COALESCE(SUM(amount_minor), 0) AS baseline_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id = $account_id
        AND transaction_date < $start_date
        AND ($status = 'all' OR status = 'cleared')
),
flows_by_day AS (
    SELECT
        transaction_date AS as_of_date,
        SUM(amount_minor) AS flow_minor
    FROM transactions
    WHERE
        is_active = TRUE
        AND account_id = $account_id
        AND transaction_date BETWEEN $start_date AND $end_date
        AND ($status = 'all' OR status = 'cleared')
    GROUP BY transaction_date
),
calendar AS (
    SELECT
        as_of_date
    FROM generate_series($start_date, $end_date, INTERVAL 1 DAY) AS series(as_of_date)
),
joined AS (
    SELECT
        calendar.as_of_date,
        baseline.baseline_minor,
        COALESCE(flows_by_day.flow_minor, 0) AS flow_minor
    FROM calendar
    CROSS JOIN baseline
    LEFT JOIN flows_by_day
        ON calendar.as_of_date = flows_by_day.as_of_date
)
SELECT
    as_of_date,
    (baseline_minor + SUM(flow_minor) OVER (ORDER BY as_of_date)) AS balance_minor
FROM joined
ORDER BY as_of_date;
