# Versions and limits (checked 2026-11-25)

Checked against official sources on the day the project was built; nothing here comes from memory.

| Component | Version used | Source checked |
|---|---|---|
| Neo4j Community (Docker image) | `neo4j:2026.10.2-community` | Docker Hub tag list `library/neo4j` (tags `2026.10.2-community`, `2026.10`, `community`, all updated 2026-11-24) |
| Neo4j Community (portable zip, used locally) | `2026.10.2` (`neo4j-community-2026.10.2-windows.zip`, SHA-256 verified) | dist.neo4j.org + `.sha256` |
| Java runtime (portable) | Eclipse Temurin JDK `21.0.13.1+2` (SHA-256 verified) | Adoptium API. Neo4j 2025.10+ supports Java SE 21 and 25 (Operations Manual, "System requirements") |
| Graph Data Science plugin | `2026.10.2` | GitHub releases `neo4j/graph-data-science` + compatibility matrix `graphdatascience.ninja/versions.json` (2026.10.2 ↔ Neo4j 2026.10.2) |
| APOC (core) | `2026.10.2` | GitHub releases `neo4j/apoc` |
| Python driver `neo4j` | `6.4.1` | PyPI |
| `graphdatascience` client | `2.4` | PyPI (note: 2.x uses a snake_case API, e.g. `gds.page_rank.write(G, write_property=...)`) |
| Python | 3.12 (managed by `uv` 0.13.9) | local |
| DuckDB | `2.0.1` | PyPI |
| Streamlit | `1.67.0` | PyPI |
| neo4j-viz | `1.13.0` | PyPI |
| pandas / numpy | `3.1.1` / `2.5.5` | PyPI |
| Typer / pydantic / ruff / pytest | `0.29.2` / `2.14.4` / `0.17.6` / `9.2.0` | PyPI |

Cypher: the server reports Cypher versions `5` and `25`. Every query in this repo is sent as **Cypher 25**
(`supplygraph.db.cypher25` adds the `CYPHER 25` prefix). Cypher-25-only features used: `allReduce()` (introduced in
2025.08) for early pruning inside quantified path patterns, `CALL () {}` scoped subqueries, `OPTIONAL CALL`,
`COUNT {}` / `EXISTS {}` subqueries, quantified path patterns `-[:R]->{1,12}`.

## AuraDB Free limits

| Limit | Value | Source |
|---|---|---|
| Nodes | 200,000 | Neo4j docs "AuraDB quotas and limits" (neo4j.com/docs/aura/quotas-and-limits) |
| Relationships | 400,000 | same |
| Storage | 1 GB | same |
| Inactivity | instance pauses when idle (docs mention pause after ~3 days and deletion after 30 days of inactivity - check the Aura console for the current policy) | Neo4j FAQ pages |

**Difference from the original brief:** the brief said "GDS does not run on Aura Free". The current Neo4j changelog
announces **Aura Graph Analytics available on AuraDB Free** (serverless GDS sessions, billed separately from the
database). The in-database GDS *plugin* is still not part of AuraDB Free, so this project keeps the original design:
compute GDS locally and write the results as properties. See [ADR-009](decisions/ADR-009-precompute-gds.md).

## Project graph size (profile `full`, seed 42)

| | Count | % of Aura Free |
|---|---:|---:|
| Nodes | 58,978 | 29.5% |
| Relationships | 231,984 | 58.0% |

Relationships are the binding constraint (the model has ~3.9 relationships per node, mostly lot genealogy and
deliveries), so the network is sized to ~58% of the relationship limit, which leaves room for the GDS-written
`SIMILAR_PORTFOLIO` relationships. Run `sgraph stats` to recount.
