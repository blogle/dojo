CREATE TABLE IF NOT EXISTS budget_category_groups (
    group_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE budget_categories ADD COLUMN group_id TEXT;
-- Note: DuckDB does not support adding foreign key constraints via ALTER TABLE easily,
-- so we rely on application logic or recreate the table if strict enforcement is needed.
-- For now, we just add the column.
