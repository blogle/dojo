-- Fixture for User Story 16: Credit Transaction Correction Workflow.
-- Seeds two credit card accounts, a checking account, and a budget category.

-- Accounts
INSERT INTO accounts (account_id, name, account_type, current_balance_minor, currency, is_active, account_class, account_role)
VALUES
    ('house_checking', 'House Checking', 'asset', 500000, 'USD', TRUE, 'cash', 'on_budget'),
    ('visa_signature', 'Visa Signature', 'liability', -100000, 'USD', TRUE, 'credit', 'on_budget'),
    ('mastercard_rewards', 'Mastercard Rewards', 'liability', -50000, 'USD', TRUE, 'credit', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET name = EXCLUDED.name,
        account_type = EXCLUDED.account_type,
        current_balance_minor = EXCLUDED.current_balance_minor,
        currency = EXCLUDED.currency,
        is_active = EXCLUDED.is_active,
        account_class = EXCLUDED.account_class,
        account_role = EXCLUDED.account_role;

-- Categories
INSERT INTO budget_categories (category_id, name, is_active, is_system)
VALUES
    ('dining_out', 'Dining Out', TRUE, FALSE),
    ('credit_card_payments', 'Credit Card Payments', TRUE, TRUE), -- System group
    ('payment_visa_signature', 'Visa Signature Payment', TRUE, FALSE), -- Payment category for Visa
    ('payment_mastercard_rewards', 'Mastercard Rewards Payment', TRUE, FALSE) -- Payment category for Mastercard
ON CONFLICT (category_id) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = EXCLUDED.is_active,
        is_system = EXCLUDED.is_system;

-- Assign payment categories to the credit card payments group
UPDATE budget_categories
SET group_id = 'credit_card_payments'
WHERE category_id IN ('payment_visa_signature', 'payment_mastercard_rewards')
  AND group_id IS DISTINCT FROM 'credit_card_payments';

-- Opening balance transactions
INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    status,
    recorded_at,
    valid_from,
    valid_to,
    is_active,
    source
)
VALUES
    ('00000000-0000-0000-0000-0000000f1601', '00000000-0000-0000-0000-0000000f1601', 'house_checking', 'opening_balance', DATE '2024-01-15', 500000, 'Opening balance', 'cleared', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TIMESTAMP '9999-12-31 00:00:00', TRUE, 'fixture'),
    ('00000000-0000-0000-0000-0000000f1602', '00000000-0000-0000-0000-0000000f1602', 'visa_signature', 'opening_balance', DATE '2024-01-15', -100000, 'Opening balance', 'cleared', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TIMESTAMP '9999-12-31 00:00:00', TRUE, 'fixture'),
    ('00000000-0000-0000-0000-0000000f1603', '00000000-0000-0000-0000-0000000f1603', 'mastercard_rewards', 'opening_balance', DATE '2024-01-15', -50000, 'Opening balance', 'cleared', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TIMESTAMP '9999-12-31 00:00:00', TRUE, 'fixture')
ON CONFLICT (transaction_version_id) DO NOTHING;

-- Update account balances to reflect opening balances
UPDATE accounts SET current_balance_minor = 500000, updated_at = TIMESTAMP '2024-01-15 12:00:00' WHERE account_id = 'house_checking';
UPDATE accounts SET current_balance_minor = -100000, updated_at = TIMESTAMP '2024-01-15 12:00:00' WHERE account_id = 'visa_signature';
UPDATE accounts SET current_balance_minor = -50000, updated_at = TIMESTAMP '2024-01-15 12:00:00' WHERE account_id = 'mastercard_rewards';

-- Monthly budgeting state for Dining Out
WITH month_start AS (
    SELECT DATE '2024-01-01' AS month_start
)
INSERT INTO budget_category_monthly_state (category_id, month_start, allocated_minor, inflow_minor, activity_minor, available_minor)
SELECT 'dining_out', month_start, 30000, 0, 0, 30000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor, inflow_minor = EXCLUDED.inflow_minor, activity_minor = EXCLUDED.activity_minor, available_minor = EXCLUDED.available_minor;

-- Monthly budgeting state for credit card payment categories
WITH month_start AS (
    SELECT DATE '2024-01-01' AS month_start
)
INSERT INTO budget_category_monthly_state (category_id, month_start, allocated_minor, inflow_minor, activity_minor, available_minor)
SELECT 'payment_visa_signature', month_start, 100000, 0, 0, 100000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor, inflow_minor = EXCLUDED.inflow_minor, activity_minor = EXCLUDED.activity_minor, available_minor = EXCLUDED.available_minor;

WITH month_start AS (
    SELECT DATE '2024-01-01' AS month_start
)
INSERT INTO budget_category_monthly_state (category_id, month_start, allocated_minor, inflow_minor, activity_minor, available_minor)
SELECT 'payment_mastercard_rewards', month_start, 50000, 0, 0, 50000 FROM month_start
ON CONFLICT (category_id, month_start) DO UPDATE
SET allocated_minor = EXCLUDED.allocated_minor, inflow_minor = EXCLUDED.inflow_minor, activity_minor = EXCLUDED.activity_minor, available_minor = EXCLUDED.available_minor;
