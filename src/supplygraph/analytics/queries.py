"""Business analytics (section 9 A-G). Every function runs a parameterised .cypher file from
cypher/analytics and returns a pandas DataFrame (or a small dict of DataFrames + numbers).
The same functions back the Streamlit app, the CLI `sgraph analyze` and the tests."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from neo4j import Driver

from supplygraph.db import read_cypher, run, run_df

Q = {
    name: f"analytics/{name}.cypher"
    for name in [
        "A1_bom_explosion",
        "A2_where_used",
        "B1_hidden_convergence",
        "B2_single_source",
        "C1_geo_exposure",
        "C2_geo_hard_dependency",
        "D1_seeds_supplier",
        "D1_seeds_country",
        "D1_seeds_port",
        "D2_impact",
        "E1_recall_forward",
        "E2_recall_backward",
        "F1_routes",
        "G1_substitutes",
    ]
}


def _q(name: str) -> str:
    return read_cypher(Q[name])


# ------------------------------------------------------------------------------------ A
def bom_explosion(d: Driver, sku: str) -> pd.DataFrame:
    return run_df(d, _q("A1_bom_explosion"), {"sku": sku})


def where_used(d: Driver, sku: str) -> pd.DataFrame:
    return run_df(d, _q("A2_where_used"), {"sku": sku})


# ------------------------------------------------------------------------------------ B
def hidden_convergence(d: Driver, strict: bool = True) -> pd.DataFrame:
    return run_df(d, _q("B1_hidden_convergence"), {"strict": strict}, timeout=300)


def single_source(d: Driver) -> pd.DataFrame:
    return run_df(d, _q("B2_single_source"), timeout=300)


def multi_sourced_l1_count(d: Driver) -> int:
    q = """MATCH (i:Item {type:'COMPONENT', level: 1})
           WHERE COUNT { (:Supplier)-[:SUPPLIES]->(i) } >= 2 RETURN count(i) AS n"""
    return run(d, q)[0]["n"]


def total_revenue(d: Driver) -> float:
    return run(d, "MATCH (f:Item {type:'FINISHED'}) RETURN sum(f.revenue_month) AS r")[0]["r"] or 0.0


def revenue_of_items_containing(d: Driver, skus: list[str]) -> float:
    """Distinct revenue of finished items whose BOM contains any of `skus` (no double counting)."""
    q = """UNWIND $skus AS s MATCH (:Item {sku: s})-[:COMPONENT_OF]->{1,12}(f:Item {type:'FINISHED'})
           WITH DISTINCT f RETURN sum(f.revenue_month) AS r"""
    return run(d, q, {"skus": skus})[0]["r"] or 0.0


# ------------------------------------------------------------------------------------ C
def geo_exposure(d: Driver) -> pd.DataFrame:
    return run_df(d, _q("C1_geo_exposure"), timeout=300)


def geo_hard_dependency(d: Driver) -> pd.DataFrame:
    return run_df(d, _q("C2_geo_hard_dependency"), timeout=300)


# ------------------------------------------------------------------------------------ D
@dataclass
class DisruptionResult:
    kind: str
    key: str
    ttr: int
    seeds: pd.DataFrame
    impact: pd.DataFrame  # one row per (finished item, DC)
    timeline: pd.DataFrame  # cumulative revenue lost per day
    summary: dict


def disruption_seeds(d: Driver, kind: str, key: str) -> pd.DataFrame:
    if kind == "supplier":
        df = run_df(d, _q("D1_seeds_supplier"), {"supplier_id": key})
    elif kind == "country":
        df = run_df(d, _q("D1_seeds_country"), {"iso2": key})
    elif kind == "port":
        df = run_df(d, _q("D1_seeds_port"), {"port": key}, timeout=300)
    else:
        raise ValueError("kind must be supplier | country | port")
    if df.empty:
        return pd.DataFrame(columns=["sku", "loss", "pipe0", "dc"])
    if "dc" not in df:
        df["dc"] = None
    # several seed rows can hit the same item: keep the worst loss and the shortest pipeline
    return df.groupby(["sku", "dc"], dropna=False, as_index=False).agg(
        loss=("loss", "max"), pipe0=("pipe0", "min")
    )


def disruption(d: Driver, kind: str, key: str, ttr: int) -> DisruptionResult:
    seeds = disruption_seeds(d, kind, key)
    recs = (
        [
            {
                "sku": r.sku,
                "loss": float(r.loss),
                "pipe0": float(r.pipe0),
                "dc": None if pd.isna(r.dc) else r.dc,
            }
            for r in seeds.itertuples()
        ]
        if not seeds.empty
        else []
    )
    impact = (
        run_df(d, _q("D2_impact"), {"seeds": recs, "ttr": float(ttr)}, timeout=300)
        if recs
        else pd.DataFrame()
    )
    if impact.empty:
        impact = pd.DataFrame(
            columns=[
                "sku",
                "name",
                "category",
                "dc",
                "uf",
                "loss_frac",
                "cover_days",
                "in_transit_days",
                "tts_days",
                "stockout_days",
                "daily_demand",
                "units_short",
                "revenue_at_risk",
                "hospitals",
            ]
        )
    short = impact[impact["revenue_at_risk"] > 0] if not impact.empty else impact
    hospitals = sorted({h for hs in short["hospitals"] for h in hs}) if not short.empty else []
    # timeline: revenue lost accumulates from day TTS until day TTR on each (item, DC)
    days = np.arange(0, ttr + 1)
    cum = np.zeros_like(days, dtype=float)
    if not short.empty:
        prices = (short["revenue_at_risk"] / short["units_short"].replace(0, np.nan)).fillna(0).to_numpy()
        rate = short["daily_demand"].to_numpy() * short["loss_frac"].to_numpy() * prices
        start = short["tts_days"].to_numpy()
        for i, t in enumerate(days):
            cum[i] = float(np.sum(rate * np.clip(t - start, 0, None)))
    timeline = pd.DataFrame({"day": days, "cumulative_revenue_lost": cum})
    summary = {
        "kind": kind,
        "key": key,
        "ttr_days": ttr,
        "items_hit": int(len(seeds)),
        "finished_skus_exposed": int(impact["sku"].nunique()) if not impact.empty else 0,
        "sku_dc_stockouts": int(len(short)),
        "finished_skus_stockout": int(short["sku"].nunique()) if not short.empty else 0,
        "units_short": float(short["units_short"].sum()) if not short.empty else 0.0,
        "revenue_at_risk": float(short["revenue_at_risk"].sum()) if not short.empty else 0.0,
        "hospitals_affected": len(hospitals),
        "first_stockout_day": float(short["tts_days"].min()) if not short.empty else None,
    }
    return DisruptionResult(kind, key, ttr, seeds, impact, timeline, summary)


def supplier_risk_ranking(
    d: Driver, ttr: int, keep_impact_rows: bool = True, ttr_by_tier: dict[int, int] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the supplier scenario for every supplier. Returns (ranking, supplier x finished heatmap rows)."""
    sups = run_df(
        d,
        "MATCH (s:Supplier) RETURN s.id AS id, s.name AS name, s.tier AS tier, "
        "s.country_iso2 AS country ORDER BY id",
    )
    rows, heat = [], []
    for s in sups.itertuples():
        s_ttr = int((ttr_by_tier or {}).get(int(s.tier), ttr))
        res = disruption(d, "supplier", s.id, s_ttr)
        rows.append(
            {
                "ttr_days": s_ttr,
                "supplier_id": s.id,
                "name": s.name,
                "tier": s.tier,
                "country": s.country,
                **{
                    k: res.summary[k]
                    for k in (
                        "finished_skus_exposed",
                        "finished_skus_stockout",
                        "revenue_at_risk",
                        "hospitals_affected",
                        "first_stockout_day",
                    )
                },
            }
        )
        if keep_impact_rows and not res.impact.empty:
            g = res.impact.groupby("sku", as_index=False)["revenue_at_risk"].sum()
            g = g[g.revenue_at_risk > 0]
            g.insert(0, "supplier_id", s.id)
            heat.append(g)
    ranking = pd.DataFrame(rows).sort_values("revenue_at_risk", ascending=False).reset_index(drop=True)
    heat_df = (
        pd.concat(heat, ignore_index=True)
        if heat
        else pd.DataFrame(columns=["supplier_id", "sku", "revenue_at_risk"])
    )
    return ranking, heat_df


