// FAIL if a finished-implant lot cannot be traced back to at least one raw-material lot.
// Implant traceability (ANVISA / UDI) requires lot genealogy down to the material heat/batch.
MATCH (l:Lot)-[:OF_ITEM]->(:Item {type: 'FINISHED'})
WHERE NOT EXISTS {
  (l)-[:DERIVED_FROM]->{1,12}(:Lot)-[:OF_ITEM]->(:Item {type: 'RAW'})
}
RETURN l.lot_id AS lot_id
LIMIT 50
