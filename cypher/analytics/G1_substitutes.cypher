// 9G - Substitution: for the finished items short in a scenario, the qualified alternatives that
// are NOT hit by the same disruption, with requalification time and stock at the same DC.
UNWIND $shortages AS s
MATCH (f:Item {sku: s.sku})-[c:CAN_SUBSTITUTE]->(g:Item)
WHERE NOT g.sku IN $affected_skus
OPTIONAL MATCH (:DC {id: s.dc})-[st:STOCKS]->(g)
RETURN s.sku AS sku, s.dc AS dc, g.sku AS substitute, g.name AS substitute_name,
       c.requalification_days AS requalification_days, coalesce(st.on_hand, 0) AS substitute_on_hand
ORDER BY sku, dc, requalification_days
