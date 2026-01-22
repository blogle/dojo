-- Remove NULL semantics from allocations: use available_to_budget explicitly.
--
-- DuckDB has limited ALTER COLUMN constraint support, so rebuild the table
-- with from_category_id enforced as NOT NULL.

-- Normalize existing rows first.
UPDATE budget_allocations
SET from_category_id = 'available_to_budget'
WHERE from_category_id IS NULL;

-- DuckDB won't allow altering a table while dependent indexes exist.
DROP INDEX IF EXISTS idx_budget_allocations_month;
DROP INDEX IF EXISTS idx_allocations_concept_active;

ALTER TABLE budget_allocations RENAME TO budget_allocations_old;

CREATE TABLE budget_allocations (
    allocation_id UUID PRIMARY KEY,
    allocation_date DATE NOT NULL,
    month_start DATE NOT NULL,
    from_category_id TEXT NOT NULL REFERENCES budget_categories (category_id),
    to_category_id TEXT NOT NULL REFERENCES budget_categories (category_id),
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    memo TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- SCD2 / temporal ledger columns
    concept_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP DEFAULT '9999-12-31 00:00:00',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO budget_allocations (
    allocation_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo,
    created_at,
    updated_at,
    concept_id,
    is_active,
    valid_from,
    valid_to,
    recorded_at
)
SELECT
    allocation_id,
    allocation_date,
    month_start,
    from_category_id,
    to_category_id,
    amount_minor,
    memo,
    created_at,
    updated_at,
    concept_id,
    is_active,
    valid_from,
    valid_to,
    recorded_at
FROM budget_allocations_old;

DROP TABLE budget_allocations_old;

-- Recreate indexes.
CREATE INDEX IF NOT EXISTS idx_budget_allocations_month
ON budget_allocations (month_start DESC, allocation_date DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_allocations_concept_active
ON budget_allocations (concept_id, is_active);
