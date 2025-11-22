-- Ensure the Credit Card Payments group exists and is ordered first.
INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES ('credit_card_payments', 'Credit Card Payments', -1000)
ON CONFLICT (group_id) DO UPDATE
SET name = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE,
    updated_at = NOW();

-- Backfill payment categories for all credit accounts so existing data stays consistent.
WITH normalized_accounts AS (
    SELECT
        account_id,
        name,
        TRIM(BOTH '_' FROM LOWER(REGEXP_REPLACE(account_id, '[^a-z0-9]+', '_', 'g'))) AS slug
    FROM accounts
    WHERE account_type = 'liability'
      AND account_class = 'credit'
)
INSERT INTO budget_categories (category_id, group_id, name, is_active, is_system)
SELECT
    'payment_' || COALESCE(NULLIF(slug, ''), 'account') AS category_id,
    'credit_card_payments',
    name,
    TRUE,
    FALSE
FROM normalized_accounts
ON CONFLICT (category_id) DO UPDATE
SET name = EXCLUDED.name,
    group_id = EXCLUDED.group_id,
    is_active = TRUE,
    is_system = FALSE,
    updated_at = NOW();
