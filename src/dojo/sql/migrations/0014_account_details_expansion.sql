-- Add institution_name to the main accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS institution_name TEXT;

-- Expand credit_account_details
ALTER TABLE credit_account_details ADD COLUMN IF NOT EXISTS card_type TEXT;
ALTER TABLE credit_account_details ADD COLUMN IF NOT EXISTS cash_advance_apr DOUBLE DEFAULT 0;

-- Expand accessible_asset_details
ALTER TABLE accessible_asset_details ADD COLUMN IF NOT EXISTS interest_rate_apy DOUBLE DEFAULT 0;
ALTER TABLE accessible_asset_details ADD COLUMN IF NOT EXISTS early_withdrawal_penalty BOOLEAN DEFAULT FALSE;

-- Expand investment_account_details
ALTER TABLE investment_account_details ADD COLUMN IF NOT EXISTS is_self_directed BOOLEAN DEFAULT FALSE;
ALTER TABLE investment_account_details ADD COLUMN IF NOT EXISTS tax_classification TEXT;

-- Expand loan_account_details
ALTER TABLE loan_account_details ADD COLUMN IF NOT EXISTS mortgage_escrow_details TEXT;

-- Expand tangible_asset_details
ALTER TABLE tangible_asset_details ADD COLUMN IF NOT EXISTS acquisition_cost_minor BIGINT DEFAULT 0;
