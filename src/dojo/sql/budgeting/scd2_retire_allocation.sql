-- Soft retire the current active version of a budget allocation
UPDATE budget_allocations
SET is_active = FALSE, valid_to = CURRENT_TIMESTAMP
WHERE concept_id = $concept_id AND is_active = TRUE;
