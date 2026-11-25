# ADR-009: Compute GDS locally and write results as properties

- Status: accepted
- Date: 2026-11-25

**Context.** AuraDB Free has no in-database GDS plugin. (Neo4j now offers Aura Graph Analytics sessions, also on the
Free tier, but as a separate serverless product.)

**Decision.** Run all algorithms locally with the `graphdatascience` client, `.write` the results (`betweenness`,
`pagerank`, `component_id`, `community_id`, `SIMILAR_PORTFOLIO`, `criticality_index`, `revenue_at_risk`) and copy the
enriched graph to Aura with `sgraph export-aura`. Projections are always dropped in a `finally` block.

**Consequences.** The public app needs no GDS; values are a snapshot (re-run `sgraph analyze` and the export to
refresh them).
