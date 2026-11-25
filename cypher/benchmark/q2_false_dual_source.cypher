// Q2 - False dual-source (strict): level-1 items with >= 2 direct suppliers where every
// direct supplier depends 100% (at every hop) on the same upstream supplier, following
// BOM-consistent BUYS_FROM chains. Returns (item, upstream) pairs and distinct items.
MATCH (i:Item {type: 'COMPONENT', level: 1})<-[:SUPPLIES]-(d:Supplier)
WITH i, collect(d) AS direct
WHERE size(direct) >= 2
UNWIND direct AS d
MATCH (d)-[bs:BUYS_FROM]->{1,6}(u:Supplier)
WHERE allReduce(acc = {next: i.sku, ok: true}, b IN bs |
        {next: b.item_sku, ok: b.for_sku = acc.next AND b.share_pct >= 99.9}, acc.ok)
WITH i, size(direct) AS n, u, count(DISTINCT d) AS dependent
WHERE dependent = n
RETURN count(*) AS pairs, count(DISTINCT i) AS checksum
