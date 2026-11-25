// 9B - Visible single sourcing: items with exactly one supplier, ranked by revenue at stake.
MATCH (s:Supplier)-[:SUPPLIES]->(i:Item)
WITH i, collect(s) AS sups
WHERE size(sups) = 1
WITH i, sups[0] AS s
CALL (i) {
  MATCH (i)-[:COMPONENT_OF]->{1,12}(f:Item {type: 'FINISHED'})
  WITH DISTINCT f
  RETURN sum(f.revenue_month) AS revenue_exposed, count(f) AS finished_affected
}
RETURN i.sku AS item_sku, i.name AS item_name, i.type AS type, i.level AS level,
       s.id AS supplier_id, s.tier AS tier, s.country_iso2 AS country,
       revenue_exposed, finished_affected
ORDER BY revenue_exposed DESC
