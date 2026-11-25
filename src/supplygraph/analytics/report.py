"""Run every business analysis (9A-9G) on the loaded graph and persist results:
reports/analytics/*.csv, reports/metrics.json and charts in docs/img/."""

from __future__ import annotations

import json
import time

import pandas as pd
from rich.console import Console

from supplygraph.analytics import plots
from supplygraph.analytics import queries as A
from supplygraph.config import DOCS_DIR, REPORTS_DIR, load_scoring_config
from supplygraph.db import driver_ctx, run

console = Console()
OUT = REPORTS_DIR / "analytics"
IMG = DOCS_DIR / "img"


def _save(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8")


def _metrics_path():
    return REPORTS_DIR / "metrics.json"


def load_metrics() -> dict:
    p = _metrics_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_metrics(update: dict) -> None:
    m = load_metrics()
    m.update(update)
    _metrics_path().write_text(json.dumps(m, indent=2, ensure_ascii=False, default=float), encoding="utf-8")


def run_cypher_analyses(ttr: int | None = None) -> dict:
    ttr = ttr or load_scoring_config().ttr_days
    IMG.mkdir(parents=True, exist_ok=True)
    m: dict = {}
    with driver_ctx() as d:
        total = A.total_revenue(d)
        m["total_revenue_month"] = total
        n_hosp = run(d, "MATCH (h:Hospital) RETURN count(h) AS n")[0]["n"]

        # --- A: BOM explosion of the top-revenue implant + where-used of medical titanium
        top = run(
            d,
            "MATCH (f:Item {type:'FINISHED'}) RETURN f.sku AS sku, f.name AS name ORDER BY f.revenue_month DESC LIMIT 1",
        )[0]
        bom = A.bom_explosion(d, top["sku"])
        _save(bom, "A1_bom_explosion_top_sku")
        wu = A.where_used(d, "RM-TI64")
        _save(wu, "A2_where_used_TI64")
        m["A"] = {
            "showcase_sku": top["sku"],
            "showcase_name": top["name"],
            "bom_lines": len(bom),
            "bom_levels": int(bom.bom_level.max()) if not bom.empty else 0,
            "raw_materials": int((bom.type == "RAW").sum()),
            "ti64_finished_skus": len(wu),
            "ti64_revenue_month": float(wu.revenue_month.sum()),
            "ti64_revenue_pct": round(100 * float(wu.revenue_month.sum()) / total, 1),
        }
        console.print(f"A  BOM {top['sku']}: {len(bom)} lines | Ti-6Al-4V used by {len(wu)} implants")

        # --- B: hidden convergence + single source
        strict = A.hidden_convergence(d, True)
        relaxed = A.hidden_convergence(d, False)
        single = A.single_source(d)
        _save(strict, "B1_false_dual_source_strict")
        _save(relaxed, "B1_shared_upstream_relaxed")
        _save(single, "B2_single_source")
        multi = A.multi_sourced_l1_count(d)
        items = strict.item_sku.unique().tolist()
        rev_conv = A.revenue_of_items_containing(d, items)
        top_hidden = (
            strict.groupby(["hidden_supplier", "hidden_tier", "hidden_country"], as_index=False)
            .agg(items=("item_sku", "nunique"))
            .sort_values("items", ascending=False)
        )
        best_hidden = top_hidden.iloc[0].to_dict() if not top_hidden.empty else {}
        if best_hidden:
            best_hidden["revenue_exposed"] = A.revenue_of_items_containing(
                d, strict[strict.hidden_supplier == best_hidden["hidden_supplier"]].item_sku.unique().tolist()
            )
        _save(top_hidden, "B1_hidden_suppliers_ranking")
        m["B"] = {
            "multi_sourced_l1_items": multi,
            "false_dual_items": len(items),
            "false_dual_pct": round(100 * len(items) / max(multi, 1), 1),
            "revenue_exposed": rev_conv,
            "revenue_exposed_pct": round(100 * rev_conv / total, 1),
            "relaxed_items": int(relaxed.item_sku.nunique()),
            "single_source_items": len(single),
            "top_hidden_supplier": best_hidden,
            "top_hidden_supplier_revenue_pct": round(100 * best_hidden.get("revenue_exposed", 0) / total, 1),
        }
        console.print(
            f"B  {len(items)}/{multi} multi-sourced items converge on one upstream supplier "
            f"({m['B']['revenue_exposed_pct']}% of revenue)"
        )

        # --- C: geography, ERP vs graph
        geo = A.geo_exposure(d)
        hard = A.geo_hard_dependency(d)
        _save(geo, "C1_geo_exposure")
        _save(hard, "C2_geo_hard_dependency")
        h2 = (
            hard[hard.iso2 != "BR"]
            .assign(gap=lambda x: x.graph_pct - x.erp_pct)
            .sort_values("gap", ascending=False)
        )
        m["C"] = {
            "largest_hidden_country": h2.iloc[0][["iso2", "country", "erp_pct", "graph_pct"]].to_dict(),
            "hard_dependency": hard.head(8).to_dict("records"),
            "weighted_exposure": geo.head(8).to_dict("records"),
        }
        plots.erp_vs_graph(
            hard,
            IMG / "geo_erp_vs_graph.png",
            "erp_pct",
            "graph_pct",
            "Revenue that depends 100% on one country",
            "ERP view (plant + tier-1) vs graph view (all tiers). Synthetic network.",
        )
        plots.erp_vs_graph(
            geo,
            IMG / "geo_weighted_exposure.png",
            "erp_pct",
            "graph_pct",
            "Revenue-weighted exposure by country",
            "Largest share of any single input sourced from the country. Synthetic network.",
        )
        console.print(
            f"C  {h2.iloc[0]['country']}: ERP {h2.iloc[0]['erp_pct']}% vs graph {h2.iloc[0]['graph_pct']}%"
        )

        # --- D: supplier ranking (TTS x TTR) + scenarios
        t0 = time.perf_counter()
        ranking, heat = A.supplier_risk_ranking(d, ttr)
        A.write_revenue_at_risk(d, ranking, ttr)
        _save(ranking, "D_supplier_risk_ranking")
        _save(heat, "D_heatmap_supplier_x_sku")
        top_s = ranking.head(20).supplier_id.tolist()
        hm = heat[heat.supplier_id.isin(top_s)]
        top_sku = hm.groupby("sku").revenue_at_risk.sum().nlargest(25).index
        pivot = (
            hm[hm.sku.isin(top_sku)]
            .pivot_table(
                index="supplier_id", columns="sku", values="revenue_at_risk", aggfunc="sum", fill_value=0
            )
            .reindex(top_s)
            .fillna(0)
        )
        plots.heatmap(
            pivot,
            IMG / "heatmap_supplier_x_sku.png",
            "Where each supplier's disruption hurts",
            f"Revenue at risk if the supplier stops for {ttr} days (top 20 suppliers x top 25 implants)",
        )
        worst = ranking.iloc[0].to_dict()
        res = A.disruption(d, "supplier", worst["supplier_id"], ttr)
        _save(res.impact.drop(columns=["hospitals"]), "D_worst_supplier_impact")
        plots.tts_ttr(
            res.impact,
            ttr,
            IMG / "tts_vs_ttr_worst_supplier.png",
            f"TTS x TTR - {worst['supplier_id']} stops for {ttr} days",
            "Each dot is one implant SKU at one DC. Left of the line = stock-out.",
        )
        plots.timeline(
            res.timeline,
            IMG / "timeline_worst_supplier.png",
            f"Revenue lost over time - {worst['supplier_id']} out for {ttr} days",
            "Losses start when the first DC runs out (TTS) and grow until recovery (TTR)",
        )
        scen = {}
        for kind, key in (
            ("country", "CN"),
            ("country", "DE"),
            ("country", "US"),
            ("port", "GRU"),
            ("port", "VCP"),
        ):
            r = A.disruption(d, kind, key, ttr)
            scen[f"{kind}:{key}"] = r.summary
        tier_counts = ranking.groupby("tier").revenue_at_risk.sum().to_dict()
        m["D"] = {
            "ttr_days": ttr,
            "runtime_s": round(time.perf_counter() - t0, 1),
            "worst_supplier": worst,
            "worst_supplier_summary": res.summary,
            "suppliers_with_stockout": int((ranking.revenue_at_risk > 0).sum()),
            "top10": ranking.head(10).to_dict("records"),
            "revenue_at_risk_by_tier": tier_counts,
            "tier23_in_top10": int((ranking.head(10).tier >= 2).sum()),
            "scenarios": scen,
            "hospitals_total": n_hosp,
        }
        console.print(
            f"D  worst supplier {worst['supplier_id']} (tier {worst['tier']}): "
            f"R$ {worst['revenue_at_risk'] / 1e6:.1f} M at risk, {worst['hospitals_affected']} hospitals"
        )

        # --- E: recall
        lot = A.pick_recall_lot(d, "RM-TI64")
        fwd = A.recall_forward(d, lot)
        summ = A.recall_summary(fwd)
        timing = A.timed_recall(d, lot)
        fwd_flat = fwd.drop(columns=["deliveries"])
        _save(fwd_flat, "E1_recall_forward")
        fl = fwd[fwd.type == "FINISHED"].lot_id.iloc[0] if (fwd.type == "FINISHED").any() else None
        if fl:
            _save(A.recall_backward(d, fl), "E2_recall_backward_example")
        m["E"] = {"lot_id": lot, **summ, **timing, "backward_example_lot": fl}
        console.print(
            f"E  recall {lot}: {summ['finished_lots']} implant lots, {summ['hospitals']} hospitals, "
            f"forward trace {timing['forward_ms']:.0f} ms"
        )

        # --- F: routes, worst-case port + alternatives
        pair = run(
            d,
            """MATCH (pl:Plant)-[:SHIPS_TO]->(:Port)-[:SHIPS_TO]->(:Port {code:'GRU'})
                         MATCH (h:Hospital {uf: 'BA'}) RETURN pl.id AS plant, h.id AS hospital
                         ORDER BY plant, hospital LIMIT 1""",
        )[0]
        base = A.routes(d, pair["plant"], pair["hospital"], None, 10, "lead")
        alt = A.routes(d, pair["plant"], pair["hospital"], "GRU", 10, "lead")
        cheap = A.routes(d, pair["plant"], pair["hospital"], None, 10, "cost")
        allr = pd.concat([base, cheap]).drop_duplicates(subset=["lead_time_days", "cost_per_unit"])
        par = A.pareto(allr)
        for nm, df in (("F_routes_base", base), ("F_routes_avoid_GRU", alt), ("F_routes_pareto", par)):
            _save(
                df.assign(route=df.route.map(" > ".join), modes=df.modes.map(",".join))
                if not df.empty
                else df,
                nm,
            )
        m["F"] = {
            **pair,
            "best_lead": float(base.lead_time_days.iloc[0]) if not base.empty else None,
            "best_cost": float(cheap.cost_per_unit.iloc[0]) if not cheap.empty else None,
            "best_lead_without_GRU": float(alt.lead_time_days.iloc[0]) if not alt.empty else None,
            "pareto_routes": len(par),
        }

        # --- G: substitution on the worst supplier scenario and on a country scenario
        g1 = A.substitution(d, res)
        rde = A.disruption(d, "country", "DE", ttr)
        g2 = A.substitution(d, rde)
        _save(g1, "G_substitution_worst_supplier")
        _save(g2, "G_substitution_country_DE")

        def gsum(g: pd.DataFrame, r) -> dict:
            if g.empty:
                return {"rows": 0}
            return {
                "rows": len(g),
                "by_mitigation": g.mitigation.value_counts().to_dict(),
                "revenue_at_risk": float(g.revenue_at_risk.sum()),
                "revenue_mitigated": float(g.revenue_mitigated.sum()),
                "mitigated_pct": round(
                    100 * float(g.revenue_mitigated.sum()) / max(float(g.revenue_at_risk.sum()), 1), 1
                ),
            }

        m["G"] = {"worst_supplier": gsum(g1, res), "country_DE": gsum(g2, rde)}
    save_metrics(m)
    return m
