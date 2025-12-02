-- Ensure SCD-2 columns exist (handling drift from previous dev state)

ALTER TABLE budget_allocations ADD COLUMN IF NOT EXISTS concept_id UUID;
UPDATE budget_allocations SET concept_id = allocation_id WHERE concept_id IS NULL;

ALTER TABLE budget_allocations ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE budget_allocations ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE budget_allocations ADD COLUMN IF NOT EXISTS valid_to TIMESTAMP DEFAULT '9999-12-31 00:00:00';
ALTER TABLE budget_allocations ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_allocations_concept_active 
ON budget_allocations (concept_id, is_active);
