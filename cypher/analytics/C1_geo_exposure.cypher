// 9C - Revenue exposure by country: "ERP view" (plant + tier-1 only) vs "graph view" (all tiers).
// Exposure of implant f to country c = the LARGEST share of any single input of f that comes
// from c (an implant stops if any one of its inputs stops). For the plant step we use the
// manufacturing share located in c. Country exposure = revenue-weighted average over implants:
//   exposure(c) = sum_f revenue(f) * max_x share_c(x) / total revenue
// It reads as: "if country c stopped, the worst-hit input of each implant would lose this
// fraction of supply, weighted by revenue" (before inventory buffers - see 9D for TTS x TTR).
// ERP view: only the plant and level-1 components (what the buyer sees in purchase orders).
// Graph view: every BOM level, all the way down to raw material.
MATCH (f:Item {type: 'FINISHED'})
WITH sum(f.revenue_month) AS total
MATCH (f:Item {type: 'FINISHED'})
CALL (f) {
  MATCH (f)<-[m:MANUFACTURES]-(p:Plant)
  RETURN p.country_iso2 AS iso2, sum(m.share_pct) / 100.0 AS share, 0 AS lvl
  UNION ALL
  MATCH path = (x:Item)-[:COMPONENT_OF]->{1,12}(f)
  WITH x, min(length(path)) AS lvl
  MATCH (x)<-[r:SUPPLIES]-(s:Supplier)
  // share of THIS input x that comes from each country (group by x, not just by country)
  WITH x, lvl, s.country_iso2 AS iso2, sum(r.share_pct) / 100.0 AS share
  RETURN iso2, share, lvl
}
WITH total, f, iso2,
     max(CASE WHEN lvl <= 1 THEN share ELSE 0.0 END) AS erp_dep,
     max(share) AS graph_dep
WITH total, iso2, sum(f.revenue_month * erp_dep) AS erp, sum(f.revenue_month * graph_dep) AS graph
MATCH (c:Country {iso2: iso2})
RETURN iso2, c.name AS country, round(100.0 * erp / total, 1) AS erp_pct, round(100.0 * graph / total, 1) AS graph_pct,
       round(100.0 * (graph - erp) / total, 1) AS hidden_pp
ORDER BY graph_pct DESC
