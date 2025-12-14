-- Fixture for Quick Allocate Actions from Budget Modal
-- Sets up an account with initial Ready-to-Assign and a Netflix category with historical allocations.

-- Insert a test account with initial Ready-to-Assign ($200.00)
INSERT INTO accounts (
    account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role
)
VALUES ('acc-1', 'Checking', 'asset', 20000, 'USD', TRUE, 'cash', 'on_budget');

-- Insert Netflix budget category
INSERT INTO budget_categories (category_id, name, is_active, group_id)
VALUES ('netflix', 'Netflix', TRUE, NULL);

-- Insert monthly state for Netflix for the previous month (November 2025).
-- Allocate $15 and spend $15 so it does not roll forward into December,
-- but "Budgeted Last Month" remains $15.
INSERT INTO budget_category_monthly_state (
    month_start,
    category_id,
    allocated_minor,
    activity_minor,
    available_minor
)
VALUES ('2025-11-01', 'netflix', 1500, -1500, 0);

-- Insert current month state (December 2025) so Ready-to-Assign starts at the full cash balance.
INSERT INTO budget_category_monthly_state (
    month_start,
    category_id,
    allocated_minor,
    activity_minor,
    available_minor
)
VALUES ('2025-12-01', 'netflix', 0, 0, 0);
