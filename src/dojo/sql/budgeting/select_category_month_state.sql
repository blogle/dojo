SELECT
    c.category_id,
    c.name,
    COALESCE(s.available_minor, 0) AS available_minor,
    COALESCE(s.activity_minor, 0) AS activity_minor
FROM budget_categories AS c
LEFT JOIN budget_category_monthly_state AS s
    ON s.category_id = c.category_id
   AND s.month_start = ?
WHERE c.category_id = ?;
