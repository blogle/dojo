WITH on_budget_cash AS (
    SELECT COALESCE(SUM(current_balance_minor), 0) AS balance_minor
    FROM accounts
    WHERE
        is_active = TRUE
        AND account_class = 'cash'
        AND account_role = 'on_budget'
),

category_state AS (
    SELECT COALESCE(SUM(s.available_minor), 0) AS available_minor
    FROM budget_category_monthly_state AS s
    INNER JOIN budget_categories AS c ON s.category_id = c.category_id
    WHERE
        s.month_start = $month_start
        AND c.is_system IS NOT TRUE
)

SELECT on_budget_cash.balance_minor - category_state.available_minor AS ready_to_assign_minor
FROM on_budget_cash
CROSS JOIN category_state;
