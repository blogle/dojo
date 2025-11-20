ALTER TABLE budget_categories ADD COLUMN goal_type TEXT;
ALTER TABLE budget_categories ADD COLUMN goal_amount_minor BIGINT;
ALTER TABLE budget_categories ADD COLUMN goal_target_date DATE;
ALTER TABLE budget_categories ADD COLUMN goal_frequency TEXT;
