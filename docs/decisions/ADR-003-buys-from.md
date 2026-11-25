# ADR-003: Add BUYS_FROM (Supplier)->(Supplier) with item_sku and for_sku

- Status: accepted
- Date: 2026-11-25

**Context.** With only `(Supplier)-[:SUPPLIES]->(Item)` the model knows who *can* supply a sub-component, not which
tier-2 each tier-1 actually buys from - so a false dual-source is undetectable.

**Decision.** Add `BUYS_FROM` with `item_sku` (what is bought), `for_sku` (the item it goes into) and `share_pct`.
A sub-tier chain is valid only if hop k+1 buys FOR the item bought in hop k (BOM-consistent).

**Consequences.** About 4.6k extra relationships. Enables section 9B, the sub-tier blast radius (9D) and benchmark
questions Q2/Q3.
