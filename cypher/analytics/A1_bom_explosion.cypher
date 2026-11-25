// 9A - "What is this implant made of, at every level?"
// Business question: full multi-level BOM explosion of one finished SKU with the gross quantity
// of every component / raw material needed per implant.
// Why graph: a variable-length path walks every BOM level in one pattern; in SQL this is a
// recursive CTE whose depth you must bound and debug by hand.
// Logic: every path child -> ... -> $sku is one way the child enters the product. The quantity
// along a path is the PRODUCT of qty_per on its relationships (reduce). The same child can enter
// through several sub-assemblies, so we SUM over paths and keep the shallowest level.
MATCH p = (c:Item)-[:COMPONENT_OF]->{1,12}(f:Item {sku: $sku})
WITH c, length(p) AS level, reduce(q = 1.0, r IN relationships(p) | q * r.qty_per) AS qty
RETURN c.sku AS sku, c.name AS name, c.type AS type, min(level) AS bom_level,
       count(*) AS paths, round(sum(qty), 4) AS qty_per_implant,
       COUNT { (:Supplier)-[:SUPPLIES]->(c) } AS n_suppliers
ORDER BY bom_level, sku
