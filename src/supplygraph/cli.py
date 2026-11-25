"""`sgraph` - command line orchestration (Windows-friendly replacement for a Makefile)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from supplygraph.config import REPORTS_DIR, ROOT, load_network_config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

app = typer.Typer(
    add_completion=False, no_args_is_help=True, help="SupplyGraph OPME - graph digital twin CLI"
)
console = Console()
RUNTIME = ROOT / ".runtime"


# ------------------------------------------------------------------------------ runtime
def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@app.command()
def up(mode: str = typer.Option("auto", help="auto | docker | portable")) -> None:
    """Start Neo4j (Docker Compose if available, otherwise the portable install in .runtime/)."""
    from supplygraph.db import wait_until_ready

    use_docker = mode == "docker" or (mode == "auto" and _docker_available())
    if use_docker:
        subprocess.run(["docker", "compose", "up", "-d"], cwd=ROOT, check=True)
    else:
        home = RUNTIME / "neo4j"
        if not home.exists():
            console.print(
                "[red]Docker not found and no portable install.[/] Run [bold]sgraph setup-portable[/] first."
            )
            raise typer.Exit(1)
        from supplygraph.portable import start

        start(RUNTIME)
    console.print("waiting for bolt://localhost:7687 ...")
    if not wait_until_ready(180):
        console.print("[red]Neo4j did not become ready in time[/]")
        raise typer.Exit(1)
    from supplygraph.db import driver_ctx, run

    with driver_ctx() as d:
        v = run(d, "RETURN gds.version() AS gds, apoc.version() AS apoc")[0]
    console.print(f"[green]Neo4j is up[/] - GDS {v['gds']} - APOC {v['apoc']}")


@app.command()
def down(mode: str = typer.Option("auto", help="auto | docker | portable")) -> None:
    """Stop Neo4j."""
    if mode == "docker" or (mode == "auto" and _docker_available()):
        subprocess.run(["docker", "compose", "down"], cwd=ROOT, check=True)
    else:
        from supplygraph.portable import stop

        stop(RUNTIME)


@app.command("setup-portable")
def setup_portable() -> None:
    """Download a portable JDK 21 + Neo4j Community + APOC + GDS into .runtime/ (no Docker, no admin rights)."""
    from supplygraph.portable import install

    install(RUNTIME)


# -------------------------------------------------------------------------------- data
@app.command("fetch-anchors")
def fetch_anchors(year: int = 2024, municipalities: int = 1500) -> None:
    """Refresh real open-data anchors in data/reference (NCM, imports by origin, IBGE)."""
    from supplygraph.generate.anchors import fetch_all

    fetch_all(year, municipalities)
    console.print("[green]anchors refreshed[/] -> data/reference/sources.json")


@app.command()
def generate(profile: str = "full", seed: int | None = None) -> None:
    """Generate the synthetic network (graph tables + tabular CSVs for DuckDB)."""
    from supplygraph.generate.network import generate as gen
    from supplygraph.generate.writer import write_tables

    cfg = load_network_config(profile, seed)
    t0 = time.perf_counter()
    tables = gen(cfg)
    out = write_tables(tables, cfg)
    console.print(
        f"[green]generated[/] profile={profile} seed={cfg.seed} in {time.perf_counter() - t0:.1f}s -> {out}"
    )
    _print_stats(tables, cfg.aura_limits)


def _print_stats(tables, limits) -> None:
    from supplygraph.generate.writer import graph_stats

    s = graph_stats(tables)
    t = Table(title="Graph size vs AuraDB Free limits")
    t.add_column("metric")
    t.add_column("count", justify="right")
    t.add_column("limit", justify="right")
    t.add_column("% used", justify="right")
    t.add_row(
        "nodes",
        f"{s['total_nodes']:,}",
        f"{limits['nodes']:,}",
        f"{100 * s['total_nodes'] / limits['nodes']:.1f}%",
    )
    t.add_row(
        "relationships",
        f"{s['total_relationships']:,}",
        f"{limits['relationships']:,}",
        f"{100 * s['total_relationships'] / limits['relationships']:.1f}%",
    )
    console.print(t)
    console.print("nodes: " + ", ".join(f"{k}={v:,}" for k, v in s["nodes"].items()))
    console.print("rels:  " + ", ".join(f"{k}={v:,}" for k, v in s["relationships"].items()))


@app.command()
def stats(profile: str = "full", db: bool = typer.Option(True, help="also count the live database")) -> None:
    """Print node/relationship counts against the AuraDB Free limits."""
    from supplygraph.generate.writer import read_tables

    cfg = load_network_config(profile)
    _print_stats(read_tables(profile), cfg.aura_limits)
    if db:
        from supplygraph.db import driver_ctx
        from supplygraph.load.loader import count_graph

        try:
            with driver_ctx() as d:
                n, r = count_graph(d)
            console.print(
                f"live database: {n:,} nodes ({100 * n / cfg.aura_limits['nodes']:.1f}%), "
                f"{r:,} relationships ({100 * r / cfg.aura_limits['relationships']:.1f}%)"
            )
        except Exception as e:  # noqa: BLE001
            console.print(f"[yellow]database not reachable:[/] {e}")


@app.command()
def load(
    profile: str = "full", batch_size: int = 5000, reset_first: bool = typer.Option(False, "--reset")
) -> None:
    """Idempotent transactional load (UNWIND/MERGE in batches)."""
    from supplygraph.db import driver_ctx
    from supplygraph.generate.writer import read_tables
    from supplygraph.load.loader import count_graph, load_tables, reset

    tables = read_tables(profile)
    with driver_ctx() as d:
        if reset_first:
            reset(d)
        t0 = time.perf_counter()
        load_tables(d, tables, batch_size)
        n, r = count_graph(d)
    console.print(f"[green]loaded[/] {n:,} nodes / {r:,} relationships in {time.perf_counter() - t0:.1f}s")


@app.command("bulk-import")
def bulk_import(profile: str = "full") -> None:
    """Initial bulk load with `neo4j-admin database import full` (stops/starts the server)."""
    from supplygraph.load.admin_import import bulk_import as run_import

    secs = run_import(profile, RUNTIME, docker=_docker_available())
    console.print(f"[green]neo4j-admin import finished[/] in {secs:.1f}s (see docs/benchmarks.md)")


@app.command()
def reset() -> None:
    """Delete all nodes and relationships (schema is kept)."""
    from supplygraph.db import driver_ctx
    from supplygraph.load.loader import reset as do_reset

    with driver_ctx() as d:
        do_reset(d)
    console.print("[green]database emptied[/]")


@app.command()
def validate(profile: str = "full") -> None:
    """Run the Cypher data-quality checks; non-zero exit code if any fails."""
    from supplygraph.db import driver_ctx
    from supplygraph.load.loader import count_graph
    from supplygraph.validate.checks import run_all, write_report

    cfg = load_network_config(profile)
    with driver_ctx() as d:
        results = run_all(d, cfg.as_of)
        counts = count_graph(d)
    t = Table(title="Graph data quality")
    for col in ("check", "status", "violations", "ms"):
        t.add_column(col)
    for r in results:
        t.add_row(
            r.description,
            "[green]PASS[/]" if r.passed else "[red]FAIL[/]",
            str(len(r.violations)),
            f"{r.ms:.0f}",
        )
    console.print(t)
    write_report(results, profile, counts)
    console.print("report -> reports/data_quality.md")
    if not all(r.passed for r in results):
        raise typer.Exit(1)


# ---------------------------------------------------------------------------- analytics
@app.command()
def analyze(
    step: str = typer.Option("all", help="all | cypher | gds | criticality"),
    ttr: int = typer.Option(None, help="TTR days for the supplier ranking (default: scoring.yaml)"),
) -> None:
    """Run the business analyses (9A-9G), GDS algorithms and the criticality index."""
    REPORTS_DIR.mkdir(exist_ok=True)
    if step in ("all", "cypher"):
        from supplygraph.analytics.report import run_cypher_analyses

        run_cypher_analyses(ttr)
    if step in ("all", "gds"):
        from supplygraph.gds.algorithms import run_gds

        run_gds()
    if step in ("all", "criticality", "gds"):
        from supplygraph.gds.scoring import run_criticality

        run_criticality()
    console.print("[green]analysis finished[/] -> reports/")


@app.command()
def benchmark(
    repeat: int = 10,
    profiles: str = "bench_s_d3,bench_s_d5,bench_s_d7,bench_l_d3,bench_l_d5,bench_l_d7",
    restore: str = typer.Option("full", help="profile to reload at the end ('' to skip)"),
) -> None:
    """Graph (Cypher) vs relational (DuckDB recursive CTE) on the same 3 questions."""
    from supplygraph.benchmark.runner import run_benchmark

    run_benchmark([p for p in profiles.split(",") if p], repeat=repeat, restore_profile=restore or None)


@app.command("export-aura")
def export_aura(dry_run: bool = typer.Option(False, help="only check limits, do not write")) -> None:
    """Copy the GDS-enriched local graph to AuraDB Free (credentials from .env)."""
    from supplygraph.export.aura import export

    export(dry_run=dry_run)


@app.command("all")
def run_all_steps(profile: str = "full") -> None:
    """generate -> load -> validate -> analyze (end-to-end)."""
    generate(profile)
    load(profile, reset_first=True)
    validate(profile)
    analyze(step="all", ttr=None)


@app.command()
def version() -> None:
    """Show versions of the database, plugins and drivers."""
    import graphdatascience
    import neo4j

    from supplygraph.db import driver_ctx, run

    info = {"neo4j-python-driver": neo4j.__version__, "graphdatascience": graphdatascience.__version__}
    try:
        with driver_ctx() as d:
            r = run(
                d,
                "CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] AS v, edition",
            )
            info["server"] = {x["name"]: f"{x['v']} {x['edition']}" for x in r}
            info["gds"] = run(d, "RETURN gds.version() AS v")[0]["v"]
            info["apoc"] = run(d, "RETURN apoc.version() AS v")[0]["v"]
    except Exception as e:  # noqa: BLE001
        info["server"] = f"unreachable: {e}"
    console.print_json(json.dumps(info))


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
    _ = Path
