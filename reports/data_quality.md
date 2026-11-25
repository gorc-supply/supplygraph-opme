# Data quality report

- Generated: 2026-11-25 23:11 UTC
- Profile: `full`  ·  Graph: 60,560 nodes / 238,873 relationships
- Result: **9/9 checks passed**

| # | Check | Status | Violations | Time (ms) |
|---|---|---|---:|---:|
| 01 | BOM (COMPONENT_OF) has no cycles | PASS | 0 | 4120 |
| 02 | Every finished item has a BOM path down to raw material | PASS | 0 | 5 |
| 03 | Every item has a supplier (purchased) or a plant (finished) | PASS | 0 | 4 |
| 04 | Supplier shares sum to 100% per item (and per sub-tier buyer) | PASS | 0 | 13 |
| 05 | No orphan suppliers, hospitals without a DC, or DCs without stock | PASS | 0 | 6 |
| 06 | Every finished lot traces back to a raw-material lot | PASS | 0 | 238 |
| 07 | No expired lot is still 'released' | PASS | 0 | 20 |
| 08 | Deliveries never exceed lot quantity | PASS | 0 | 66 |
| 09 | Child lots are never older than their parent lots | PASS | 0 | 69 |

Each check lives in `cypher/validation/` and returns the violating rows (0 rows = pass).
