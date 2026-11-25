# ADR-001: Graph database (Neo4j) for supply-chain risk

- Status: accepted
- Date: 2026-11-25

**Context.** The questions that matter (which tier-3 supplier I do not know about can stop 40% of revenue? where did
this titanium heat end up?) are traversals of unknown depth across BOM, sourcing and logistics.

**Decision.** Model the network as a property graph in Neo4j and answer the questions in Cypher; keep a tabular copy
in DuckDB to *measure* the claim instead of asserting it ([benchmarks](../benchmarks.md)).

**Consequences.** Variable-length patterns replace recursive CTEs; graph algorithms (GDS) become available. The
benchmark reports honestly where the relational engine is faster.
