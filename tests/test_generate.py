"""Generator tests - no database needed."""

from __future__ import annotations

import hashlib
from collections import defaultdict

import pytest

from supplygraph.config import load_network_config
from supplygraph.generate.network import generate
from supplygraph.generate.writer import graph_stats


def _hashes(tables) -> dict[str, str]:
    return {
        k: hashlib.sha256(v.to_csv(index=False, float_format="%.4f", lineterminator="\n").encode()).hexdigest()
        for k, v in sorted(tables.items())
    }


@pytest.fixture(scope="module")
def ci_tables():
    return generate(load_network_config("ci"))


def test_same_seed_same_hash(ci_tables):
    again = generate(load_network_config("ci"))
    assert _hashes(ci_tables) == _hashes(again)


def test_different_seed_changes_data(ci_tables):
    other = generate(load_network_config("ci", seed=7))
    assert _hashes(ci_tables)["supplies"] != _hashes(other)["supplies"]


def test_shares_sum_to_100(ci_tables):
    s = ci_tables["supplies"].groupby("item_sku")["share_pct"].sum()
    assert ((s - 100).abs() <= 0.5).all()
    b = ci_tables["buys_from"].groupby(["buyer_id", "item_sku", "for_sku"])["share_pct"].sum()
    assert ((b - 100).abs() <= 0.5).all()


def test_bom_is_dag_and_reaches_raw(ci_tables):
    children = defaultdict(list)
    for r in ci_tables["bom"].itertuples():
        children[r.parent_sku].append(r.child_sku)
    types = dict(zip(ci_tables["items"].sku, ci_tables["items"].type, strict=True))
    state: dict[str, int] = {}

    def reaches_raw(n: str) -> bool:  # DFS with cycle detection
        if state.get(n) == 1:
            raise AssertionError(f"cycle at {n}")
        if types[n] == "RAW":
            return True
        state[n] = 1
        ok = any(reaches_raw(c) for c in children[n])
        state[n] = 2
        return ok

    for sku, t in types.items():
        if t == "FINISHED":
            assert reaches_raw(sku), sku


def test_planted_false_dual_source_exists(ci_tables):
    planted = ci_tables["planted_false_dual_source"]
    assert len(planted) > 0
    bf = ci_tables["buys_from"]
    for r in planted.itertuples():
        rows = bf[(bf.for_sku == r.item_sku) & (bf.item_sku == r.child_sku)]
        assert set(rows.seller_id) == {r.upstream_supplier_id}
        assert (rows.share_pct == 100).all()


def test_full_profile_fits_aura_free():
    cfg = load_network_config("full")
    s = graph_stats(generate(cfg))
    assert s["total_nodes"] < cfg.aura_limits["nodes"] * 0.6
    assert s["total_relationships"] < cfg.aura_limits["relationships"] * 0.6
