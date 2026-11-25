// FAIL if more units were delivered from a lot than the lot contained.
MATCH (l:Lot)-[d:DELIVERED_TO]->(:Hospital)
WITH l, sum(d.qty) AS delivered
WHERE delivered > l.qty
RETURN l.lot_id AS lot_id, l.qty AS qty, delivered
LIMIT 50
