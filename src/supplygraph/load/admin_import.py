"""Bulk initial load with `neo4j-admin database import full` (offline, much faster for big graphs).

Builds typed-header CSVs from the same normalised tables, stops the server, imports into the
`neo4j` database (overwrite), restarts and applies the schema + enrichment.
Community Edition has a single user database, so the server must be offline during import.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pandas as pd

from supplygraph.config import GENERATED_DIR
from supplygraph.generate.writer import read_tables

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
NODE_FILES = {
    "countries": "Country",
    "ports": "Port",
    "suppliers": "Supplier",
    "items": "Item",
    "plants": "Plant",
    "dcs": "DC",
    "hospitals": "Hospital",
    "lots": "Lot",
}
DATE_COLS = {"mfg_date", "expiry_date", "date"}


def _typed(col: str, s: pd.Series) -> str:
    if col in DATE_COLS:
        return f"{col}:date"
    if pd.api.types.is_bool_dtype(s):
        return f"{col}:boolean"
    if pd.api.types.is_integer_dtype(s):
        return f"{col}:long"
    if pd.api.types.is_float_dtype(s):
        return f"{col}:double"
    return col


def _write(df: pd.DataFrame, header: list[str], path: Path) -> None:
    out = df.copy()
    out.columns = header
    out.to_csv(path, index=False, encoding="utf-8")


def build_import_files(profile: str) -> tuple[Path, list[str]]:
    t = read_tables(profile)
    out = GENERATED_DIR / profile / "admin_import"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    args: list[str] = []
    for table, label in NODE_FILES.items():
        df = t.get(table)
        if df is None or df.empty:
            continue
        key = KEYS[label]
        hdr = [f"{c}:ID({label})" if c == key else _typed(c, df[c]) for c in df.columns]
        if table == "items":
            df = df.assign(
                extra_labels=["Item;Critical" if c == "HIGH" else "Item" for c in df["criticality"]]
            )
            hdr = hdr + [":LABEL"]
            p = out / "items.csv"
            _write(df, hdr, p)
            args.append(f"--nodes={p}")
            continue
        p = out / f"{table}.csv"
        _write(df, hdr, p)
        args.append(f"--nodes={label}={p}")

    def rel(
        name: str,
        df: pd.DataFrame,
        rtype: str,
        start: tuple[str, str],
        end: tuple[str, str],
        props: list[str],
    ):
        if df is None or df.empty:
            return
        sub = df[[start[0], end[0]] + props]
        hdr = [f":START_ID({start[1]})", f":END_ID({end[1]})"] + [_typed(c, sub[c]) for c in props]
        p = out / f"rel_{name}.csv"
        _write(sub, hdr, p)
        args.append(f"--relationships={rtype}={p}")

    rel(
        "supplies",
        t.get("supplies"),
        "SUPPLIES",
        ("supplier_id", "Supplier"),
        ("item_sku", "Item"),
        ["share_pct", "lead_time_days", "unit_price", "moq"],
    )
    rel(
        "buys_from",
        t.get("buys_from"),
        "BUYS_FROM",
        ("buyer_id", "Supplier"),
        ("seller_id", "Supplier"),
        ["item_sku", "for_sku", "share_pct", "lead_time_days"],
    )
    rel("bom", t.get("bom"), "COMPONENT_OF", ("child_sku", "Item"), ("parent_sku", "Item"), ["qty_per"])
    for table, label, key in (
        ("suppliers", "Supplier", "id"),
        ("plants", "Plant", "id"),
        ("ports", "Port", "code"),
    ):
        rel(f"located_{table}", t.get(table), "LOCATED_IN", (key, label), ("country_iso2", "Country"), [])
    rel(
        "manufactures",
        t.get("manufactures"),
        "MANUFACTURES",
        ("plant_id", "Plant"),
        ("item_sku", "Item"),
        ["capacity_month", "share_pct"],
    )
    ships = t.get("ships_to")
    for (ft, tt), g in ships.groupby(["from_type", "to_type"]):
        rel(
            f"ships_{ft}_{tt}",
            g,
            "SHIPS_TO",
            ("from_id", ft),
            ("to_id", tt),
            ["mode", "lead_time_days", "cost_per_unit"],
        )
    rel(
        "stocks",
        t.get("stocks"),
        "STOCKS",
        ("dc_id", "DC"),
        ("item_sku", "Item"),
        ["on_hand", "avg_daily_demand", "safety_stock", "transit_days"],
    )
    rel(
        "serves",
        t.get("serves"),
        "SERVES",
        ("dc_id", "DC"),
        ("hospital_id", "Hospital"),
        ["lead_time_days", "cost_per_unit", "is_primary"],
    )
    rel(
        "consumes",
        t.get("consumes"),
        "CONSUMES",
        ("hospital_id", "Hospital"),
        ("item_sku", "Item"),
        ["monthly_demand", "revenue_month"],
    )
    rel(
        "can_substitute",
        t.get("can_substitute"),
        "CAN_SUBSTITUTE",
        ("from_sku", "Item"),
        ("to_sku", "Item"),
        ["requalification_days"],
    )
    if "lots" in t and not t["lots"].empty:
        rel("of_item", t["lots"], "OF_ITEM", ("lot_id", "Lot"), ("item_sku", "Item"), [])
        rel(
            "derived_from",
            t.get("derived_from"),
            "DERIVED_FROM",
            ("child_lot_id", "Lot"),
            ("parent_lot_id", "Lot"),
            ["qty_used"],
        )
        rel(
            "delivered_to",
            t.get("delivered_to"),
            "DELIVERED_TO",
            ("lot_id", "Lot"),
            ("hospital_id", "Hospital"),
            ["date", "qty"],
        )
    return out, args


def bulk_import(profile: str, runtime: Path, docker: bool = False) -> float:
    """Returns the seconds spent by neo4j-admin import itself (also prints end-to-end time)."""
    from supplygraph.db import driver_ctx, run_file, wait_until_ready
    from supplygraph.portable import admin_import, start, stop

    files_dir, args = build_import_files(profile)
    base = [
        "neo4j",
        "--overwrite-destination=true",
        "--multiline-fields=true",
        "--skip-duplicate-nodes=false",
    ]
    t_all = time.perf_counter()
    if docker:
        # inside the container data/generated is mounted at /import/generated
        cargs = [a.replace(str(GENERATED_DIR), "/import/generated").replace("\\", "/") for a in args]
        subprocess.run(["docker", "compose", "stop", "neo4j"], check=True)
        t0 = time.perf_counter()
        subprocess.run(
            [
                "docker",
                "compose",
                "run",
                "--rm",
                "neo4j",
                "neo4j-admin",
                "database",
                "import",
                "full",
                *base,
                *cargs,
            ],
            check=True,
        )
        secs = time.perf_counter() - t0
        subprocess.run(["docker", "compose", "start", "neo4j"], check=True)
    else:
        stop(runtime)
        t0 = time.perf_counter()
        res = admin_import(runtime, base + args)
        secs = time.perf_counter() - t0
        if res.returncode != 0:
            print(res.stdout[-3000:], res.stderr[-3000:])
            start(runtime)
            raise RuntimeError("neo4j-admin import failed")
        start(runtime)
    if not wait_until_ready(180):
        raise RuntimeError("Neo4j did not come back after import")
    with driver_ctx() as d:
        t1 = time.perf_counter()
        run_file(d, "00_schema.cypher")
        run_file(d, "01_enrich.cypher")
        schema_s = time.perf_counter() - t1
    total = time.perf_counter() - t_all
    print(
        f"neo4j-admin import: {secs:.1f}s | schema+enrich: {schema_s:.1f}s | end-to-end incl. restart: {total:.1f}s"
    )
    (files_dir / "timing.txt").write_text(
        f"import_s={secs:.2f}\nschema_s={schema_s:.2f}\ntotal_s={total:.2f}\n"
    )
    return secs
