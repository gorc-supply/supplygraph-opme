// SupplyGraph OPME - schema (idempotent: safe to run many times).
// Uniqueness constraints give us an index on every business key, which is what MERGE
// and every point lookup in the app use. Extra range indexes cover the common filters.

CREATE CONSTRAINT country_iso2 IF NOT EXISTS FOR (n:Country) REQUIRE n.iso2 IS UNIQUE;
CREATE CONSTRAINT port_code IF NOT EXISTS FOR (n:Port) REQUIRE n.code IS UNIQUE;
CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (n:Supplier) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT item_sku IF NOT EXISTS FOR (n:Item) REQUIRE n.sku IS UNIQUE;
CREATE CONSTRAINT plant_id IF NOT EXISTS FOR (n:Plant) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT dc_id IF NOT EXISTS FOR (n:DC) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT hospital_id IF NOT EXISTS FOR (n:Hospital) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT lot_id IF NOT EXISTS FOR (n:Lot) REQUIRE n.lot_id IS UNIQUE;

CREATE INDEX supplier_tier IF NOT EXISTS FOR (n:Supplier) ON (n.tier);
CREATE INDEX supplier_country IF NOT EXISTS FOR (n:Supplier) ON (n.country_iso2);
CREATE INDEX item_type IF NOT EXISTS FOR (n:Item) ON (n.type);
CREATE INDEX item_category IF NOT EXISTS FOR (n:Item) ON (n.category);
CREATE INDEX item_level IF NOT EXISTS FOR (n:Item) ON (n.level);
CREATE INDEX lot_item IF NOT EXISTS FOR (n:Lot) ON (n.item_sku);
CREATE INDEX lot_status IF NOT EXISTS FOR (n:Lot) ON (n.status);
CREATE INDEX hospital_uf IF NOT EXISTS FOR (n:Hospital) ON (n.uf);
CREATE INDEX buys_from_item IF NOT EXISTS FOR ()-[r:BUYS_FROM]-() ON (r.item_sku);
CREATE INDEX buys_from_for IF NOT EXISTS FOR ()-[r:BUYS_FROM]-() ON (r.for_sku);
