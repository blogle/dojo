UPDATE transactions
SET is_active = FALSE,
    valid_to = ?,
    recorded_at = ?
WHERE concept_id = ?
  AND is_active = TRUE;