def write_revenue_at_risk(d: Driver, ranking: pd.DataFrame, ttr: int) -> None:
    cols = ["supplier_id", "revenue_at_risk", "hospitals_affected", "finished_skus_stockout", "ttr_days"]
    rows = ranking[cols].to_dict("records")
    run(
        d,
        """UNWIND $rows AS r MATCH (s:Supplier {id: r.supplier_id})
           SET s.revenue_at_risk = r.revenue_at_risk, s.hospitals_at_risk = r.hospitals_affected,
               s.skus_stockout = r.finished_skus_stockout, s.risk_ttr_days = r.ttr_days""",
        {"rows": rows},
        write=True,
    )


# ------------------------------------------------------------------------------------ E
def recall_forward(d: Driver, lot_id: str) -> pd.DataFrame:
    return run_df(d, _q("E1_recall_forward"), {"lot_id": lot_id})


def recall_backward(d: Driver, lot_id: str) -> pd.DataFrame:
    return run_df(d, _q("E2_recall_backward"), {"lot_id": lot_id})


def recall_summary(fwd: pd.DataFrame) -> dict:
    fin = fwd[fwd["type"] == "FINISHED"] if not fwd.empty else fwd
    hosp = {x["hospital_id"] for ds in fin["deliveries"] for x in ds} if not fin.empty else set()
    ufs = {x["uf"] for ds in fin["deliveries"] for x in ds} if not fin.empty else set()
    return {
        "derived_lots": int(len(fwd)),
        "finished_lots": int(len(fin)),
        "units_implanted_or_delivered": int(fin["delivered"].sum()) if not fin.empty else 0,
        "units_in_stock_to_quarantine": int(fin["in_stock"].clip(lower=0).sum()) if not fin.empty else 0,
        "hospitals": len(hosp),
        "ufs": len(ufs),
    }


