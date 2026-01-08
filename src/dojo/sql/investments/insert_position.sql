INSERT INTO positions (
    position_id,
    concept_id,
    account_id,
    security_id,
    quantity,
    avg_cost_minor,
    valid_from,
    valid_to,
    is_active,
    recorded_at
)
VALUES (
    $position_id,
    $concept_id,
    $account_id,
    $security_id,
    $quantity,
    $avg_cost_minor,
    $valid_from,
    $valid_to,
    TRUE,
    $recorded_at
);
