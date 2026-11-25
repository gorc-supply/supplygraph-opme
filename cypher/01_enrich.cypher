// Post-load enrichment (idempotent).
// :Critical is an extra label (not just a property) because "show me critical items" is the
// most frequent filter in the app: a label scan is cheaper than a property predicate and
// reads naturally in patterns like (i:Item:Critical).
MATCH (i:Item) WHERE i.criticality = 'HIGH' SET i:Critical;
MATCH (i:Item:Critical) WHERE i.criticality <> 'HIGH' REMOVE i:Critical;
