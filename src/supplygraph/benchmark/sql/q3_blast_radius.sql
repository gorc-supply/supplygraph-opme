-- Q3 - Blast radius of supplier $supplier_id stopping for $ttr days (TTS x TTR) in DuckDB.
WITH RECURSIVE
-- sub-tier chains expanded outwards from the disrupted supplier; pipe = lead time of the stages
-- between the disrupted supplier's output and the item reached (material still flowing)
chain(buyer, need, prod, pipe, depth) AS (
    SELECT b.buyer_id, b.for_sku, b.share_pct / 100.0, coalesce(it.pipeline_lead_days, CAST(0.0 AS DOUBLE)), 1
    FROM buys_from b
    JOIN items it ON it.sku = b.for_sku
    WHERE b.seller_id = $supplier_id
    UNION ALL
    SELECT b.buyer_id, b.for_sku, c.prod * b.share_pct / 100.0,
           c.pipe + coalesce(it.pipeline_lead_days, CAST(0.0 AS DOUBLE)), c.depth + 1
    FROM chain c
    JOIN buys_from b ON b.seller_id = c.buyer AND b.item_sku = c.need
    JOIN items it ON it.sku = b.for_sku
    WHERE c.depth < 6
),
indirect AS (
    SELECT item_sku AS sku, least(sum(share * dep), 1.0) AS loss, min(pipe) AS pipe0
    FROM (
        SELECT s.item_sku, s.supplier_id, s.share_pct / 100.0 AS share, max(c.prod) AS dep, min(c.pipe) AS pipe
        FROM chain c
        JOIN supplies s ON s.supplier_id = c.buyer AND s.item_sku = c.need
        GROUP BY s.item_sku, s.supplier_id, s.share_pct
    ) t
    GROUP BY item_sku
),
seeds AS (
    SELECT sku, max(loss) AS loss, min(pipe0) AS pipe0
    FROM (
        SELECT item_sku AS sku, share_pct / 100.0 AS loss, CAST(0.0 AS DOUBLE) AS pipe0
        FROM supplies WHERE supplier_id = $supplier_id
        UNION ALL
        SELECT sku, loss, pipe0 FROM indirect
    ) u
    GROUP BY sku
),
-- walk UP the BOM from every seed, accumulating the pipeline lead time of each parent
up(sku, loss, pipe, depth) AS (
    SELECT sku, loss, pipe0, 0 FROM seeds
    UNION ALL
    SELECT b.parent_sku, up.loss, up.pipe + coalesce(p.pipeline_lead_days, CAST(0.0 AS DOUBLE)), up.depth + 1
    FROM up
    JOIN bom b ON b.child_sku = up.sku
    JOIN items p ON p.sku = b.parent_sku
    WHERE up.depth < 12
),
fin AS (
    SELECT up.sku, max(up.loss) AS loss, min(up.pipe) AS pipe
    FROM up
    JOIN items i ON i.sku = up.sku
    WHERE i.type = 'FINISHED'
    GROUP BY up.sku
),
tts AS (
    SELECT f.sku, f.loss, s.avg_daily_demand AS add, i.unit_price,
           s.on_hand / s.avg_daily_demand + f.pipe + coalesce(s.transit_days, 0.0) AS tts
    FROM fin f
    JOIN stocks s ON s.item_sku = f.sku
    JOIN items i ON i.sku = f.sku
)
SELECT count(*) AS pairs, round(sum(add * ($ttr - tts) * loss * unit_price), 0) AS checksum
FROM tts
WHERE tts < $ttr
