INSERT INTO budget_categories (category_id, group_id, name, is_active, is_system)
VALUES (?, ?, ?, TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
SET name = EXCLUDED.name,
    group_id = EXCLUDED.group_id,
    is_active = TRUE,
    is_system = FALSE,
    updated_at = NOW();
