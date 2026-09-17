-- Aspire migration: persist best-effort dashboard proxy values for parity checks

ALTER TABLE aspire_migration_sessions
ADD COLUMN IF NOT EXISTS dashboard_category_proxy_json TEXT;
