// 9E - Backward trace ("where did it come from?"): all ancestor lots of $lot_id down to the
// raw-material heat, with the supplier / plant that produced each one.
MATCH (l:Lot {lot_id: $lot_id})
MATCH p = (l)-[:DERIVED_FROM]->{1,12}(a:Lot)
MATCH (a)-[:OF_ITEM]->(i:Item)
RETURN a.lot_id AS lot_id, i.sku AS sku, i.name AS name, i.type AS type, min(length(p)) AS depth,
       a.source_id AS produced_by, toString(a.mfg_date) AS mfg_date, a.status AS status
ORDER BY depth, lot_id
