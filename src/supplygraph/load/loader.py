"""Idempotent transactional loader: UNWIND $rows AS row MERGE ... in batches.

Every write runs inside a managed transaction (`session.execute_write`) so the driver retries
transient errors. Running the load twice produces the same graph (MERGE on business keys).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import pandas as pd
from neo4j import Driver
from rich.console import Console

from supplygraph.db import batched, cypher25, database_of, run_file

console = Console()


@dataclass(frozen=True)
class NodeSpec:
    table: str
    label: str
    key: str
    extra_set: str = ""


@dataclass(frozen=True)
class RelSpec:
    table: str
    query: str


NODE_SPECS = [
    NodeSpec("countries", "Country", "iso2"),
    NodeSpec("ports", "Port", "code"),
    NodeSpec("suppliers", "Supplier", "id"),
    NodeSpec("items", "Item", "sku"),
    NodeSpec("plants", "Plant", "id"),
    NodeSpec("dcs", "DC", "id"),
    NodeSpec("hospitals", "Hospital", "id"),
    NodeSpec(
        "lots", "Lot", "lot_id", "SET n.mfg_date = date(row.mfg_date), n.expiry_date = date(row.expiry_date)"
    ),
]

REL_SPECS = [
    RelSpec(
        "supplies",
        """
        UNWIND $rows AS row
        MATCH (a:Supplier {id: row.supplier_id})
        MATCH (b:Item {sku: row.item_sku})
        MERGE (a)-[r:SUPPLIES]->(b)
        SET r += row{.share_pct, .lead_time_days, .unit_price, .moq}""",
    ),
    RelSpec(
        "buys_from",
        """
        UNWIND $rows AS row
        MATCH (a:Supplier {id: row.buyer_id})
        MATCH (b:Supplier {id: row.seller_id})
        MERGE (a)-[r:BUYS_FROM {item_sku: row.item_sku, for_sku: row.for_sku}]->(b)
        SET r += row{.share_pct, .lead_time_days}""",
    ),
    RelSpec(
        "bom",
        """
        UNWIND $rows AS row
        MATCH (c:Item {sku: row.child_sku})
        MATCH (p:Item {sku: row.parent_sku})
        MERGE (c)-[r:COMPONENT_OF]->(p)
        SET r.qty_per = row.qty_per""",
    ),
    RelSpec(
        "suppliers",
        """
        UNWIND $rows AS row
        MATCH (n:Supplier {id: row.id})
        MATCH (c:Country {iso2: row.country_iso2})
        MERGE (n)-[:LOCATED_IN]->(c)""",
    ),
    RelSpec(
        "plants",
        """
        UNWIND $rows AS row
        MATCH (n:Plant {id: row.id})
        MATCH (c:Country {iso2: row.country_iso2})
        MERGE (n)-[:LOCATED_IN]->(c)""",
    ),
    RelSpec(
        "ports",
        """
        UNWIND $rows AS row
        MATCH (n:Port {code: row.code})
        MATCH (c:Country {iso2: row.country_iso2})
        MERGE (n)-[:LOCATED_IN]->(c)""",
    ),
    RelSpec(
        "manufactures",
        """
        UNWIND $rows AS row
        MATCH (a:Plant {id: row.plant_id})
        MATCH (b:Item {sku: row.item_sku})
        MERGE (a)-[r:MANUFACTURES]->(b)
        SET r += row{.capacity_month, .share_pct}""",
    ),
    RelSpec(
        "stocks",
        """
        UNWIND $rows AS row
        MATCH (a:DC {id: row.dc_id})
        MATCH (b:Item {sku: row.item_sku})
        MERGE (a)-[r:STOCKS]->(b)
        SET r += row{.on_hand, .avg_daily_demand, .safety_stock, .transit_days}""",
    ),
    RelSpec(
        "serves",
        """
        UNWIND $rows AS row
        MATCH (a:DC {id: row.dc_id})
        MATCH (b:Hospital {id: row.hospital_id})
        MERGE (a)-[r:SERVES]->(b)
        SET r += row{.lead_time_days, .cost_per_unit, .is_primary}""",
    ),
    RelSpec(
        "consumes",
        """
        UNWIND $rows AS row
        MATCH (a:Hospital {id: row.hospital_id})
        MATCH (b:Item {sku: row.item_sku})
        MERGE (a)-[r:CONSUMES]->(b)
        SET r += row{.monthly_demand, .revenue_month}""",
    ),
    RelSpec(
        "can_substitute",
        """
        UNWIND $rows AS row
        MATCH (a:Item {sku: row.from_sku})
        MATCH (b:Item {sku: row.to_sku})
        MERGE (a)-[r:CAN_SUBSTITUTE]->(b)
        SET r.requalification_days = row.requalification_days""",
    ),
    RelSpec(
        "lots",
        """
        UNWIND $rows AS row
        MATCH (l:Lot {lot_id: row.lot_id})
        MATCH (i:Item {sku: row.item_sku})
        MERGE (l)-[:OF_ITEM]->(i)""",
    ),
    RelSpec(
        "derived_from",
        """
        UNWIND $rows AS row
        MATCH (c:Lot {lot_id: row.child_lot_id})
        MATCH (p:Lot {lot_id: row.parent_lot_id})
        MERGE (c)-[r:DERIVED_FROM]->(p)
        SET r.qty_used = row.qty_used""",
    ),
    RelSpec(
        "delivered_to",
        """
        UNWIND $rows AS row
        MATCH (l:Lot {lot_id: row.lot_id})
        MATCH (h:Hospital {id: row.hospital_id})
        MERGE (l)-[r:DELIVERED_TO]->(h)
        SET r.date = date(row.date), r.qty = row.qty""",
    ),
]

SHIPS_KEYS = {"Plant": "id", "Port": "code", "DC": "id"}


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of dicts with NaN converted to None and numpy scalars to python."""
    out = []
    cols = list(df.columns)
    for row in df.itertuples(index=False, name=None):
        rec = {}
        for c, v in zip(cols, row, strict=True):
            if isinstance(v, float) and math.isnan(v):
                v = None
            elif hasattr(v, "item"):
                v = v.item()
            rec[c] = v
        out.append(rec)
    return out


