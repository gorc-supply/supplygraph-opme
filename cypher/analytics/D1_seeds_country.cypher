// 9D - Seeds of a COUNTRY disruption: all suppliers and plants located in $iso2 stop.
// Same logic as D1_seeds_supplier, applied to every supplier located in the country.
MATCH (s:Supplier)-[r:SUPPLIES]->(x:Item)
WHERE s.country_iso2 = $iso2
WITH x, sum(r.share_pct) / 100.0 AS loss
RETURN x.sku AS sku, CASE WHEN loss > 1.0 THEN 1.0 ELSE loss END AS loss, 0.0 AS pipe0
UNION
MATCH (u:Supplier)<-[bs:BUYS_FROM]-{1,6}(d:Supplier)
WHERE u.country_iso2 = $iso2
  AND allReduce(acc = {need: null, ok: true}, b IN bs |
        {need: b.for_sku, ok: acc.need IS NULL OR b.item_sku = acc.need}, acc.ok)
MATCH (d)-[sp:SUPPLIES]->(i:Item {sku: last(bs).for_sku})
CALL (bs) {
  UNWIND bs AS b
  MATCH (stage:Item {sku: b.for_sku})
  RETURN sum(coalesce(stage.pipeline_lead_days, 0.0)) AS chain_pipe
}
WITH i, d, sp, max(reduce(x = 1.0, b IN bs | x * b.share_pct / 100.0)) AS dep, min(chain_pipe) AS chain_pipe
WITH i, sum(sp.share_pct / 100.0 * dep) AS loss, min(chain_pipe) AS pipe0
RETURN i.sku AS sku, CASE WHEN loss > 1.0 THEN 1.0 ELSE loss END AS loss, pipe0
UNION
MATCH (p:Plant)-[m:MANUFACTURES]->(f:Item)
WHERE p.country_iso2 = $iso2
WITH f, sum(m.share_pct) / 100.0 AS loss
RETURN f.sku AS sku, CASE WHEN loss > 1.0 THEN 1.0 ELSE loss END AS loss, 0.0 AS pipe0
