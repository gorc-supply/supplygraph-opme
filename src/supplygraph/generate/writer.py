"""Write generated tables as deterministic CSVs + manifest, and compute graph size stats."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from supplygraph.config import GENERATED_DIR, NetworkConfig

NODE_TABLES = {
    "countries": "Country",
    "ports": "Port",
    "suppliers": "Supplier",
    "items": "Item",
    "plants": "Plant",
    "dcs": "DC",
    "hospitals": "Hospital",
    "lots": "Lot",
}
REL_TABLES = {
    "supplies": "SUPPLIES",
    "buys_from": "BUYS_FROM",
    "bom": "COMPONENT_OF",
    "manufactures": "MANUFACTURES",
    "ships_to": "SHIPS_TO",
    "stocks": "STOCKS",
    "serves": "SERVES",
    "consumes": "CONSUMES",
    "can_substitute": "CAN_SUBSTITUTE",
    "derived_from": "DERIVED_FROM",
    "delivered_to": "DELIVERED_TO",
}
AUX_TABLES = {"planted_false_dual_source"}


def profile_dir(profile: str) -> Path:
    return GENERATED_DIR / profile / "tables"


def write_tables(tables: dict[str, pd.DataFrame], cfg: NetworkConfig) -> Path:
    out = profile_dir(cfg.profile_name)
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, df in sorted(tables.items()):
        path = out / f"{name}.csv"
        df.to_csv(path, index=False, float_format="%.4f", lineterminator="\n", encoding="utf-8")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    stats = graph_stats(tables)
    manifest = {
        "profile": cfg.profile_name,
        "seed": cfg.seed,
        "as_of": cfg.as_of,
        "config": cfg.profile.model_dump(),
        "stats": stats,
        "sha256": hashes,
    }
    (out.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


def read_tables(profile: str) -> dict[str, pd.DataFrame]:
    d = profile_dir(profile)
    if not d.exists():
        raise FileNotFoundError(
            f"No generated data for profile '{profile}'. Run: sgraph generate --profile {profile}"
        )
    return {p.stem: pd.read_csv(p, keep_default_na=True) for p in sorted(d.glob("*.csv"))}


def graph_stats(tables: dict[str, pd.DataFrame]) -> dict:
    nodes = {label: len(tables[t]) for t, label in NODE_TABLES.items() if t in tables}
    rels = {rtype: len(tables[t]) for t, rtype in REL_TABLES.items() if t in tables}
    # derived relationships created by the loader from FK columns
    located = sum(len(tables[t]) for t in ("suppliers", "plants", "ports") if t in tables)
    rels["LOCATED_IN"] = located
    rels["OF_ITEM"] = len(tables.get("lots", []))
    return {
        "nodes": nodes,
        "relationships": rels,
        "total_nodes": int(sum(nodes.values())),
        "total_relationships": int(sum(rels.values())),
    }
