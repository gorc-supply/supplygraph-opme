# ADR-013: Calibration of the sourcing parameters

- Status: accepted
- Date: 2026-11-25

**Context.** The first parameter set produced hidden convergence in 81% of the multi-sourced items and 96% of the
revenue - not credible.

**Decision.** Lower deep single-sourcing (tier-2 supplier count probabilities 8/52/40%), make sub-tier buyers pick a
source with probability proportional to the square root of market share, single-source sub-tier purchases in 20% of
cases, and plant 10% of the multi-sourced items as deliberate false dual-sources. Result: 35% of multi-sourced
level-1 items converge on one upstream supplier.

**Consequences.** The headline numbers are a product of these assumptions; they live in `config/network.yaml` so
anyone can change them and re-run.
