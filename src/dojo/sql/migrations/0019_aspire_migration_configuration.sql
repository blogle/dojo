-- Aspire migration: persist budget configuration table + goal hints

ALTER TABLE aspire_migration_sessions
ADD COLUMN IF NOT EXISTS user_def_amounts_json TEXT;

ALTER TABLE aspire_migration_sessions
ADD COLUMN IF NOT EXISTS user_def_goals_json TEXT;

ALTER TABLE aspire_migration_sessions
ADD COLUMN IF NOT EXISTS category_type_symbols_json TEXT;

ALTER TABLE aspire_migration_sessions
ADD COLUMN IF NOT EXISTS configuration_rows_json TEXT;
