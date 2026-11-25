// 9A - "If raw material / component $sku goes missing, which finished implants stop?"
// Where-used is the same path read in the opposite direction: from the item UP to every
// finished product that contains it, with the revenue those products bring every month.
MATCH p = (x:Item {sku: $sku})-[:COMPONENT_OF]->{1,12}(f:Item {type: 'FINISHED'})
WITH f, min(length(p)) AS levels_above,
     sum(reduce(q = 1.0, r IN relationships(p) | q * r.qty_per)) AS qty_per_implant
RETURN f.sku AS finished_sku, f.name AS name, f.category AS category, levels_above,
       round(qty_per_implant, 4) AS qty_per_implant, f.revenue_month AS revenue_month,
       COUNT { (:Hospital)-[:CONSUMES]->(f) } AS hospitals
ORDER BY revenue_month DESC
