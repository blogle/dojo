SELECT
    c.category_id,
    c.name,
    COALESCE(s.available_minor, 0) AS available_minor
FROM budget_categories AS c
LEFT JOIN budget_category_monthly_state AS s
    ON c.category_id = s.category_id
    AND s.month_start = $month_start
WHERE
    c.is_active = TRUE
    AND COALESCE(c.allow_allocations, TRUE) = TRUE
ORDER BY c.name;
