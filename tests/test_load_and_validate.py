"""Loader idempotency + data-quality checks on the generated `ci` network (needs Neo4j)."""

from __future__ import annotations

import pytest

from supplygraph.config import load_network_config
from supplygraph.db import run
from supplygraph.generate.network import generate
from supplygraph.generate.writer import graph_stats
from supplygraph.load.loader import count_graph, load_tables, reset
from supplygraph.validate.checks import CHECKS, run_check

pytestmark = pytest.mark.neo4j
CFG = load_network_config("ci")


@pytest.fixture(scope="module")
def loaded(driver):
    tables = generate(CFG)
    reset(driver)
    load_tables(driver, tables)
    return tables


def test_load_matches_generated_counts(driver, loaded):
    s = graph_stats(loaded)
    assert count_graph(driver) == (s["total_nodes"], s["total_relationships"])


def test_load_is_idempotent(driver, loaded):
    before = count_graph(driver)
    load_tables(driver, loaded)
    assert count_graph(driver) == before


@pytest.mark.parametrize("name", list(CHECKS))
def test_quality_check_passes(driver, loaded, name):
    res = run_check(driver, name, CFG.as_of)
    assert res.passed, f"{name}: {res.violations[:5]}"


def test_cycle_is_detected(driver, loaded):
    """Negative test: inject a BOM cycle, the DAG check must fail, then remove it."""
    pair = run(driver, """MATCH (c:Item)-[:COMPONENT_OF]->(p:Item {type: 'COMPONENT'})
                          RETURN c.sku AS c, p.sku AS p LIMIT 1""")[0]
    run(driver, "MATCH (c:Item {sku: $c}), (p:Item {sku: $p}) MERGE (p)-[:COMPONENT_OF {qty_per: 1.0, test: true}]->(c)",
        pair, write=True)
    try:
        assert not run_check(driver, "01_bom_is_dag", CFG.as_of).passed
    finally:
        run(driver, "MATCH ()-[r:COMPONENT_OF {test: true}]->() DELETE r", write=True)


def test_expired_released_is_detected(driver, loaded):
    lot = run(driver, "MATCH (l:Lot {status: 'expired'}) RETURN l.lot_id AS id LIMIT 1")
    if not lot:
        pytest.skip("no expired lot in this network")
    run(driver, "MATCH (l:Lot {lot_id: $id}) SET l.status = 'released'", {"id": lot[0]["id"]}, write=True)
    try:
        assert not run_check(driver, "07_no_expired_released", CFG.as_of).passed
    finally:
        run(driver, "MATCH (l:Lot {lot_id: $id}) SET l.status = 'expired'", {"id": lot[0]["id"]}, write=True)
