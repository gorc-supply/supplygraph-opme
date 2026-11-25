// FAIL if a finished implant has no path down to any raw material
// (an implant "made of nothing" means a broken or truncated BOM).
MATCH (f:Item {type: 'FINISHED'})
WHERE NOT EXISTS { (:Item {type: 'RAW'})-[:COMPONENT_OF]->{1,25}(f) }
RETURN f.sku AS sku, f.name AS name
LIMIT 50
