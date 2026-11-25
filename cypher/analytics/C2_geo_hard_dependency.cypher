// 9C - Hard dependency: revenue that CANNOT be produced without a given country, because some
// item in the BOM is sourced 100% from suppliers located there (or all its plants are there).
// ERP view looks only at level-1 components and plants; graph view at every BOM level.
MATCH (f:Item {type: 'FINISHED'})
WITH sum(f.revenue_month) AS total
MATCH (f:Item {type: 'FINISHED'})
CALL (f) {
  // plants: the country holds 100% of the manufacturing share
  MATCH (f)<-[m:MANUFACTURES]-(:Plant)-[:LOCATED_IN]->(c:Country)
  WITH c, sum(m.share_pct) AS share
  WHERE share >= 99.9
  RETURN c.iso2 AS iso2, 0 AS lvl
  UNION
  // any BOM item whose supplier share located in one country is 100%
  MATCH p = (x:Item)-[:COMPONENT_OF]->{1,12}(f)
  WITH x, min(length(p)) AS lvl
  MATCH (x)<-[r:SUPPLIES]-(:Supplier)-[:LOCATED_IN]->(c:Country)
  WITH x, lvl, c, sum(r.share_pct) AS share
  WHERE share >= 99.9
  RETURN c.iso2 AS iso2, lvl
}
WITH total, f, iso2, min(lvl) AS lvl
WITH total, iso2,
     sum(CASE WHEN lvl <= 1 THEN f.revenue_month ELSE 0 END) AS erp,
     sum(f.revenue_month) AS graph
MATCH (c:Country {iso2: iso2})
RETURN iso2, c.name AS country, round(100.0 * erp / total, 1) AS erp_pct, round(100.0 * graph / total, 1) AS graph_pct
ORDER BY graph_pct DESC
