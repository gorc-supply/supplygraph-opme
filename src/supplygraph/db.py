"""Thin helpers around the official neo4j driver.

* Every query is sent as Cypher 25 (prefix added if missing).
* Parameters are always passed as parameters - never string-concatenated.
* `run_file` executes a .cypher file statement by statement (split on ';' at line end).
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from neo4j import Driver, GraphDatabase, Query, RoutingControl

from supplygraph.config import CYPHER_DIR, Neo4jSettings, neo4j_settings

_PREFIX = re.compile(r"^\s*CYPHER\s+(5|25)\b", re.IGNORECASE)


def cypher25(q: str) -> str:
    body = strip_comments(q).strip()
    return body if _PREFIX.match(body) else f"CYPHER 25\n{body}"


def strip_comments(q: str) -> str:
    out = []
    for line in q.splitlines():
        s = line.strip()
        if s.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


def get_driver(settings: Neo4jSettings | None = None, target: str = "local") -> Driver:
    s = settings or neo4j_settings(target)
    return GraphDatabase.driver(
        s.uri, auth=(s.user, s.password), connection_timeout=15, max_connection_lifetime=600
    )


@contextmanager
def driver_ctx(target: str = "local"):
    d = get_driver(target=target)
    try:
        yield d
    finally:
        d.close()


def read_cypher(relpath: str) -> str:
    return (CYPHER_DIR / relpath).read_text(encoding="utf-8")


def split_statements(text: str) -> list[str]:
    text = strip_comments(text)
    parts = re.split(r";\s*(?:\n|$)", text)
    return [p.strip() for p in parts if p.strip()]


def run(
    driver: Driver,
    query: str,
    params: dict | None = None,
    database: str | None = None,
    write: bool = False,
    timeout: float | None = None,
) -> list[dict]:
    db = database or neo4j_settings().database
    q = Query(cypher25(query), timeout=timeout) if timeout else cypher25(query)
    records, _, _ = driver.execute_query(
        q,
        parameters_=params or {},
        database_=db,
        routing_=RoutingControl.WRITE if write else RoutingControl.READ,
    )
    return [r.data() for r in records]


def run_df(
    driver: Driver, query: str, params: dict | None = None, timeout: float | None = 60, **kw
) -> pd.DataFrame:
    return pd.DataFrame(run(driver, query, params, timeout=timeout, **kw))


def run_file(driver: Driver, relpath: str | Path, params: dict | None = None, write: bool = True) -> int:
    text = (
        Path(relpath).read_text(encoding="utf-8")
        if Path(relpath).is_absolute()
        else read_cypher(str(relpath))
    )
    n = 0
    for stmt in split_statements(text):
        run(driver, stmt, params, write=write)
        n += 1
    return n


def timed(
    driver: Driver, query: str, params: dict | None = None, repeat: int = 10, warmup: int = 2
) -> tuple[float, int]:
    """Median wall time (ms) of `repeat` executions after `warmup` runs; returns (ms, rows)."""
    for _ in range(warmup):
        rows = run(driver, query, params)
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        rows = run(driver, query, params)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return times[len(times) // 2], len(rows)


def batched(rows: list[dict], size: int) -> Iterable[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def wait_until_ready(timeout_s: int = 120, target: str = "local") -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with driver_ctx(target) as d:
                d.verify_connectivity()
                return True
        except Exception:  # noqa: BLE001 - connection not ready yet
            time.sleep(2)
    return False


def params_of(_: Any) -> None:  # pragma: no cover - placeholder for typing tools
    return None
