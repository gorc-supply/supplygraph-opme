# Plan (phase 0)

Recorded at the start of the build (2026-11-25), updated with what changed during execution.

## Environment found

| Tool | Status | Action |
|---|---|---|
| Docker Desktop | **not installed** | Portable Neo4j (JDK 21 + Neo4j zip + plugins) in `.runtime/` - [ADR-006](decisions/ADR-006-portable-neo4j.md); `docker-compose.yml` kept for when Docker is installed |
| Python | not on PATH (Windows Store alias only) | `uv` 0.13.9 provides CPython 3.12 |
| uv | 0.13.9 | used for the venv and lock file |
| git / gh | 2.56 / 2.105, gh logged in as `gorc-supply` | repo created locally |
| WSL2 Ubuntu | present, no Docker, no sudo | not used |
| RAM / CPU | 32 GB / 16 threads | Neo4j heap 2 GB, page cache 1 GB |

Versions confirmed online: see [VERSIONS.md](VERSIONS.md).

## Model adjustments vs the brief

1. `BUYS_FROM (Supplier)->(Supplier) {item_sku, for_sku, share_pct}` added to make sub-tier sourcing explicit
   (false dual-source detection) - [ADR-003](decisions/ADR-003-buys-from.md).
2. `Lot.status` gains `expired`; `Lot.source_id` stores the producing supplier/plant.
3. `MANUFACTURES.share_pct`, `SERVES.is_primary`, `SERVES.cost_per_unit`, `STOCKS.transit_days`,
   `Item.pipeline_lead_days`, `Item.level`, `Item.category/family` added for the analyses.
4. `:Critical` extra label for HIGH-criticality items.

## Phases

| Phase | Deliverable | Command |
|---|---|---|
| 0 | this plan, VERSIONS.md | - |
| 1 | repo, pyproject, Neo4j + APOC + GDS up, schema, CLI | `sgraph setup-portable`, `sgraph up` |
| 2 | generator + anchors, graph & tabular CSVs, size vs Aura | `sgraph fetch-anchors`, `sgraph generate`, `sgraph stats` |
| 3 | idempotent load, driver vs `neo4j-admin import`, quality checks | `sgraph load`, `sgraph bulk-import`, `sgraph validate` |
| 4 | analyses 9A-9G with numbers and recommendations | `sgraph analyze --step cypher` -> [analysis.md](analysis.md) |
| 5 | GDS + criticality index + sensitivity | `sgraph analyze --step gds` |
| 6 | Cypher vs DuckDB benchmark | `sgraph benchmark` -> [benchmarks.md](benchmarks.md) |
| 7 | Streamlit app, 6 pages | `streamlit run app/streamlit_app.py` |
| 8 | public repo, CI, READMEs, Aura export + Streamlit deploy ready | see [deploy.md](deploy.md) |
| 9 | portfolio material | [portfolio/](portfolio/) |
