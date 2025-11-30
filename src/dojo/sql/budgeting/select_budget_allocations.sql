SELECT
    a.allocation_id,
    a.concept_id,
    a.allocation_date,
    a.amount_minor,
    a.memo,
    a.from_category_id,
    fc.name AS from_category_name,
    a.to_category_id,
    tc.name AS to_category_name,
    a.created_at
FROM budget_allocations AS a
LEFT JOIN budget_categories AS fc ON a.from_category_id = fc.category_id
INNER JOIN budget_categories AS tc ON a.to_category_id = tc.category_id
WHERE a.month_start = $month_start
  AND a.is_active = TRUE
ORDER BY a.allocation_date DESC, a.created_at DESC
LIMIT $limit_count;