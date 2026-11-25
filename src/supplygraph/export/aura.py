"""Copy the GDS-enriched local graph to AuraDB Free (credentials from .env: AURA_URI / AURA_PASSWORD).

1. Count local nodes/relationships and refuse if they do not fit the Aura Free limits.
2. Apply the schema on Aura, then copy nodes (all properties, incl. betweenness / pagerank /
   community_id / criticality_index written by GDS) and relationships in batches with MERGE.
The public app then needs no GDS at runtime.
"""

from __future__ import annotations

import time
from collections import defaultdict

from rich.console import Console

from supplygraph.config import load_network_config
from supplygraph.db import batched, cypher25, driver_ctx, run, run_file

console = Console()
KEYS = {
    "Country": "iso2",
    "Port": "code",
    "Supplier": "id",
    "Item": "sku",
    "Plant": "id",
    "DC": "id",
    "Hospital": "id",
    "Lot": "lot_id",
}
REL_MERGE_KEYS = {"BUYS_FROM": ["item_sku", "for_sku"]}


def _primary_label(labels: list[str]) -> str:
    return next(lbl for lbl in labels if lbl in KEYS)


def export(dry_run: bool = False, batch_size: int = 2000) -> None:
    limits = load_network_config("full").aura_limits
    with driver_ctx("local") as src:
        n = run(src, "MATCH (n) RETURN count(n) AS c")[0]["c"]
        r = run(src, "MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        console.print(
            f"local graph: {n:,} nodes ({100 * n / limits['nodes']:.1f}% of Aura Free), "
            f"{r:,} relationships ({100 * r / limits['relationships']:.1f}%)"
        )
        if n > limits["nodes"] or r > limits["relationships"]:
            raise SystemExit("graph does not fit AuraDB Free - generate a smaller profile")
        enriched = run(src, "MATCH (s:Supplier) WHERE s.criticality_index IS NOT NULL RETURN count(s) AS c")[
            0
        ]["c"]
        if not enriched:
            console.print(
                "[yellow]warning:[/] no GDS / criticality properties found - run `sgraph analyze` first"
            )
        if dry_run:
            console.print("[green]dry run OK[/] - fits the Aura Free limits")
            return
        with driver_ctx("aura") as dst:
            t0 = time.perf_counter()
            run_file(dst, "00_schema.cypher")
            for label, key in KEYS.items():
                rows = run(src, f"MATCH (n:{label}) RETURN properties(n) AS p, labels(n) AS l")
                by_labels = defaultdict(list)
                for row in rows:
                    by_labels[tuple(sorted(row["l"]))].append(row["p"])
                for labels, props in by_labels.items():
                    extra = "".join(f":{x}" for x in labels if x != label)
                    q = cypher25(
                        f"UNWIND $rows AS row MERGE (n:{label} {{{key}: row.{key}}}) SET n += row"
                        + (f" SET n{extra}" if extra else "")
                    )
                    with dst.session(database="neo4j") as s:
                        for chunk in batched(props, batch_size):
                            s.execute_write(lambda tx, c=chunk, q=q: tx.run(q, rows=c).consume())
                console.print(f"  nodes {label:<9} {len(rows):>7,}")
            types = [
                x["t"] for x in run(src, "CALL db.relationshipTypes() YIELD relationshipType AS t RETURN t")
            ]
            for rtype in types:
                rows = run(
                    src,
                    f"""MATCH (a)-[r:{rtype}]->(b)
                                   RETURN labels(a) AS la, labels(b) AS lb, properties(a) AS pa, properties(b) AS pb,
                                          properties(r) AS pr""",
                    timeout=600,
                )
                groups = defaultdict(list)
                for x in rows:
                    la, lb = _primary_label(x["la"]), _primary_label(x["lb"])
                    groups[(la, lb)].append({"a": x["pa"][KEYS[la]], "b": x["pb"][KEYS[lb]], "p": x["pr"]})
                mk = REL_MERGE_KEYS.get(rtype, [])
                merge_props = "{" + ", ".join(f"{k}: row.p.{k}" for k in mk) + "}" if mk else ""
                for (la, lb), rr in groups.items():
                    q = cypher25(f"""UNWIND $rows AS row
                        MATCH (a:{la} {{{KEYS[la]}: row.a}}) MATCH (b:{lb} {{{KEYS[lb]}: row.b}})
                        MERGE (a)-[r:{rtype} {merge_props}]->(b) SET r += row.p""")
                    with dst.session(database="neo4j") as s:
                        for chunk in batched(rr, batch_size):
                            s.execute_write(lambda tx, c=chunk, q=q: tx.run(q, rows=c).consume())
                console.print(f"  rels  {rtype:<15} {len(rows):>7,}")
            n2 = run(dst, "MATCH (n) RETURN count(n) AS c")[0]["c"]
            r2 = run(dst, "MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
            console.print(
                f"[green]Aura now has[/] {n2:,} nodes / {r2:,} relationships "
                f"(copied in {time.perf_counter() - t0:.0f}s)"
            )
