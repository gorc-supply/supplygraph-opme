// 9D - Seeds of a SUPPLIER disruption: which items lose which fraction of their supply.
// (1) items the supplier sells directly -> they lose its network share;
// (2) items whose suppliers buy from it, directly or through a BOM-consistent sub-tier chain ->
//     loss = sum over suppliers d of share(d, item) x product of BUYS_FROM shares along the chain.
// The chain is expanded FROM the disrupted supplier outwards (anchored on its id): bs[0] is the
// purchase made from u, bs[k+1] is the purchase that needs bs[k]'s buyer output, so
// bs[k].for_sku must equal bs[k+1].item_sku. allReduce() checks that at every step and prunes early.
// pipe0 = lead time of the intermediate stages already between u's output and the seed item
// (material in those stages keeps flowing during the outage), so TTS is not under-estimated.
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
