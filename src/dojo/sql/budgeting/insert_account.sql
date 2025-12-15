INSERT INTO accounts (
    account_id,
    name,
    account_type,
    account_class,
    account_role,
    current_balance_minor,
    currency,
    is_active,
    opened_on,
    institution_name,
    created_at,
    updated_at
)
VALUES (
    $account_id,
    $name,
    $account_type,
    $account_class,
    $account_role,
    $current_balance_minor,
    $currency,
    $is_active,
    $opened_on,
    $institution_name,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