def timed_recall(d: Driver, lot_id: str, repeat: int = 10) -> dict:
    out = {}
    for name, fn in (("forward_ms", recall_forward), ("backward_ms", recall_backward)):
        fn(d, lot_id)  # warm-up
        times = []
        for _ in range(repeat):
            t0 = time.perf_counter()
            fn(d, lot_id)
            times.append((time.perf_counter() - t0) * 1000)
        out[name] = float(np.median(times))
    return out


def pick_recall_lot(d: Driver, material: str = "RM-TI64") -> str | None:
    """A raw-material lot of `material` with a large but not extreme forward footprint (demo default)."""
    q = """MATCH (src:Lot)-[:OF_ITEM]->(:Item {sku: $sku})
           WITH src, COUNT { (l:Lot)-[:DERIVED_FROM]->{1,12}(src) } AS n
           WHERE n > 0 RETURN src.lot_id AS lot_id, n ORDER BY n DESC, lot_id"""
    rows = run(d, q, {"sku": material}, timeout=120)
    return rows[len(rows) // 4]["lot_id"] if rows else None


# ------------------------------------------------------------------------------------ F
def routes(
    d: Driver, plant: str, hospital: str, avoid_port: str | None = None, k: int = 5, order_by: str = "lead"
) -> pd.DataFrame:
    return run_df(
        d,
        _q("F1_routes"),
        {"plant": plant, "hospital": hospital, "avoid_port": avoid_port, "k": k, "order_by": order_by},
        timeout=120,
    )


def pareto(df: pd.DataFrame) -> pd.DataFrame:
    """Routes not dominated on (lead time, cost)."""
    if df.empty:
        return df
    s = df.sort_values(["lead_time_days", "cost_per_unit"]).reset_index(drop=True)
    keep, best_cost = [], float("inf")
    for r in s.itertuples():
        if r.cost_per_unit < best_cost:
            keep.append(r.Index)
            best_cost = r.cost_per_unit
    return s.loc[keep].reset_index(drop=True)


# ------------------------------------------------------------------------------------ G
def substitution(d: Driver, res: DisruptionResult) -> pd.DataFrame:
    short = res.impact[res.impact["revenue_at_risk"] > 0]
    if short.empty:
        return pd.DataFrame()
    affected = sorted(res.impact["sku"].unique().tolist())
    sh = short[["sku", "dc"]].drop_duplicates().to_dict("records")
    cands = run_df(d, _q("G1_substitutes"), {"shortages": sh, "affected_skus": affected})
    best = (
        cands.sort_values(["sku", "dc", "requalification_days"])
        .groupby(["sku", "dc"], as_index=False)
        .first()
        if not cands.empty
        else pd.DataFrame(columns=["sku", "dc", "substitute", "requalification_days", "substitute_on_hand"])
    )
    m = short.merge(best, on=["sku", "dc"], how="left")
    ttr = res.ttr

    def classify(r) -> tuple[str, float]:
        if pd.isna(r.get("substitute")):
            return "no substitute", 0.0
        rq, tts = float(r["requalification_days"]), float(r["tts_days"])
        if rq <= tts:
            return "fully mitigable", float(r["revenue_at_risk"])
        if rq < ttr:
            return "partially mitigable", float(r["revenue_at_risk"]) * (ttr - rq) / max(ttr - tts, 1e-9)
        return "not in time", 0.0

    cls = m.apply(classify, axis=1, result_type="expand")
    m["mitigation"], m["revenue_mitigated"] = cls[0], cls[1].round(2)
    return m[
        [
            "sku",
            "name",
            "dc",
            "tts_days",
            "stockout_days",
            "revenue_at_risk",
            "substitute",
            "requalification_days",
            "substitute_on_hand",
            "mitigation",
            "revenue_mitigated",
        ]
    ]
