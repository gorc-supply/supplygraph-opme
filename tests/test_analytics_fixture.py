"""Analytics on a hand-built graph with known answers (tests/fixtures/fixture_network.py)."""

from __future__ import annotations

import pytest
from fixtures.fixture_network import fixture_tables

from supplygraph.analytics import queries as A
from supplygraph.load.loader import load_tables, reset

pytestmark = pytest.mark.neo4j


@pytest.fixture(scope="module")
def fx(driver):
    reset(driver)
    load_tables(driver, fixture_tables())
    yield driver
    reset(driver)


def test_bom_explosion_multiplies_quantities(fx):
    df = A.bom_explosion(fx, "FG-T-0001").set_index("sku")
    assert set(df.index) == {"CP-T1-A", "CP-T2-A", "RM-T-R1"}
    assert df.loc["CP-T2-A", "qty_per_implant"] == pytest.approx(2.0)
    assert df.loc["RM-T-R1", "qty_per_implant"] == pytest.approx(1.0)  # 2 blanks x 0.5 kg
    assert df.loc["RM-T-R1", "bom_level"] == 3


def test_where_used(fx):
    assert set(A.where_used(fx, "RM-T-R1").finished_sku) == {"FG-T-0001", "FG-T-0003", "FG-T-0004"}


def test_false_dual_source(fx):
    df = A.hidden_convergence(fx, strict=True)
    got = {(r.item_sku, r.hidden_supplier) for r in df.itertuples()}
    assert got == {("CP-T1-A", "S-T2-007"), ("CP-T1-A", "S-T3-001"), ("CP-T1-B", "S-T3-002")}


def test_supplier_disruption_hits_exactly_known_skus(fx):
    res = A.disruption(fx, "supplier", "S-T2-007", ttr=60)
    assert set(res.impact.sku) == {"FG-T-0001", "FG-T-0004"}
    short = res.impact[res.impact.revenue_at_risk > 0]
    assert list(short.sku) == ["FG-T-0001"]
    row = short.iloc[0]
    assert row.tts_days == pytest.approx(55.0)          # 30 cover + 20 pipeline + 5 transit
    assert row.revenue_at_risk == pytest.approx(5000.0)  # 5 days x 1/day x R$1,000
    assert res.summary["hospitals_affected"] == 1


def test_tier3_disruption_reaches_more_skus(fx):
    res = A.disruption(fx, "supplier", "S-T3-001", ttr=60)
    assert set(res.impact.sku) == {"FG-T-0001", "FG-T-0003", "FG-T-0004"}


def test_geo_hard_dependency_erp_vs_graph(fx):
    df = A.geo_hard_dependency(fx).set_index("iso2")
    assert df.loc["CN", "erp_pct"] == 0.0           # China is invisible to the buyer...
    assert df.loc["CN", "graph_pct"] == 75.0        # ...but 3 of 4 implants need Chinese titanium


def test_recall_forward_and_backward(fx):
    fwd = A.recall_forward(fx, "RM-T-R1-L0001")
    s = A.recall_summary(fwd)
    assert s["derived_lots"] == 5 and s["finished_lots"] == 2 and s["hospitals"] == 1
    assert s["units_in_stock_to_quarantine"] == 3   # 8 made, 5 delivered (FG-T-0001); FG-T-0003 fully delivered
    back = A.recall_backward(fx, "FG-T-0001-L0001")
    assert back.iloc[-1].lot_id == "RM-T-R1-L0001" and back.depth.max() == 3


def test_routes_and_port_avoidance(fx):
    best = A.routes(fx, "P-01", "H-0001", None, 5, "lead")
    assert best.iloc[0].route == ["P-01", "FRA", "GRU", "DC-SP1", "H-0001"]
    cheap = A.routes(fx, "P-01", "H-0001", None, 5, "cost")
    assert cheap.iloc[0].route[1] == "DEHAM"
    alt = A.routes(fx, "P-01", "H-0001", "GRU", 5, "lead")
    assert len(alt) == 1 and "GRU" not in alt.iloc[0].route


def test_port_with_alternative_causes_no_stockout(fx):
    res = A.disruption(fx, "port", "GRU", ttr=60)
    assert res.summary["revenue_at_risk"] == 0


def test_substitution_mitigates(fx):
    res = A.disruption(fx, "supplier", "S-T2-007", ttr=60)
    sub = A.substitution(fx, res)
    assert sub.iloc[0].substitute == "FG-T-0002"
    assert sub.iloc[0].mitigation == "fully mitigable"
