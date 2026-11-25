# ADR-004: Cypher 25 everywhere and allReduce() for path pruning

- Status: accepted
- Date: 2026-11-25

**Context.** The first version of the false dual-source query (`MATCH (d)-[bs:BUYS_FROM]->{1,6}(u) WHERE all(...)`)
timed out after 300 s: Cypher enumerated every BUYS_FROM path before filtering.

**Decision.** Send all queries as Cypher 25 and express the per-hop BOM constraint with `allReduce()` (Cypher 25,
Neo4j 2025.08+), which the planner inlines into the quantified path pattern and evaluates while expanding. For the
blast radius, expand from the disrupted supplier outwards (anchored on its id) with the mirrored constraint.

**Consequences.** False dual-source: more than 300 s down to about 5 s; one supplier scenario: 2.6 s down to 0.3 s;
ranking all 244 suppliers: about 30 s. Queries require Neo4j 2025.08+ (Aura always runs the current version).
