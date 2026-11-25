// 9F - Alternative supply routes plant -> hospital ranked by lead time or cost, optionally
// avoiding a gateway ($avoid_port). Pure-Cypher enumeration so it also runs on AuraDB Free
// (no GDS): the logistics layer is small, so we list every simple route and sum its weights.
// The GDS Dijkstra / Yen version in supplygraph.gds returns the same best routes.
MATCH (pl:Plant {id: $plant})
MATCH (h:Hospital {id: $hospital})
MATCH p = (pl)-[:SHIPS_TO]->{1,6}(dc:DC)-[:SERVES]->(h)
WHERE ($avoid_port IS NULL OR none(n IN nodes(p) WHERE n:Port AND n.code = $avoid_port))
  AND all(k IN range(0, size(nodes(p)) - 2) WHERE NOT nodes(p)[k] IN nodes(p)[k + 1..])
WITH p, reduce(t = 0.0, r IN relationships(p) | t + r.lead_time_days) AS lead,
        reduce(c = 0.0, r IN relationships(p) | c + r.cost_per_unit) AS cost
RETURN [n IN nodes(p) | coalesce(n.code, n.id)] AS route,
       [r IN relationships(p) | coalesce(r.mode, 'last-mile')] AS modes,
       round(lead, 1) AS lead_time_days, round(cost, 2) AS cost_per_unit
ORDER BY CASE WHEN $order_by = 'cost' THEN cost ELSE lead END, lead, cost
LIMIT $k
