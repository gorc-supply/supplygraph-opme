// 9B - The "false dual-source": items that LOOK multi-sourced in the ERP but whose tier-1
// suppliers all depend on the SAME upstream supplier for a sub-component.
// Why graph: the dependency is a chain of BUYS_FROM hops whose item must follow the BOM
// (supplier d buys child C *for* item i, d's supplier buys C's child *for* C, ...). That is a
// pattern with a per-hop condition - natural in Cypher, a self-join per tier in SQL.
// $strict = true  -> every hop must be a sole source (share >= 99.9%): a real single point of failure
// $strict = false -> any share: the upstream supplier touches every "alternative"
MATCH (i:Item {type: 'COMPONENT', level: 1})<-[:SUPPLIES]-(d:Supplier)
WITH i, collect(d) AS direct
WHERE size(direct) >= 2
UNWIND direct AS d
// Chain of sub-tier purchases starting at d: hop k+1 must buy the child FOR the item of hop k.
// allReduce() carries "the item the next hop must be bought for" as an accumulator and is
// checked at every step, so the planner prunes invalid chains DURING expansion instead of
// enumerating every BUYS_FROM path first (which explodes combinatorially).
MATCH (d)-[bs:BUYS_FROM]->{1,6}(u:Supplier)
WHERE allReduce(acc = {next: i.sku, ok: true}, b IN bs |
        {next: b.item_sku, ok: b.for_sku = acc.next AND ($strict = false OR b.share_pct >= 99.9)},
        acc.ok)
WITH i, direct, u, collect(DISTINCT d.id) AS dependent, collect(DISTINCT last(bs).item_sku) AS via_items,
     min(size(bs)) AS hops
WHERE size(dependent) = size(direct)
// revenue that stops if u stops: every finished implant whose BOM contains i
CALL (i) {
  MATCH (i)-[:COMPONENT_OF]->{1,12}(f:Item {type: 'FINISHED'})
  WITH DISTINCT f
  RETURN sum(f.revenue_month) AS revenue_exposed, count(f) AS finished_affected
}
RETURN i.sku AS item_sku, i.name AS item_name, i.category AS category,
       [x IN direct | x.id] AS direct_suppliers, [x IN direct | x.country_iso2] AS direct_countries,
       u.id AS hidden_supplier, u.tier AS hidden_tier, u.country_iso2 AS hidden_country,
       via_items, hops, revenue_exposed, finished_affected
ORDER BY revenue_exposed DESC, item_sku, hidden_supplier
