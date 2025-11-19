WITH bounds AS (
    SELECT
        DATE_TRUNC('month', ?) AS month_start,
        DATE_TRUNC('month', ?) + INTERVAL 1 MONTH AS month_end
)
SELECT COALESCE(SUM(t.amount_minor), 0) AS inflow_minor
FROM transactions AS t
JOIN accounts AS a ON a.account_id = t.account_id
CROSS JOIN bounds AS b
WHERE t.is_active = TRUE
  AND t.amount_minor > 0
  AND a.account_class = 'cash'
  AND a.account_role = 'on_budget'
  AND t.transaction_date >= b.month_start
  AND t.transaction_date < b.month_end;
