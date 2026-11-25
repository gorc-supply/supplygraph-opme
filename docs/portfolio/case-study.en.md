# Case study - SupplyGraph OPME

**Seeing the suppliers the ERP cannot see: a graph digital twin of an implant supply chain**

## Problem

Implant (OPME) supply chains are deep: a hip stem depends on a machining shop, which depends on a forging house,
which depends on a handful of mills that make medical-grade titanium. Purchasing systems only show the first
link. Risk reviews built on that view miss the suppliers that can actually stop the business - and when a
material lot fails inspection, tracing it to patients takes days.

## Approach

- Built a **graph digital twin** in Neo4j (Community 2026.10, Cypher 25): 244 suppliers in three tiers,
  869 items in a multi-level BOM, plants, ports, 14 Brazilian DCs, 1,400 hospitals and 58k lots with full
  genealogy - **synthetic data (fixed seed) calibrated with real open data** (Brazil's 2024 implant imports by
  origin, official NCM codes, IBGE municipalities).
- Modelled what the ERP lacks: **which tier-2 each tier-1 actually buys from** (`BUYS_FROM`), so hidden
  convergence becomes a query.
- Wrote seven business analyses in commented Cypher, a **TTS x TTR** (Simchi-Levi) disruption simulator, GDS
  algorithms (betweenness, PageRank, Leiden, node similarity, Dijkstra/Yen) and a weighted **supplier
  criticality index** with sensitivity analysis.
- Engineered it like production: deterministic generator, idempotent loader, 9 data-quality checks as tests,
  CI with Neo4j as a service container, a Streamlit app ready for AuraDB Free.
- **Benchmarked graph vs relational** (DuckDB recursive CTEs) on the same three questions - and published the
  result even though DuckDB won on speed.

## Results (synthetic network)

1. **China: 0.4% -> 43.6%.** Share of revenue that cannot be produced without China in the ERP view vs the graph view.
2. **29% false dual-source.** 66 of 224 components with two or more suppliers converge 100% on one upstream
   supplier; they feed 53% of revenue.
3. **Top 10 risks are invisible to the ERP.** The 10 suppliers with the highest revenue at risk are all tier-2/3;
   the first tier-1 ranks #74. The worst (a titanium-bar producer) leaves 35 days of cover against a 180-day recovery.
4. **Recall in 19 ms**: one titanium lot -> 105 implant lots, 180 hospitals in 26 states, 684 units to quarantine.

## Impact

For a supply-chain director: a ranked list of the suppliers to put under a risk programme (not the top by spend),
a quantified case for strategic raw-material stock, the 66 items that need a truly independent second source,
and a recall perimeter in milliseconds instead of days. For an engineering reviewer: a reproducible, tested
graph pipeline and an honest measurement of when a graph is - and is not - the right tool.

Repository: https://github.com/gorc-supply/supplygraph-opme
