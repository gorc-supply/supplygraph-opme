// FAIL if the bill of materials has a cycle. COMPONENT_OF must be a DAG, otherwise
// a BOM explosion never terminates and quantities multiply forever.
// A cycle is a COMPONENT_OF path that comes back to its start node.
MATCH p = (i:Item)-[:COMPONENT_OF]->{1,25}(i)
RETURN i.sku AS sku, length(p) AS cycle_length
LIMIT 50
