// FAIL if the supplier shares of an item do not add up to 100% (tolerance 0.5 p.p.).
// Same rule for each buyer's sub-tier split (BUYS_FROM grouped by buyer + item + program).
MATCH (s:Supplier)-[r:SUPPLIES]->(i:Item)
WITH i.sku AS key, 'SUPPLIES' AS rel, sum(r.share_pct) AS total
WHERE abs(total - 100.0) > 0.5
RETURN key, rel, total
UNION ALL
MATCH (b:Supplier)-[r:BUYS_FROM]->(:Supplier)
WITH b.id + ' / ' + r.item_sku + ' / ' + r.for_sku AS key, 'BUYS_FROM' AS rel, sum(r.share_pct) AS total
WHERE abs(total - 100.0) > 0.5
RETURN key, rel, total
