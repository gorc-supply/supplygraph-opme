-- Q1 - Multi-level BOM explosion of every finished implant down to raw material (DuckDB).
-- Recursive CTE: anchor = direct children of finished items; recursion = join the BOM again.
WITH RECURSIVE ex(root, sku, qty, depth) AS (
    SELECT b.parent_sku, b.child_sku, b.qty_per, 1
    FROM bom b
    JOIN items i ON i.sku = b.parent_sku
    WHERE i.type = 'FINISHED'
    UNION ALL
    SELECT ex.root, b.child_sku, ex.qty * b.qty_per, ex.depth + 1
    FROM ex
    JOIN bom b ON b.parent_sku = ex.sku
    WHERE ex.depth < 12
),
per_pair AS (
    SELECT ex.root, ex.sku, sum(ex.qty) AS qty
    FROM ex
    JOIN items i ON i.sku = ex.sku
    WHERE i.type = 'RAW'
    GROUP BY ex.root, ex.sku
)
SELECT count(*) AS pairs, round(sum(qty), 3) AS checksum
FROM per_pair
