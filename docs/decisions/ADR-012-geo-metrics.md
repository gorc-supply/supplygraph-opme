# ADR-012: Two geographic exposure metrics

- Status: accepted
- Date: 2026-11-25

**Context.** "Revenue exposed to country X if ANY input comes from X" saturates near 100% for every big country once
all tiers are visible - true but useless.

**Decision.** Report (a) **hard dependency**: revenue of implants with at least one input sourced 100% from the
country (they cannot be produced without it), and (b) **weighted exposure**: the revenue-weighted largest share of
any single input coming from the country. Both in an ERP view (plant + level-1 components) and a graph view (all
levels).

**Consequences.** (a) is the headline (clear and conservative); (b) is in the app and the reports.
