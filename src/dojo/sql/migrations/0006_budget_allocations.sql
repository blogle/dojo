CREATE TABLE IF NOT EXISTS budget_allocations (
    allocation_id UUID PRIMARY KEY,
    allocation_date DATE NOT NULL,
    month_start DATE NOT NULL,
    from_category_id TEXT REFERENCES budget_categories (category_id),
    to_category_id TEXT NOT NULL REFERENCES budget_categories (category_id),
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    memo TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_budget_allocations_month
ON budget_allocations (month_start DESC, allocation_date DESC, created_at DESC);
