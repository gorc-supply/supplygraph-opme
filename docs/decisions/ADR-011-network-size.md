# ADR-011: Size the network on the relationship limit

- Status: accepted
- Date: 2026-11-25

**Context.** The brief asks for 40-60% of the Aura Free limits. The model has about 3.9 relationships per node (lot
genealogy and deliveries dominate), so both targets cannot be met at the same time.

**Decision.** Size on the binding constraint: profile `full` = 238,467 relationships (59.6%) and 60,560 nodes
(30.3%). `sgraph stats` prints both against the limits.
