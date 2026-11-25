// FAIL on nodes that are orphans where the business says they cannot be:
// a supplier that supplies nothing, a hospital no DC serves, a DC that stocks nothing.
MATCH (s:Supplier) WHERE NOT EXISTS { (s)-[:SUPPLIES]->(:Item) }
RETURN 'Supplier' AS label, s.id AS id
UNION ALL
MATCH (h:Hospital) WHERE NOT EXISTS { (:DC)-[:SERVES]->(h) }
RETURN 'Hospital' AS label, h.id AS id
UNION ALL
MATCH (d:DC) WHERE NOT EXISTS { (d)-[:STOCKS]->(:Item) }
RETURN 'DC' AS label, d.id AS id
