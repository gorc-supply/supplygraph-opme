"""Build notebooks/01_supplygraph_story.ipynb (narrative EDA). Execute with:
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/01_supplygraph_story.ipynb"""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("""# SupplyGraph OPME - the story in one notebook

Exploratory walk-through of the synthetic network and of the main results. It reads the generated tables
(`data/generated/full/tables`) and the analysis outputs (`reports/`), so it runs without a database.
Regenerate everything with `uv run sgraph all`.

> All business numbers are **synthetic** (seed 42). Real open data only calibrates country weights, NCM codes
> and municipality locations - see `docs/data-sources.md`."""),
    code("""import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
T = {p.stem: pd.read_csv(p) for p in (ROOT / "data/generated/full/tables").glob("*.csv")}
M = json.loads((ROOT / "reports/metrics.json").read_text(encoding="utf-8"))
BLUE, ORANGE, GRAY = "#257de0", "#f47230", "#9c9c9c"
print({k: len(v) for k, v in sorted(T.items())})"""),
    md("""## 1. The real anchor: where Brazil imports implants from

UN Comtrade, reporter Brazil, 2024, HS 9021.10 / 9021.31 / 9021.39 / 9021.90 (ComexStat was down at extraction
time). These shares weight the countries of plants and tier-1 suppliers."""),
    code("""imp = pd.read_csv(ROOT / "data/reference/br_imports_9021_by_origin_2024.csv")
by = imp.groupby("partner_name").cif_usd.sum().sort_values(ascending=False)
print(f"Total CIF 2024: US$ {by.sum()/1e6:,.1f} M")
(by.head(10) / by.sum() * 100).round(1).rename("% of CIF").to_frame()"""),
    md("""## 2. The synthetic network

Concentration is deliberate: deep components are assigned with linear preferential attachment, so a few tier-2
hubs emerge; some raw materials have one to three producers."""),
    code("""s = T["supplies"]
deg = s.groupby("supplier_id").size().rename("items")
tiers = T["suppliers"].set_index("id").tier
fig, ax = plt.subplots(1, 2, figsize=(11, 3.5))
for t, c in ((1, ORANGE), (2, BLUE), (3, GRAY)):
    ax[0].hist(deg[tiers[deg.index] == t], bins=30, alpha=0.75, color=c, label=f"tier {t}")
ax[0].set_title("Items supplied per supplier"); ax[0].legend(frameon=False)
ax[1].hist(s.lead_time_days, bins=40, color=BLUE)
ax[1].set_title("Supplier lead time (days) - lognormal by region")
plt.tight_layout()"""),
    code("""c = T["consumes"]
dem = c.groupby("hospital_id").revenue_month.sum().sort_values(ascending=False)
share_top10 = dem.head(int(len(dem) * 0.1)).sum() / dem.sum()
print(f"Top 10% of hospitals = {share_top10:.0%} of revenue (long tail by design)")
dem.reset_index(drop=True).plot(logy=True, color=BLUE, title="Revenue per hospital (log), ranked");"""),
    md("""## 3. The false dual-source (section 9B)

A level-1 component bought from two or three tier-1 suppliers *looks* safe in the ERP. In the graph we follow
each supplier's own sub-tier purchases (BOM-consistent `BUYS_FROM` chains) and ask whether all of them depend
100% on the same upstream supplier."""),
    code("""b = M["B"]
print(f"{b['false_dual_items']} of {b['multi_sourced_l1_items']} multi-sourced items ({b['false_dual_pct']}%) "
      f"converge on one upstream supplier -> {b['revenue_exposed_pct']}% of revenue")
pd.read_csv(ROOT / "reports/analytics/B1_hidden_suppliers_ranking.csv").head(10)"""),
    md("""## 4. ERP view vs graph view by country (section 9C)

Hard dependency = revenue of implants that have at least one input sourced 100% from the country."""),
    code("""geo = pd.read_csv(ROOT / "reports/analytics/C2_geo_hard_dependency.csv").head(10)
geo.assign(hidden_pp=geo.graph_pct - geo.erp_pct)"""),
    md("![ERP vs graph](../docs/img/geo_erp_vs_graph.png)"),
    md("""## 5. Who can really stop the business? (section 9D, TTS x TTR)"""),
    code("""r = pd.read_csv(ROOT / "reports/analytics/D_supplier_risk_ranking.csv")
print("Tier of the 10 suppliers with the highest revenue at risk:", r.head(10).tier.tolist())
print("Position of the first tier-1 supplier:", int(r.index[r.tier == 1][0]) + 1)
r.head(10)[["supplier_id", "tier", "country", "revenue_at_risk", "hospitals_affected", "first_stockout_day"]]"""),
    md("![TTS x TTR](../docs/img/tts_vs_ttr_worst_supplier.png)"),
    md("""## 6. Recall in milliseconds (section 9E)"""),
    code("""e = M["E"]
print(f"Raw lot {e['lot_id']}: {e['finished_lots']} implant lots, {e['units_implanted_or_delivered']:,} units "
      f"delivered to {e['hospitals']} hospitals in {e['ufs']} states, {e['units_in_stock_to_quarantine']} units "
      f"to quarantine. Forward trace: {e['forward_ms']:.0f} ms, backward: {e['backward_ms']:.0f} ms")"""),
    md("""## 7. Graph algorithms and the criticality index (section 10)"""),
    code("""g = M["GDS"]
print("Leiden:", g["leiden"], "| vs purchasing categories:", g["communities_vs_categories"])
pd.DataFrame(M["criticality"]["sensitivity"])"""),
    md("""## 8. Graph vs relational benchmark (section 11)"""),
    code("""bm = pd.read_csv(ROOT / "reports/benchmark/results.csv")
bm.pivot_table(index=["size", "bom_depth"], columns="question", values="speedup_graph").round(2)"""),
    md("""`speedup_graph` > 1 would mean Neo4j was faster. It is below 1 everywhere: DuckDB won all 18 cases on these
whole-network batch questions. The graph's case is expressiveness (3-6x fewer lines), interactive point queries and
graph algorithms - see `docs/benchmarks.md` for the full reading."""),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = ROOT / "notebooks" / "01_supplygraph_story.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print(out)
