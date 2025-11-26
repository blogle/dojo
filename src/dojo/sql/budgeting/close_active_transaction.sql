UPDATE transactions
SET
    is_active = FALSE,
    valid_to = $valid_to,
    recorded_at = $recorded_at
WHERE
    concept_id = $concept_id
    AND is_active = TRUE;
