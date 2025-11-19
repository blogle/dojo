SELECT
    a.allocation_id,
    a.allocation_date,
    a.amount_minor,
    a.memo,
    a.from_category_id,
    fc.name AS from_category_name,
    a.to_category_id,
    tc.name AS to_category_name,
    a.created_at
FROM budget_allocations AS a
LEFT JOIN budget_categories AS fc ON fc.category_id = a.from_category_id
JOIN budget_categories AS tc ON tc.category_id = a.to_category_id
WHERE a.month_start = ?
ORDER BY a.allocation_date DESC, a.created_at DESC
LIMIT ?;
