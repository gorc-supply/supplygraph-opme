"""Supplier Criticality Index (0-100) and its sensitivity to the weights (config/scoring.yaml).

index = 100 * sum_k w_k * minmax(component_k)
components: revenue_at_risk (9D, TTS x TTR), betweenness, pagerank (GDS), geo_risk (country),
financial_risk (supplier), single_source (1 if sole source of at least one item).
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console

from supplygraph.analytics.report import _save, save_metrics
from supplygraph.config import load_scoring_config
from supplygraph.db import driver_ctx, run, run_df

console = Console()
COMPONENTS = ["revenue_at_risk", "betweenness", "pagerank", "geo_risk", "financial_risk", "single_source"]


def supplier_features(d) -> pd.DataFrame:
    return run_df(
        d,
        """
        MATCH (s:Supplier)-[:LOCATED_IN]->(c:Country)
        RETURN s.id AS supplier_id, s.name AS name, s.tier AS tier, s.country_iso2 AS country,
               coalesce(s.revenue_at_risk, 0.0) AS revenue_at_risk,
               coalesce(s.betweenness, 0.0) AS betweenness, coalesce(s.pagerank, 0.0) AS pagerank,
               c.geo_risk_score AS geo_risk, s.financial_risk AS financial_risk,
               CASE WHEN EXISTS { (s)-[:SUPPLIES]->(i:Item) WHERE COUNT { (:Supplier)-[:SUPPLIES]->(i) } = 1 }
                    THEN 1.0 ELSE 0.0 END AS single_source
        ORDER BY supplier_id""",
    )


def score(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    total = pd.Series(0.0, index=df.index)
    for k in COMPONENTS:
        col = df[k].astype(float)
        rng = col.max() - col.min()
        norm = (col - col.min()) / rng if rng > 0 else col * 0
        total += weights.get(k, 0.0) * norm
    return (100 * total).round(1)


def run_criticality() -> pd.DataFrame:
    cfg = load_scoring_config()
    with driver_ctx() as d:
        df = supplier_features(d)
        df["criticality_index"] = score(df, cfg.weights)
        df["rank"] = df["criticality_index"].rank(ascending=False, method="min").astype(int)
        run(
            d,
            """UNWIND $rows AS r MATCH (s:Supplier {id: r.supplier_id})
                  SET s.criticality_index = r.criticality_index, s.criticality_rank = r.rank,
                      s.is_single_source = r.single_source = 1.0""",
            {"rows": df[["supplier_id", "criticality_index", "rank", "single_source"]].to_dict("records")},
            write=True,
        )
    df = df.sort_values("criticality_index", ascending=False).reset_index(drop=True)
    _save(df, "criticality_index")
    # sensitivity: how stable is the ranking when the weights change?
    base_rank = df.set_index("supplier_id")["criticality_index"].rank(ascending=False)
    base_top10 = set(df.head(10).supplier_id)
    rows = []
    for name, w in cfg.sensitivity_scenarios.items():
        s = score(df, w)
        r = pd.Series(s.values, index=df.supplier_id).rank(ascending=False)
        top10 = set(pd.Series(s.values, index=df.supplier_id).nlargest(10).index)
        # Pearson correlation of two rank vectors = Spearman rank correlation (no scipy needed)
        rows.append(
            {
                "scenario": name,
                "spearman_vs_base": round(float(base_rank.corr(r)), 3),
                "top10_overlap": len(base_top10 & top10),
                "top1": pd.Series(s.values, index=df.supplier_id).idxmax(),
            }
        )
    sens = pd.DataFrame(rows)
    _save(sens, "criticality_sensitivity")
    tier_top10 = df.head(10).tier.value_counts().to_dict()
    save_metrics(
        {
            "criticality": {
                "weights": cfg.weights,
                "top10": df.head(10)[["supplier_id", "tier", "country", "criticality_index"]].to_dict(
                    "records"
                ),
                "top10_by_tier": {int(k): int(v) for k, v in tier_top10.items()},
                "sensitivity": rows,
            }
        }
    )
    console.print(
        f"criticality index written for {len(df)} suppliers | top: {df.iloc[0].supplier_id} "
        f"({df.iloc[0].criticality_index}) | sensitivity spearman "
        + ", ".join(f"{r['scenario']}={r['spearman_vs_base']}" for r in rows)
    )
    return df
