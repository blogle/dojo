INSERT INTO budget_categories (category_id, group_id, name, is_active, is_system)
VALUES ($category_id, $group_id, $name, TRUE, FALSE)
ON CONFLICT (category_id) DO UPDATE
    SET
        name = excluded.name,
        group_id = excluded.group_id,
        is_active = TRUE,
        is_system = FALSE,
        updated_at = NOW();
