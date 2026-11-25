// FAIL if a lot was manufactured before the lot it was derived from (time travel in genealogy).
MATCH (c:Lot)-[:DERIVED_FROM]->(p:Lot)
WHERE c.mfg_date < p.mfg_date
RETURN c.lot_id AS child, p.lot_id AS parent
LIMIT 50
