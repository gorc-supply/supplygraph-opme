// 9D - Time-to-Survive (TTS) x Time-to-Recover (TTR), after Simchi-Levi.
// Input: $seeds = [{sku, loss, pipe0, dc?}] (fraction of supply lost per item, stages already in the
// pipeline before the seed item) and $ttr (days).
// 1. Propagate every seed UP the BOM to the finished implants that contain it.
// 2. Pipeline days: material already past the disrupted node keeps flowing for the lead time of
//    every stage downstream of it (sum of pipeline_lead_days of the parents on the path).
// 3. TTS at each DC = on-hand cover (on_hand / avg_daily_demand) + pipeline + plant->DC transit.
// 4. If TTS < TTR the DC stocks out for (TTR - TTS) days; units short = daily demand x gap x loss.
UNWIND $seeds AS seed
MATCH (x:Item {sku: seed.sku})
MATCH p = (x)-[:COMPONENT_OF]->{0,12}(f:Item {type: 'FINISHED'})
WITH f, seed, coalesce(seed.pipe0, 0.0) + reduce(d = 0.0, n IN tail(nodes(p)) | d + coalesce(n.pipeline_lead_days, 0.0)) AS pipe
MATCH (dc:DC)-[s:STOCKS]->(f)
WHERE seed.dc IS NULL OR seed.dc = dc.id
WITH f, dc, s, max(seed.loss) AS loss, min(pipe) AS pipeline_days
WITH f, dc, s, loss, pipeline_days,
     s.on_hand / s.avg_daily_demand AS cover_days,
     pipeline_days + coalesce(s.transit_days, 0.0) AS in_transit_days
WITH f, dc, s, loss, cover_days, in_transit_days, cover_days + in_transit_days AS tts
WITH f, dc, s, loss, cover_days, in_transit_days, tts,
     CASE WHEN tts < $ttr THEN $ttr - tts ELSE 0.0 END AS gap_days
WITH f, dc, s, loss, cover_days, in_transit_days, tts, gap_days,
     s.avg_daily_demand * gap_days * loss AS units_short
RETURN f.sku AS sku, f.name AS name, f.category AS category, dc.id AS dc, dc.uf AS uf,
       round(loss, 3) AS loss_frac, round(cover_days, 1) AS cover_days,
       round(in_transit_days, 1) AS in_transit_days, round(tts, 1) AS tts_days,
       round(gap_days, 1) AS stockout_days, s.avg_daily_demand AS daily_demand,
       round(units_short, 2) AS units_short, round(units_short * f.unit_price, 2) AS revenue_at_risk,
       [(dc)-[:SERVES {is_primary: true}]->(h:Hospital)-[:CONSUMES]->(f) | h.id] AS hospitals
ORDER BY revenue_at_risk DESC
