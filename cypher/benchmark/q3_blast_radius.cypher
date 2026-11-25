// Q3 - Blast radius of supplier $supplier_id stopping for $ttr days (TTS x TTR), in ONE query:
// seeds (direct + BOM-consistent sub-tier chains) -> up the BOM -> DC stocks -> revenue at risk.
CALL () {
  MATCH (u:Supplier {id: $supplier_id})-[r:SUPPLIES]->(x:Item)
  RETURN x.sku AS sku, r.share_pct / 100.0 AS loss, 0.0 AS pipe0
  UNION
  MATCH (u:Supplier {id: $supplier_id})<-[bs:BUYS_FROM]-{1,6}(d:Supplier)
  WHERE allReduce(acc = {need: null, ok: true}, b IN bs |
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
}
WITH sku, max(loss) AS loss, min(pipe0) AS pipe0
MATCH (x:Item {sku: sku})
MATCH p = (x)-[:COMPONENT_OF]->{0,12}(f:Item {type: 'FINISHED'})
WITH f, loss, pipe0 + reduce(d = 0.0, n IN tail(nodes(p)) | d + coalesce(n.pipeline_lead_days, 0.0)) AS pipe
WITH f, max(loss) AS loss, min(pipe) AS pipe
MATCH (dc:DC)-[s:STOCKS]->(f)
WITH f, loss, s.avg_daily_demand AS add, s.on_hand / s.avg_daily_demand + pipe + coalesce(s.transit_days, 0.0) AS tts
WHERE tts < $ttr
RETURN count(*) AS pairs, round(sum(add * ($ttr - tts) * loss * f.unit_price), 0) AS checksum
