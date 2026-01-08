UPDATE positions
SET
    is_active = FALSE,
    valid_to = $valid_to,
    recorded_at = $recorded_at
WHERE
    position_id = $position_id
    AND is_active = TRUE;
