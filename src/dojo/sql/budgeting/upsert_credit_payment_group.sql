INSERT INTO budget_category_groups (group_id, name, sort_order)
VALUES ($group_id, $name, $sort_order)
ON CONFLICT (group_id) DO UPDATE
    SET
        name = excluded.name,
        sort_order = excluded.sort_order,
        is_active = TRUE,
        updated_at = NOW();
