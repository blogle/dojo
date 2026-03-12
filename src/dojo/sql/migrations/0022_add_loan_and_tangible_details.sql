-- Expand loan_account_details
ALTER TABLE loan_account_details ADD COLUMN IF NOT EXISTS loan_start_date DATE;
ALTER TABLE loan_account_details ADD COLUMN IF NOT EXISTS original_term_months INTEGER;
ALTER TABLE loan_account_details ADD COLUMN IF NOT EXISTS payment_mode TEXT;

-- Expand tangible_asset_details
ALTER TABLE tangible_asset_details ADD COLUMN IF NOT EXISTS acquisition_date DATE;
ALTER TABLE tangible_asset_details ADD COLUMN IF NOT EXISTS valuation_source TEXT;
ALTER TABLE tangible_asset_details ADD COLUMN IF NOT EXISTS notes TEXT;
