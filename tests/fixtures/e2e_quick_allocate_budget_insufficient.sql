-- Fixture for Quick Allocate Actions from Budget Modal - Insufficient Funds Scenario
-- Sets up an account with initial low Ready-to-Assign and a Netflix category with historical allocations.

-- Insert a test account with initial Ready-to-Assign ($10.00)
INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES ('acc-1', 'Checking', 'asset', 1000, 'USD', TRUE, 'cash', 'on_budget');

-- Insert Netflix budget category
INSERT INTO budget_categories (category_id, name, is_active, group_id)
VALUES ('netflix', 'Netflix', TRUE, NULL);

-- Insert monthly state for Netflix for the previous month (November 2025)
-- This enables the "Budgeted last month" quick action of $15.00
INSERT INTO budget_category_monthly_state (month_start, category_id, allocated_minor, activity_minor, available_minor)
VALUES ('2025-11-01', 'netflix', 1500, 0, 1500);
