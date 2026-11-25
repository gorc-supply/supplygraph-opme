// FAIL if an item cannot be obtained: purchased items (components / raw) need at least one
// SUPPLIES relationship; finished items need at least one plant that MANUFACTURES them.
MATCH (i:Item)
WHERE (i.type <> 'FINISHED' AND NOT EXISTS { (:Supplier)-[:SUPPLIES]->(i) })
   OR (i.type = 'FINISHED' AND NOT EXISTS { (:Plant)-[:MANUFACTURES]->(i) })
RETURN i.sku AS sku, i.type AS type
LIMIT 50
