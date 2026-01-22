-- Category context flags (Aspire alignment)
--
-- Dojo uses a single budget_categories table for multiple semantic roles.
-- Add explicit capability flags so we can filter/validate by context.

ALTER TABLE budget_categories ADD COLUMN IF NOT EXISTS allow_transactions BOOLEAN DEFAULT TRUE;
ALTER TABLE budget_categories ADD COLUMN IF NOT EXISTS allow_allocations BOOLEAN DEFAULT TRUE;
ALTER TABLE budget_categories ADD COLUMN IF NOT EXISTS is_envelope BOOLEAN DEFAULT TRUE;
ALTER TABLE budget_categories ADD COLUMN IF NOT EXISTS is_payment BOOLEAN DEFAULT FALSE;

-- Backfill NULLs (older rows may predate the columns).
UPDATE budget_categories
SET
    allow_transactions = COALESCE(allow_transactions, TRUE),
    allow_allocations = COALESCE(allow_allocations, TRUE),
    is_envelope = COALESCE(is_envelope, TRUE),
    is_payment = COALESCE(is_payment, FALSE);

-- System categories: explicit semantics.
UPDATE budget_categories
SET
    allow_transactions = TRUE,
    allow_allocations = FALSE,
    is_envelope = FALSE,
    is_payment = FALSE
WHERE category_id IN ('opening_balance', 'balance_adjustment', 'account_transfer');

-- Available-to-budget is a system category that behaves like an allocation envelope.
UPDATE budget_categories
SET
    allow_transactions = TRUE,
    allow_allocations = TRUE,
    is_envelope = TRUE,
    is_payment = FALSE
WHERE category_id = 'available_to_budget';

-- Payment envelopes: allocatable, not a normal transaction category.
UPDATE budget_categories
SET
    allow_transactions = FALSE,
    allow_allocations = TRUE,
    is_envelope = TRUE,
    is_payment = TRUE
WHERE category_id LIKE 'payment_%' OR group_id = 'credit_card_payments';
