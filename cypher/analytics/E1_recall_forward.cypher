// 9E - Forward trace ("where did it go?"): every lot derived from $lot_id at any depth, the
// hospitals that received finished implants, and the units still in stock to quarantine.
// Why graph: genealogy is a DAG of unknown depth; one variable-length pattern replaces a
// recursive CTE per genealogy level.
MATCH (src:Lot {lot_id: $lot_id})
MATCH (l:Lot)-[:DERIVED_FROM]->{1,12}(src)
WITH DISTINCT l
MATCH (l)-[:OF_ITEM]->(i:Item)
OPTIONAL MATCH (l)-[d:DELIVERED_TO]->(h:Hospital)
WITH l, i, collect(CASE WHEN h IS NULL THEN null ELSE
       {hospital_id: h.id, hospital: h.name, uf: h.uf, qty: d.qty, date: toString(d.date)} END) AS deliveries,
     sum(coalesce(d.qty, 0)) AS delivered
RETURN l.lot_id AS lot_id, i.sku AS sku, i.type AS type, i.level AS level, l.status AS status,
       l.qty AS qty, delivered,
       CASE WHEN i.type = 'FINISHED' THEN l.qty - delivered END AS in_stock,
       deliveries
ORDER BY level DESC, lot_id
