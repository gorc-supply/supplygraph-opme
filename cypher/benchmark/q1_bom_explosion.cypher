// Q1 - Multi-level BOM explosion of EVERY finished implant down to raw material,
// with the gross raw-material quantity per implant (product of qty_per along each path,
// summed over all paths). Returns a checksum so it can be compared with the SQL version.
MATCH p = (r:Item {type: 'RAW'})-[:COMPONENT_OF]->{1,12}(f:Item {type: 'FINISHED'})
WITH f, r, sum(reduce(q = 1.0, x IN relationships(p) | q * x.qty_per)) AS qty
RETURN count(*) AS pairs, round(sum(qty), 3) AS checksum
