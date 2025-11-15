INSERT INTO budget_categories (
    category_id,
    name,
    is_active,
    created_at,
    updated_at
)
VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
