WITH on_budget_cash AS (
    SELECT COALESCE(SUM(current_balance_minor), 0) AS balance_minor
    FROM accounts
    WHERE is_active = TRUE
      AND account_class = 'cash'
      AND account_role = 'on_budget'
),
category_flow AS (
    SELECT COALESCE(SUM(s.allocated_minor + s.inflow_minor - s.activity_minor), 0) AS committed_minor
    FROM budget_category_monthly_state AS s
    JOIN budget_categories AS c ON c.category_id = s.category_id
    WHERE s.month_start = ?
      AND c.is_system IS NOT TRUE
)
SELECT
    on_budget_cash.balance_minor - category_flow.committed_minor AS ready_to_assign_minor
FROM on_budget_cash
CROSS JOIN category_flow;
