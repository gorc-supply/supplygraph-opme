-- Q2 - False dual-source (strict) in DuckDB.
-- The sub-tier chain must follow the BOM: the next purchase is the one made FOR the item
-- bought in the previous hop (for_sku = previous item_sku) and every hop is a sole source.
WITH RECURSIVE direct AS (
    SELECT s.item_sku, s.supplier_id
    FROM supplies s
    JOIN items i ON i.sku = s.item_sku
    WHERE i.type = 'COMPONENT' AND i.level = 1
),
multi AS (
    SELECT item_sku, count(*) AS n
    FROM direct
    GROUP BY item_sku
    HAVING count(*) >= 2
),
chain(item, d, u, next_sku, depth) AS (
    SELECT m.item_sku, d.supplier_id, b.seller_id, b.item_sku, 1
    FROM multi m
    JOIN direct d ON d.item_sku = m.item_sku
    JOIN buys_from b ON b.buyer_id = d.supplier_id AND b.for_sku = m.item_sku AND b.share_pct >= 99.9
    UNION ALL
    SELECT c.item, c.d, b.seller_id, b.item_sku, c.depth + 1
    FROM chain c
    JOIN buys_from b ON b.buyer_id = c.u AND b.for_sku = c.next_sku AND b.share_pct >= 99.9
    WHERE c.depth < 6
),
converged AS (
    SELECT c.item, c.u
    FROM chain c
    JOIN multi m ON m.item_sku = c.item
    GROUP BY c.item, c.u, m.n
    HAVING count(DISTINCT c.d) = m.n
)
SELECT count(*) AS pairs, count(DISTINCT item) AS checksum
FROM converged
