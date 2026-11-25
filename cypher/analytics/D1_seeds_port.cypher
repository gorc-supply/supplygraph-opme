// 9D - Seeds of a PORT / gateway disruption. A port cuts specific lanes, not items: for every
// (finished item, DC) we check whether each plant->DC route of the item's plants goes through
// the port. If an alternative route exists the loss is 0 for that plant (only a re-routing delay).
MATCH (port:Port {code: $port})
MATCH (pl:Plant)-[m:MANUFACTURES]->(f:Item)<-[:STOCKS]-(dc:DC)
WHERE EXISTS { (pl)-[:SHIPS_TO]->{1,3}(port) }
OPTIONAL CALL (pl, dc, port) {
  MATCH p = (pl)-[:SHIPS_TO]->{1,6}(dc)
  WHERE NOT port IN nodes(p)
  RETURN min(reduce(t = 0.0, r IN relationships(p) | t + r.lead_time_days)) AS alt_lead
}
WITH f, dc, sum(CASE WHEN alt_lead IS NULL THEN m.share_pct / 100.0 ELSE 0.0 END) AS loss
WHERE loss > 0
RETURN f.sku AS sku, dc.id AS dc, CASE WHEN loss > 1.0 THEN 1.0 ELSE loss END AS loss, 0.0 AS pipe0
