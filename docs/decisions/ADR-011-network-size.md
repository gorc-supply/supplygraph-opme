# ADR-011: Size the network on the relationship limit

- Status: accepted
- Date: 2026-11-25

**Context.** The brief asks for 40-60% of the Aura Free limits. The model has about 3.9 relationships per node (lot
genealogy and deliveries dominate), so both targets cannot be met at the same time.

**Decision.** Size on the binding constraint: profile `full` = 231,984 relationships (58.0%) and 58,978 nodes
(29.5%). `sgraph stats` prints both against the limits.
