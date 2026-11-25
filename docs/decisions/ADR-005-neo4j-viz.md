# ADR-005: neo4j-viz for the network explorer

- Status: accepted
- Date: 2026-11-25

**Options.** `neo4j-viz` 1.13 (Neo4j's official library, released 2026-11), `streamlit-agraph` 0.0.45 (last release
2023-01), `pyvis` 0.3.2 (last release 2023-02).

**Decision.** neo4j-viz: maintained, renders the NVL canvas used by Neo4j's own tools, supports colour and size per
node and exports self-contained HTML that Streamlit embeds with `components.html`.

**Consequences.** One extra dependency; the alternatives would bring unmaintained code into a public portfolio.
