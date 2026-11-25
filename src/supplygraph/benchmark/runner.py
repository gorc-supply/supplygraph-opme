"""Graph (Neo4j / Cypher) vs relational (DuckDB / recursive CTE) on the same three questions.

For every network profile (BOM depth 3/5/7 x size S/L): generate -> load into Neo4j ->
run each question `repeat` times after warm-up (median) in both engines, check that both
return the same answer (checksum), count lines of code, plot and write docs/benchmarks.md.
"""

from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path

import duckdb
import pandas as pd
from rich.console import Console

from supplygraph.analytics import plots
from supplygraph.config import CYPHER_DIR, DOCS_DIR, REPORTS_DIR, load_network_config
from supplygraph.db import driver_ctx, run
from supplygraph.generate.network import generate
from supplygraph.generate.writer import graph_stats, profile_dir, read_tables, write_tables
from supplygraph.load.loader import load_tables, reset

console = Console()
SQL_DIR = Path(__file__).parent / "sql"
QUESTIONS = {
    "q1_bom_explosion": "Q1 BOM explosion (all implants)",
    "q2_false_dual_source": "Q2 false dual-source (strict)",
    "q3_blast_radius": "Q3 blast radius, TTR 60 d",
}
TTR = 60


def loc(text: str, comment: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.strip() and not ln.strip().startswith(comment))


def _median_ms(fn, repeat: int, warmup: int = 2) -> tuple[float, object]:
    res = None
    for _ in range(warmup):
        res = fn()
    ts = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        res = fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts), res


def _duck(profile: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    d = profile_dir(profile)
    for t in ("items", "bom", "supplies", "buys_from", "stocks"):
        con.execute(
            f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{(d / f'{t}.csv').as_posix()}', header=true)"
        )
    return con


def run_benchmark(
    profiles: list[str], repeat: int = 10, restore_profile: str | None = "full"
) -> pd.DataFrame:
    rows = []
    for prof in profiles:
        cfg = load_network_config(prof)
        tables = generate(cfg)
        write_tables(tables, cfg)
        stats = graph_stats(tables)
        target = tables["buys_from"].groupby("seller_id").size().idxmax()  # most depended-upon supplier
        params = {"supplier_id": target, "ttr": float(TTR)}
        con = _duck(prof)
        with driver_ctx() as d:
            reset(d)
            t0 = time.perf_counter()
            load_tables(d, tables)
            load_s = time.perf_counter() - t0
            for q, label in QUESTIONS.items():
                cy = (CYPHER_DIR / "benchmark" / f"{q}.cypher").read_text(encoding="utf-8")
                sql = (SQL_DIR / f"{q}.sql").read_text(encoding="utf-8")
                cy_ms, cy_res = _median_ms(lambda cy=cy, p=params: run(d, cy, p, timeout=600), repeat)
                du_ms, du_res = _median_ms(
                    lambda sql=sql, c=con, p=params: c.execute(sql, p if "$" in sql else None).fetchall(),
                    repeat,
                )
                cy_pairs, cy_chk = cy_res[0]["pairs"], cy_res[0]["checksum"]
                du_pairs, du_chk = du_res[0]
                same = int(cy_pairs) == int(du_pairs) and abs(float(cy_chk or 0) - float(du_chk or 0)) <= max(
                    1.0, 1e-6 * abs(float(du_chk or 0))
                )
                rows.append(
                    {
                        "profile": prof,
                        "bom_depth": cfg.profile.bom_depth,
                        "size": "L" if "_l_" in prof else "S",
                        "nodes": stats["total_nodes"],
                        "relationships": stats["total_relationships"],
                        "question": label,
                        "cypher_ms": round(cy_ms, 1),
                        "duckdb_ms": round(du_ms, 1),
                        "speedup_graph": round(du_ms / cy_ms, 2) if cy_ms else None,
                        "answer_rows": int(cy_pairs),
                        "same_answer": same,
                        "cypher_loc": loc(cy, "//"),
                        "sql_loc": loc(sql, "--"),
                        "sql_ctes": len(re.findall(r"\bAS \(", sql)),
                        "sql_joins": len(re.findall(r"\bJOIN\b", sql)),
                        "load_s": round(load_s, 1),
                    }
                )
                console.print(
                    f"{prof:<11} {label:<34} cypher {cy_ms:8.1f} ms | duckdb {du_ms:8.1f} ms | "
                    f"rows {cy_pairs} | same={same}"
                )
        con.close()
    df = pd.DataFrame(rows)
    out = REPORTS_DIR / "benchmark"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "results.csv", index=False)
    _charts(df)
    (out / "results.json").write_text(json.dumps(df.to_dict("records"), indent=2), encoding="utf-8")
    if restore_profile:
        console.print(f"restoring profile '{restore_profile}' in Neo4j ...")
        cfg = load_network_config(restore_profile)
        if not profile_dir(restore_profile).exists():
            write_tables(generate(cfg), cfg)
        with driver_ctx() as d:
            reset(d)
            load_tables(d, read_tables(restore_profile))
    return df


def _charts(df: pd.DataFrame) -> None:
    img = DOCS_DIR / "img"
    img.mkdir(parents=True, exist_ok=True)
    for q, label in QUESTIONS.items():
        sub = df[df.question == label].copy()
        sub["scenario"] = sub["size"] + " / depth " + sub["bom_depth"].astype(str)
        sub = sub.rename(columns={"cypher_ms": "Neo4j (Cypher)", "duckdb_ms": "DuckDB (recursive CTE)"})
        plots.bar_ms(
            sub,
            "scenario",
            ["Neo4j (Cypher)", "DuckDB (recursive CTE)"],
            img / f"benchmark_{q}.png",
            label,
            "Median of 10 runs after warm-up, log scale. Lower is better.",
            "milliseconds",
            log=True,
        )