def _write(driver: Driver, query: str, rows: list[dict], batch_size: int) -> None:
    q = cypher25(query)
    db = database_of(driver)
    with driver.session(database=db) as session:
        for chunk in batched(rows, batch_size):
            session.execute_write(lambda tx, c=chunk: tx.run(q, rows=c).consume())


def apply_schema(driver: Driver) -> int:
    return run_file(driver, "00_schema.cypher")


def load_tables(driver: Driver, tables: dict[str, pd.DataFrame], batch_size: int = 5000) -> dict[str, float]:
    """Load all node and relationship tables. Returns seconds spent per step."""
    timings: dict[str, float] = {}
    apply_schema(driver)
    for spec in NODE_SPECS:
        df = tables.get(spec.table)
        if df is None or df.empty:
            continue
        t0 = time.perf_counter()
        q = f"UNWIND $rows AS row MERGE (n:{spec.label} {{{spec.key}: row.{spec.key}}}) SET n += row {spec.extra_set}"
        _write(driver, q, _records(df), batch_size)
        timings[f"node:{spec.label}"] = time.perf_counter() - t0
        console.print(
            f"  [green]ok[/] {spec.label:<10} {len(df):>7,} nodes  {timings[f'node:{spec.label}']:.1f}s"
        )
    for spec in REL_SPECS:
        df = tables.get(spec.table)
        if df is None or df.empty:
            continue
        t0 = time.perf_counter()
        _write(driver, spec.query, _records(df), batch_size)
        timings[f"rel:{spec.table}"] = time.perf_counter() - t0
        console.print(
            f"  [green]ok[/] {spec.table:<15} {len(df):>7,} rows   {timings[f'rel:{spec.table}']:.1f}s"
        )
    ships = tables.get("ships_to")
    if ships is not None and not ships.empty:
        t0 = time.perf_counter()
        for (ft, tt), grp in ships.groupby(["from_type", "to_type"], sort=True):
            q = f"""
            UNWIND $rows AS row
            MATCH (a:{ft} {{{SHIPS_KEYS[ft]}: row.from_id}})
            MATCH (b:{tt} {{{SHIPS_KEYS[tt]}: row.to_id}})
            MERGE (a)-[r:SHIPS_TO]->(b)
            SET r += row{{.mode, .lead_time_days, .cost_per_unit}}"""
            _write(driver, q, _records(grp), batch_size)
        timings["rel:ships_to"] = time.perf_counter() - t0
    run_file(driver, "01_enrich.cypher")
    return timings


def reset(driver: Driver) -> None:
    """Delete everything (data + GDS-written props) in batches; keep the schema."""
    db = database_of(driver)
    with driver.session(database=db) as s:
        s.run("CYPHER 25 MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS").consume()


def count_graph(driver: Driver) -> tuple[int, int]:
    db = database_of(driver)
    with driver.session(database=db) as s:
        n = s.run("CYPHER 25 MATCH (n) RETURN count(n) AS c").single()["c"]
        r = s.run("CYPHER 25 MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    return n, r
