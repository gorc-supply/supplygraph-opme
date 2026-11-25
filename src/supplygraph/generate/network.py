"""Deterministic synthetic generator for the SupplyGraph OPME network.

Output: a dict of normalised tables (pandas DataFrames). The same tables feed
(a) the Neo4j loader (UNWIND/MERGE), (b) neo4j-admin bulk import and (c) DuckDB.

Design notes (see docs/data-model.md):
* BOM is built level by level (finished=0, components 1..D-1, raw at the bottom) so COMPONENT_OF
  is a DAG by construction.
* Deep components are assigned to tier-2 suppliers with preferential attachment
  (p ~ (degree+1)^alpha) -> a few hub suppliers, which is where hidden risk concentrates.
* Some raw materials are deliberately single/few-sourced (config.sourcing.concentrated_raw).
* "False dual-source": for a share of multi-sourced level-1 items, every tier-1 supplier buys
  one sub-component from the SAME upstream supplier (BUYS_FROM share 100%).
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from supplygraph.config import NetworkConfig
from supplygraph.generate import anchors
from supplygraph.generate.catalog import (
    BR_PORTS,
    CATEGORIES,
    COMMON_DEEP,
    COUNTRIES,
    DEEP_DESCRIPTORS,
    L1_DESCRIPTORS,
    PORTS,
    RAW_MATERIALS,
    SUPPLIER_WORDS,
)

REGION_LEAD_MEDIAN = {  # supplier lead time median (days) by region, relative to Brazil (synthetic)
    "South America": 28,
    "North America": 38,
    "Central America": 35,
    "Europe": 48,
    "Middle East": 50,
    "Asia": 60,
}
AIR_LEAD = {
    "South America": 2,
    "North America": 2.5,
    "Central America": 2.5,
    "Europe": 3.5,
    "Middle East": 4,
    "Asia": 5,
}
SEA_LEAD = {
    "South America": 10,
    "North America": 18,
    "Central America": 16,
    "Europe": 25,
    "Middle East": 30,
    "Asia": 40,
}
AIR_COST = {
    "South America": 12,
    "North America": 18,
    "Central America": 18,
    "Europe": 24,
    "Middle East": 26,
    "Asia": 30,
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _shares(rng: np.random.Generator, n: int, alpha: list[float] | None = None) -> list[float]:
    """Dirichlet shares in percent, rounded to 0.1 and forced to sum to exactly 100."""
    if n == 1:
        return [100.0]
    a = alpha if alpha is not None else [2.0] * n
    raw = rng.dirichlet(a[:n]) * 100
    raw = np.maximum(raw, 2.0)
    raw = raw / raw.sum() * 100
    vals = [round(float(x), 1) for x in raw]
    vals[int(np.argmax(vals))] += round(100.0 - sum(vals), 1)
    return [round(v, 1) for v in vals]


@dataclass
class Net:
    """Mutable working state while generating."""

    items: list[dict] = field(default_factory=list)
    bom: list[dict] = field(default_factory=list)  # child_sku, parent_sku, qty_per
    suppliers: list[dict] = field(default_factory=list)
    supplies: list[dict] = field(default_factory=list)
    buys_from: list[dict] = field(default_factory=list)


class Generator:
    def __init__(self, cfg: NetworkConfig):
        self.cfg = cfg
        self.p = cfg.profile
        self.rng = np.random.default_rng(cfg.seed)
        self.as_of = date.fromisoformat(cfg.as_of)
        self.net = Net()

    # ------------------------------------------------------------------ countries
    def _countries(self) -> pd.DataFrame:
        imports = anchors.read_imports(self.cfg.reference_year)
        by_iso3 = imports.groupby("partner_iso3")["cif_usd"].sum()
        rows = []
        br_lat, br_lon = -15.79, -47.88
        dists = {c[0]: haversine_km(br_lat, br_lon, c[4], c[5]) for c in COUNTRIES}
        max_d = max(dists.values())
        for iso2, iso3, name, region, lat, lon in COUNTRIES:
            # Synthetic geo-risk proxy: grows with distance to Brazil + seeded noise. NOT a geopolitical assessment.
            geo = 0.12 + 0.5 * dists[iso2] / max_d + float(self.rng.uniform(0, 0.25))
            rows.append(
                {
                    "iso2": iso2,
                    "iso3": iso3,
                    "name": name,
                    "region": region,
                    "geo_risk_score": round(min(geo, 1.0), 3),
                    "import_share_9021": float(by_iso3.get(iso3, 0.0)),
                    "lat": lat,
                    "lon": lon,
                }
            )
        df = pd.DataFrame(rows)
        total = by_iso3[[c for c in by_iso3.index if c != "BRA"]].sum()
        df["import_share_9021"] = (df["import_share_9021"] / total).round(5)
        df.loc[df.iso2 == "BR", "import_share_9021"] = 0.0
        return df

    def _country_sampler(self, weights: dict[str, float]):
        keys = sorted(weights)
        w = np.array([weights[k] for k in keys], dtype=float)
        w = w / w.sum()
        return lambda: keys[int(self.rng.choice(len(keys), p=w))]

    # ------------------------------------------------------------------------ BOM
    def _build_items_and_bom(self) -> None:
        p, rng = self.p, self.rng
        D = p.bom_depth
        cats = sorted(CATEGORIES)
        cat_w = np.array([CATEGORIES[c]["weight"] for c in cats])
        cat_w = cat_w / cat_w.sum()
        n_by_cat = {c: max(2, int(round(p.n_finished * w))) for c, w in zip(cats, cat_w, strict=True)}
        diff = p.n_finished - sum(n_by_cat.values())
        n_by_cat[cats[0]] += diff
        ncm_valid = anchors.validate_ncm_codes(sorted({n for c in CATEGORIES.values() for n in c["ncm"]}))
        bad = [k for k, ok in ncm_valid.items() if not ok]
        if bad:
            raise ValueError(f"NCM codes not found in the official Siscomex table: {bad}")

        items: list[dict] = []
        bom: list[dict] = []
        # raw materials
        for code, (name, cost, fam) in sorted(RAW_MATERIALS.items()):
            items.append(
                {
                    "sku": f"RM-{code}",
                    "name": name,
                    "type": "RAW",
                    "category": "RAW",
                    "family": fam,
                    "level": D,
                    "anvisa_risk_class": None,
                    "ncm": None,
                    "unit_cost": round(cost * float(rng.uniform(0.9, 1.1)), 2),
                    "unit_price": None,
                    "raw_code": code,
                }
            )
        # common deep pools per family (levels 2..D-1)
        pools: dict[tuple[str, int], list[str]] = defaultdict(
            list
        )  # (category or family:COMMON, level) -> skus
        counter = defaultdict(int)

        def new_component(cat: str, fam: str, level: int, common_name: str | None = None) -> str:
            counter[level] += 1
            sku = f"CP-L{level}-{counter[level]:04d}"
            if common_name:
                name = f"{common_name} (L{level}-{counter[level]:04d})"
            else:
                desc = (L1_DESCRIPTORS if level == 1 else DEEP_DESCRIPTORS)[int(rng.integers(0, 10))]
                name = f"{cat.title()} {desc} {counter[level]:04d}"
            items.append(
                {
                    "sku": sku,
                    "name": name,
                    "type": "COMPONENT",
                    "category": cat if not common_name else f"{fam}-COMMON",
                    "family": fam,
                    "level": level,
                    "anvisa_risk_class": None,
                    "ncm": None,
                    "unit_cost": None,
                    "unit_price": None,
                    "raw_code": None,
                }
            )
            return sku

        fin_counter = 0
        finished_by_cat: dict[str, list[str]] = {}
        for cat in cats:
            meta = CATEGORIES[cat]
            fam = meta["family"]
            l1_n = max(2, math.ceil(n_by_cat[cat] * p.l1_per_finished))
            for _ in range(l1_n):
                pools[(cat, 1)].append(new_component(cat, fam, 1))
            prev = l1_n
            for lvl in range(2, D):
                n = max(2, math.ceil(prev * p.level_decay))
                for _ in range(n):
                    pools[(cat, lvl)].append(new_component(cat, fam, lvl))
                prev = n
            finished_by_cat[cat] = []
            for k in range(n_by_cat[cat]):
                fin_counter += 1
                tmpl = meta["templates"][k % len(meta["templates"])]
                size = (k // len(meta["templates"])) + 1
                sku = f"FG-{cat}-{fin_counter:04d}"
                lo, hi = meta["price"]
                price = round(float(np.exp(rng.uniform(math.log(lo), math.log(hi)))), -1)
                items.append(
                    {
                        "sku": sku,
                        "name": f"{tmpl} - variant {size}",
                        "type": "FINISHED",
                        "category": cat,
                        "family": fam,
                        "level": 0,
                        "anvisa_risk_class": meta["anvisa"],
                        "ncm": meta["ncm"][k % len(meta["ncm"])],
                        "unit_cost": round(price * 0.45, 2),
                        "unit_price": price,
                        "raw_code": None,
                    }
                )
                finished_by_cat[cat].append(sku)
        for fam in ("ORTHO", "CARDIO"):
            for lvl in range(2, D):
                fam_cat_n = sum(len(pools[(c, lvl)]) for c in cats if CATEGORIES[c]["family"] == fam)
                n = max(1, math.ceil(fam_cat_n * 0.2))
                names = COMMON_DEEP[fam]
                for j in range(n):
                    pools[(f"{fam}-COMMON", lvl)].append(new_component(fam, fam, lvl, names[j % len(names)]))

        # popularity weights (Zipf) so that some components are shared by many parents
        def pick(pool: list[str], k: int) -> list[str]:
            k = min(k, len(pool))
            w = 1.0 / np.arange(1, len(pool) + 1) ** 0.8
            perm = rng.permutation(len(pool))  # random rank per draw-set keeps it seeded but varied
            w = w[np.argsort(perm)]
            w = w / w.sum()
            idx = rng.choice(len(pool), size=k, replace=False, p=w)
            return [pool[i] for i in sorted(idx)]

        def raw_for(cat: str, k: int) -> list[str]:
            raws = CATEGORIES[cat]["raw"]
            w = np.array([1.0 / (i + 1) for i in range(len(raws))])
            w = w / w.sum()
            idx = rng.choice(len(raws), size=min(k, len(raws)), replace=False, p=w)
            return [f"RM-{raws[i]}" for i in sorted(idx)]

        parents_of: dict[str, list[str]] = defaultdict(list)
        children_of: dict[str, list[str]] = defaultdict(list)

        def link(child: str, parent: str, qty: float) -> None:
            if child in children_of[parent]:
                return
            bom.append({"child_sku": child, "parent_sku": parent, "qty_per": qty})
            children_of[parent].append(child)
            parents_of[child].append(parent)

        for cat in cats:
            fam = CATEGORIES[cat]["family"]
            for f in finished_by_cat[cat]:
                for c in pick(pools[(cat, 1)], int(rng.integers(2, 5))):
                    link(c, f, float(rng.choice([1, 1, 1, 2])))
            for lvl in range(1, D):
                for comp in pools[(cat, lvl)]:
                    if lvl == D - 1:
                        for r in raw_for(cat, int(rng.integers(1, 3))):
                            link(r, comp, round(float(rng.uniform(0.02, 0.6)), 3))
                        continue
                    deeper = pools[(cat, lvl + 1)]
                    common = pools[(f"{fam}-COMMON", lvl + 1)]
                    for c in pick(deeper, int(rng.integers(1, 3))):
                        link(c, comp, float(rng.choice([1, 1, 2])))
                    if common and rng.random() < 0.4:
                        link(common[int(rng.integers(0, len(common)))], comp, 1.0)
                    if rng.random() < 0.2:
                        link(raw_for(cat, 1)[0], comp, round(float(rng.uniform(0.01, 0.2)), 3))
            # common components at level < D-1 need children too
        for fam in ("ORTHO", "CARDIO"):
            fam_cats = [c for c in cats if CATEGORIES[c]["family"] == fam]
            for lvl in range(2, D):
                for comp in pools[(f"{fam}-COMMON", lvl)]:
                    cat = fam_cats[int(rng.integers(0, len(fam_cats)))]
                    if lvl == D - 1:
                        for r in raw_for(cat, 1):
                            link(r, comp, round(float(rng.uniform(0.05, 0.8)), 3))
                    else:
                        nxt = pools[(f"{fam}-COMMON", lvl + 1)] or pools[(cat, lvl + 1)]
                        link(nxt[int(rng.integers(0, len(nxt)))], comp, 1.0)
        # every component must be used by at least one parent (no orphan components)
        for (key, lvl), pool in sorted(pools.items()):
            for comp in pool:
                if parents_of[comp]:
                    continue
                if lvl == 1:
                    cands = finished_by_cat[key]
                else:
                    fam = key.split("-")[0] if key.endswith("COMMON") else CATEGORIES[key]["family"]
                    cands = (
                        pools[(key, lvl - 1)]
                        if not key.endswith("COMMON")
                        else [s for c in cats if CATEGORIES[c]["family"] == fam for s in pools[(c, lvl - 1)]]
                    )
                link(comp, cands[int(rng.integers(0, len(cands)))], 1.0)
        # every raw material should be used somewhere
        for code in sorted(RAW_MATERIALS):
            sku = f"RM-{code}"
            if not parents_of[sku]:
                fam = RAW_MATERIALS[code][2]
                cands = [
                    s
                    for (k, lvl), pl in sorted(pools.items())
                    if lvl == D - 1
                    for s in pl
                    if (k.startswith(fam) or (k in CATEGORIES and CATEGORIES[k]["family"] == fam))
                ]
                link(sku, cands[int(rng.integers(0, len(cands)))], 0.1)

        self.net.items = items
        self.net.bom = bom
        self.parents_of = parents_of
        self.children_of = children_of
        self.pools = pools
        self.finished_by_cat = finished_by_cat
        self.item_by_sku = {i["sku"]: i for i in items}
        self._cost_rollup()

    def _cost_rollup(self) -> None:
        """Components cost = sum(children cost * qty) * value-add markup (bottom-up by level)."""
        rng = self.rng
        comps = sorted((i for i in self.net.items if i["type"] == "COMPONENT"), key=lambda x: -x["level"])
        for it in comps:
            base = sum(self.item_by_sku[c]["unit_cost"] * q for c, q in self._children_qty(it["sku"]))
            it["unit_cost"] = round(base * float(rng.uniform(1.4, 2.2)) + float(rng.uniform(20, 300)), 2)

    def _children_qty(self, sku: str) -> list[tuple[str, float]]:
        if not hasattr(self, "_bom_idx"):
            self._bom_idx = defaultdict(list)
            for b in self.net.bom:
                self._bom_idx[b["parent_sku"]].append((b["child_sku"], b["qty_per"]))
        return self._bom_idx[sku]

    # ------------------------------------------------------------------ suppliers
    def _build_suppliers(self, countries: pd.DataFrame) -> None:
        p, rng, src = self.p, self.rng, self.cfg.sourcing
        region = dict(zip(countries.iso2, countries.region, strict=True))
        imp = {r.iso2: r.import_share_9021 for r in countries.itertuples() if r.import_share_9021 > 0}
        t1_weights = {k: v * (1 - src.tier1_domestic_share) for k, v in imp.items()}
        t1_weights["BR"] = src.tier1_domestic_share
        samplers = {
            1: self._country_sampler(t1_weights),
            2: self._country_sampler(src.tier2_country_weights),
            3: self._country_sampler(src.tier3_country_weights),
        }
        n_by_tier = {1: p.n_tier1, 2: p.n_tier2, 3: p.n_tier3}
        suppliers = []
        for tier in (1, 2, 3):
            for k in range(1, n_by_tier[tier] + 1):
                c = samplers[tier]()
                fam = "ORTHO" if rng.random() < 0.6 else "CARDIO"
                word = SUPPLIER_WORDS[tier][int(rng.integers(0, 5))]
                suppliers.append(
                    {
                        "id": f"S-T{tier}-{k:03d}",
                        "name": f"Synth {word} {k:03d} ({c})",
                        "tier": tier,
                        "country_iso2": c,
                        "family": fam,
                        "financial_risk": round(float(rng.beta(2, 5)), 3),
                        "capacity_month": int(rng.lognormal(math.log(5000), 0.6)),
                        "is_certified": bool(
                            rng.random() < (0.9 if tier == 1 else 0.8 if tier == 2 else 0.65)
                        ),
                    }
                )
        by_tier_fam = defaultdict(list)
        for s in suppliers:
            by_tier_fam[(s["tier"], s["family"])].append(s["id"])
        sup_by_id = {s["id"]: s for s in suppliers}
        degree = defaultdict(int)
        supplies: list[dict] = []

        def lead(sid: str) -> float:
            med = REGION_LEAD_MEDIAN[region[sup_by_id[sid]["country_iso2"]]]
            if sup_by_id[sid]["country_iso2"] == "BR":
                med = 18
            return round(float(rng.lognormal(math.log(med), 0.35)), 1)

        def choose(cands: list[str], k: int, alpha: float) -> list[str]:
            k = min(k, len(cands))
            w = np.array([(degree[c] + 1) ** alpha for c in cands], dtype=float)
            w = w / w.sum()
            idx = rng.choice(len(cands), size=k, replace=False, p=w)
            return [cands[i] for i in sorted(idx)]

        def add_supplies(sku: str, sids: list[str], alpha_shares: list[float] | None = None) -> None:
            shares = _shares(rng, len(sids), alpha_shares)
            it = self.item_by_sku[sku]
            for sid, sh in zip(sids, shares, strict=True):
                degree[sid] += 1
                moq = (
                    int(rng.choice([50, 100, 250, 500]))
                    if it["type"] == "RAW"
                    else int(rng.choice([20, 50, 100, 200]))
                )
                supplies.append(
                    {
                        "supplier_id": sid,
                        "item_sku": sku,
                        "share_pct": sh,
                        "lead_time_days": lead(sid),
                        "unit_price": round(it["unit_cost"] * float(rng.uniform(0.95, 1.15)), 2),
                        "moq": moq,
                    }
                )

        # tier-3 -> raw materials (deliberate concentration on a few critical materials)
        t3_all = sorted([s["id"] for s in suppliers if s["tier"] == 3])
        for code in sorted(RAW_MATERIALS):
            fam = RAW_MATERIALS[code][2]
            n = src.concentrated_raw.get(code, int(rng.integers(2, 5)))
            cands = sorted(by_tier_fam[(3, fam)]) or t3_all
            if len(cands) < n:
                cands = t3_all
            # prefer least-used suppliers so every tier-3 gets work, but keep it seeded
            order = sorted(cands, key=lambda c: (degree[c], rng.random()))
            sids = sorted(order[:n])
            add_supplies(
                f"RM-{code}", sids, [6.0, 2.5, 1.0, 0.8, 0.6] if code in src.concentrated_raw else None
            )

        # tier-2 -> deep components (levels >= 2), preferential attachment -> hubs
        deep = sorted(
            (i for i in self.net.items if i["type"] == "COMPONENT" and i["level"] >= 2),
            key=lambda x: x["sku"],
        )
        for it in deep:
            n = int(rng.choice([1, 2, 3], p=src.tier2_supplier_count_probs))
            cands = sorted(by_tier_fam[(2, it["family"])]) or sorted(
                s["id"] for s in suppliers if s["tier"] == 2
            )
            add_supplies(it["sku"], choose(cands, n, src.tier2_concentration_alpha))
        # tier-1 -> level-1 components
        l1 = sorted(
            (i for i in self.net.items if i["type"] == "COMPONENT" and i["level"] == 1),
            key=lambda x: x["sku"],
        )
        for it in l1:
            n = int(rng.choice([1, 2, 3], p=src.tier1_supplier_count_probs))
            cands = sorted(by_tier_fam[(1, it["family"])])
            add_supplies(it["sku"], choose(cands, n, 1.0))

        # no orphan suppliers: idle ones become an extra source of an item of their family and tier
        by_item = defaultdict(list)
        for s in supplies:
            by_item[s["item_sku"]].append(s)
        for s in suppliers:
            if degree[s["id"]] > 0:
                continue
            tier, fam = s["tier"], s["family"]
            if tier == 1:
                pool = [i["sku"] for i in l1 if i["family"] == fam] or [i["sku"] for i in l1]
            elif tier == 2:
                pool = [i["sku"] for i in deep if i["family"] == fam] or [i["sku"] for i in deep]
            else:
                pool = [f"RM-{c}" for c in sorted(RAW_MATERIALS) if c not in src.concentrated_raw]
            if not pool:
                continue
            sku = pool[int(rng.integers(0, len(pool)))]
            rows = by_item[sku]
            sids = [r["supplier_id"] for r in rows] + [s["id"]]
            for r in rows:
                supplies.remove(r)
            for r in rows:
                degree[r["supplier_id"]] -= 1
            by_item[sku] = []
            add_supplies(sku, sids)
            by_item[sku] = [r for r in supplies if r["item_sku"] == sku]

        self.net.suppliers = suppliers
        self.net.supplies = supplies
        self.region = region
        self.sup_by_id = sup_by_id
        self.suppliers_of = defaultdict(list)
        for s in supplies:
            self.suppliers_of[s["item_sku"]].append(s)
        # pipeline lead (days) of each purchased item = share-weighted supplier lead time
        for it in self.net.items:
            rows = self.suppliers_of.get(it["sku"], [])
            if rows:
                it["pipeline_lead_days"] = round(
                    sum(r["lead_time_days"] * r["share_pct"] for r in rows) / 100, 1
                )

    def _build_buys_from(self) -> None:
        """Sub-tier sourcing: which upstream supplier each supplier actually buys each child item from."""
        rng, src = self.rng, self.cfg.sourcing
        out: list[dict] = []
        l1_multi = sorted(
            {
                s["item_sku"]
                for s in self.net.supplies
                if self.item_by_sku[s["item_sku"]]["level"] == 1
                and len(self.suppliers_of[s["item_sku"]]) >= 2
            }
        )
        n_false = int(round(len(l1_multi) * src.false_dual_source_share))
        planted = set(rng.choice(l1_multi, size=n_false, replace=False).tolist()) if n_false else set()
        planted_choice: dict[str, tuple[str, str]] = {}
        for sku in sorted(planted):
            kids = [c for c, _ in self._children_qty(sku) if self.suppliers_of.get(c)]
            if not kids:
                continue
            child = kids[int(rng.integers(0, len(kids)))]
            ups = sorted(self.suppliers_of[child], key=lambda r: -r["share_pct"])
            planted_choice[sku] = (child, ups[0]["supplier_id"])
        self.planted_false_dual = planted_choice

        for s in sorted(self.net.supplies, key=lambda r: (r["item_sku"], r["supplier_id"])):
            sku, buyer = s["item_sku"], s["supplier_id"]
            if self.item_by_sku[sku]["type"] == "RAW":
                continue
            for child, _ in self._children_qty(sku):
                ups = self.suppliers_of.get(child, [])
                if not ups:
                    continue
                if sku in planted_choice and planted_choice[sku][0] == child:
                    sellers, shares = [planted_choice[sku][1]], [100.0]
                else:
                    k = (
                        1
                        if (len(ups) == 1 or rng.random() < self.cfg.sourcing.sub_tier_single_buy_prob)
                        else min(2, len(ups))
                    )
                    # sqrt of the market share: big suppliers win more often, but buyers still diversify
                    w = np.sqrt(np.array([u["share_pct"] for u in ups], dtype=float))
                    idx = rng.choice(len(ups), size=k, replace=False, p=w / w.sum())
                    sellers = sorted(ups[i]["supplier_id"] for i in idx)
                    shares = _shares(rng, len(sellers))
                lead_of = {u["supplier_id"]: u["lead_time_days"] for u in ups}
                for seller, sh in zip(sellers, shares, strict=True):
                    if seller == buyer:
                        continue
                    out.append(
                        {
                            "buyer_id": buyer,
                            "seller_id": seller,
                            "item_sku": child,
                            "for_sku": sku,
                            "share_pct": sh,
                            "lead_time_days": lead_of[seller],
                        }
                    )
        # renormalise per (buyer, item, for) in case a self-loop was dropped
        df = pd.DataFrame(out)
        if not df.empty:
            tot = df.groupby(["buyer_id", "item_sku", "for_sku"])["share_pct"].transform("sum")
            df["share_pct"] = (df["share_pct"] / tot * 100).round(1)
        self.net.buys_from = df.to_dict("records")

    # ---------------------------------------------------------------- plants, logistics
    def _build_plants(self, countries: pd.DataFrame) -> list[dict]:
        p, src = self.p, self.cfg.sourcing
        imp = {
            r.iso2: r.import_share_9021
            for r in countries.itertuples()
            if r.import_share_9021 > 0 and r.iso2 in PORTS
        }
        w = {k: v * (1 - src.plant_domestic_share) for k, v in imp.items()}
        w["BR"] = src.plant_domestic_share
        sample = self._country_sampler(w)
        plants = []
        for k in range(1, p.n_plants + 1):
            fam = "ORTHO" if k <= max(1, round(p.n_plants * 0.6)) else "CARDIO"
            c = sample()
            plants.append(
                {
                    "id": f"P-{k:02d}",
                    "name": f"Synth {fam.title()} Plant {k:02d} ({c})",
                    "country_iso2": c,
                    "family": fam,
                }
            )
        return plants

    def _build_logistics(self, plants: list[dict], dcs: list[dict], countries: pd.DataFrame):
        rng = self.rng
        region = self.region
        ports, ships = [], []
        used = sorted({pl["country_iso2"] for pl in plants if pl["country_iso2"] != "BR"})
        for c in used:
            for code, name, typ in PORTS[c]:
                ports.append({"code": code, "name": name, "country_iso2": c, "type": typ})
        for code, name, typ, lat, lon in BR_PORTS:
            ports.append(
                {"code": code, "name": name, "country_iso2": "BR", "type": typ, "lat": lat, "lon": lon}
            )
        br_air = [p for p in BR_PORTS if p[2] == "air"]
        br_sea = [p for p in BR_PORTS if p[2] == "sea"]

        def edge(frm, ft, to, tt, mode, lt, cost):
            ships.append(
                {
                    "from_id": frm,
                    "from_type": ft,
                    "to_id": to,
                    "to_type": tt,
                    "mode": mode,
                    "lead_time_days": round(lt, 1),
                    "cost_per_unit": round(cost, 2),
                }
            )

        # plant -> origin gateways (foreign) or -> DCs (domestic)
        dc_xy = {d["id"]: (d["lat"], d["lon"]) for d in dcs}
        for pl in plants:
            c = pl["country_iso2"]
            if c == "BR":
                # domestic plant: assume located near Sao Paulo state industrial belt (synthetic)
                lat, lon = -23.0 + float(rng.uniform(-1.2, 1.0)), -47.0 + float(rng.uniform(-1.5, 1.5))
                near = sorted(dcs, key=lambda d: haversine_km(lat, lon, d["lat"], d["lon"]))[:2]
                for d in near:
                    km = haversine_km(lat, lon, d["lat"], d["lon"])
                    edge(pl["id"], "Plant", d["id"], "DC", "road", 1 + km / 500, 3 + 0.01 * km)
                continue
            gws = PORTS[c]
            air = [g for g in gws if g[2] == "air"]
            sea = [g for g in gws if g[2] == "sea"]
            chosen = [air[int(rng.integers(0, len(air)))]] if air else []
            if len(air) > 1 and rng.random() < 0.4:
                chosen = air
            if sea and rng.random() > self.cfg.logistics.air_share:
                chosen.append(sea[0])
            if not chosen:
                chosen = [gws[0]]
            for code, _, _typ in chosen:
                edge(
                    pl["id"],
                    "Plant",
                    code,
                    "Port",
                    "road",
                    float(rng.uniform(0.5, 2.0)),
                    float(rng.uniform(1, 3)),
                )
        # origin gateway -> Brazilian entry gateway
        for prt in [p for p in ports if p["country_iso2"] != "BR"]:
            reg = region[prt["country_iso2"]]
            if prt["type"] == "air":
                targets = [br_air[0]] + [b for b in br_air[1:] if rng.random() < 0.5]
                for b in targets:
                    edge(
                        prt["code"],
                        "Port",
                        b[0],
                        "Port",
                        "air",
                        float(rng.lognormal(math.log(AIR_LEAD[reg]), 0.25)),
                        AIR_COST[reg] * float(rng.uniform(0.85, 1.2)),
                    )
            else:
                targets = [br_sea[0]] + [b for b in br_sea[1:] if rng.random() < 0.45]
                for b in targets:
                    edge(
                        prt["code"],
                        "Port",
                        b[0],
                        "Port",
                        "sea",
                        float(rng.lognormal(math.log(SEA_LEAD[reg]), 0.2)),
                        float(rng.uniform(4, 8)),
                    )
        # BR entry gateway -> nearest DC(s): customs + ANVISA clearance + road leg (synthetic)
        for code, _, typ, lat, lon in BR_PORTS:
            near = sorted(dcs, key=lambda d: haversine_km(lat, lon, d["lat"], d["lon"]))
            targets = [near[0]] + [d for d in near[1:3] if haversine_km(lat, lon, d["lat"], d["lon"]) < 200]
            for d in targets:
                km = haversine_km(lat, lon, d["lat"], d["lon"])
                clearance = float(rng.lognormal(math.log(5 if typ == "air" else 8), 0.3))
                edge(code, "Port", d["id"], "DC", "road", clearance + 1 + km / 500, 4 + 0.01 * km)
        # DC -> DC replenishment: SP hubs feed regional DCs; AM/PA only from the main hub (single corridor)
        hubs = [d for d in dcs if d["uf"] == "SP"]
        main_hub = hubs[0]
        for d in dcs:
            if d["uf"] == "SP":
                continue
            sources = [main_hub] + (
                [hubs[1]] if len(hubs) > 1 and d["uf"] not in ("AM", "PA") and rng.random() < 0.55 else []
            )
            for h in sources:
                km = haversine_km(h["lat"], h["lon"], d["lat"], d["lon"])
                mode = "air" if km > 1800 else "road"
                lt = 2.0 + float(rng.uniform(0, 1)) if mode == "air" else 1 + km / 550
                edge(h["id"], "DC", d["id"], "DC", mode, lt, (22 if mode == "air" else 3) + 0.006 * km)
        if len(hubs) > 1:
            edge(hubs[0]["id"], "DC", hubs[1]["id"], "DC", "road", 1.0, 2.0)
            edge(hubs[1]["id"], "DC", hubs[0]["id"], "DC", "road", 1.0, 2.0)
        regional = [d for d in dcs if d["uf"] not in ("SP", "AM", "PA")]
        for a in regional:
            for b in regional:
                if a["id"] < b["id"]:
                    km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
                    if km < 800 and rng.random() < 0.6:
                        edge(a["id"], "DC", b["id"], "DC", "road", 1 + km / 550, 3 + 0.006 * km)
                        edge(b["id"], "DC", a["id"], "DC", "road", 1 + km / 550, 3 + 0.006 * km)
        _ = dc_xy
        return ports, ships

    @staticmethod
    def _dijkstra(adj: dict[str, list[tuple[str, float]]], src: str) -> dict[str, float]:
        dist = {src: 0.0}
        pq = [(0.0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, math.inf):
                continue
            for v, w in adj.get(u, []):
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist

    # ------------------------------------------------------------------ demand side
    def _build_dcs(self, mun: pd.DataFrame) -> list[dict]:
        dcs, used = [], set()
        counts: dict[str, int] = defaultdict(int)
        for uf in self.cfg.logistics.dc_ufs:
            cands = mun[(mun.uf == uf) & (~mun.ibge_code.isin(used))].sort_values(
                "population_2022", ascending=False
            )
            if cands.empty:
                continue
            m = cands.iloc[0]
            used.add(m.ibge_code)
            counts[uf] += 1
            dcs.append(
                {
                    "id": f"DC-{uf}{counts[uf]}",
                    "name": f"DC {m.municipality}/{uf}",
                    "uf": uf,
                    "municipality": m.municipality,
                    "lat": round(float(m.lat), 4),
                    "lon": round(float(m.lon), 4),
                }
            )
        return dcs

    def _build_hospitals(self, mun: pd.DataFrame, dcs: list[dict]):
        rng, p = self.rng, self.p
        top = (
            mun.sort_values("population_2022", ascending=False)
            .head(p.n_municipalities)
            .reset_index(drop=True)
        )
        w = top.population_2022.to_numpy(dtype=float) ** 0.9
        w = w / w.sum()
        idx = np.sort(rng.choice(len(top), size=p.n_hospitals, p=w))
        hospitals = []
        for k, i in enumerate(idx, start=1):
            m = top.iloc[int(i)]
            size = float(rng.lognormal(0, 0.8))
            hospitals.append(
                {
                    "id": f"H-{k:04d}",
                    "name": f"Synthetic Hospital {k:04d} ({m.municipality}/{m.uf})",
                    "uf": m.uf,
                    "municipality": m.municipality,
                    "lat": round(float(m.lat) + float(rng.normal(0, 0.03)), 5),
                    "lon": round(float(m.lon) + float(rng.normal(0, 0.03)), 5),
                    "type": "public" if rng.random() < 0.55 else "private",
                    "size_index": round(size, 3),
                }
            )
        serves = []
        for h in hospitals:
            near = sorted(dcs, key=lambda d: haversine_km(h["lat"], h["lon"], d["lat"], d["lon"]))
            targets = [near[0]]
            if len(near) > 1:
                km2 = haversine_km(h["lat"], h["lon"], near[1]["lat"], near[1]["lon"])
                if (
                    km2 < self.cfg.logistics.second_dc_max_km
                    and rng.random() < self.cfg.logistics.second_dc_probability
                ):
                    targets.append(near[1])
            for rank, d in enumerate(targets):
                km = haversine_km(h["lat"], h["lon"], d["lat"], d["lon"])
                lt = 1 + km / 500 if km < 1500 else 2.5
                serves.append(
                    {
                        "dc_id": d["id"],
                        "hospital_id": h["id"],
                        "lead_time_days": round(lt, 1),
                        "cost_per_unit": round(15 + 0.02 * km, 2),
                        "is_primary": rank == 0,
                    }
                )
        # consumption: hospitals consume finished SKUs of the categories they practise
        fin = [i for i in self.net.items if i["type"] == "FINISHED"]
        popularity = {i["sku"]: float(rng.lognormal(0, 0.9)) for i in fin}
        consumes = []
        for h in hospitals:
            size = h["size_index"]
            cats = [
                c
                for c in sorted(CATEGORIES)
                if (CATEGORIES[c]["family"] == "ORTHO" and rng.random() < 0.9)
                or (CATEGORIES[c]["family"] == "CARDIO" and rng.random() < min(0.95, 0.2 + 0.3 * size))
            ]
            if not cats:
                cats = ["TRAUMA"]
            pool = [i for i in fin if i["category"] in cats]
            k = int(min(len(pool), max(2, rng.poisson(p.skus_per_hospital * math.sqrt(size)))))
            pw = np.array([popularity[i["sku"]] for i in pool])
            chosen = rng.choice(len(pool), size=k, replace=False, p=pw / pw.sum())
            for j in sorted(chosen):
                it = pool[int(j)]
                mean = CATEGORIES[it["category"]]["demand"] * size * popularity[it["sku"]] * 0.03
                dem = int(max(1, rng.poisson(mean)))
                consumes.append(
                    {
                        "hospital_id": h["id"],
                        "item_sku": it["sku"],
                        "monthly_demand": dem,
                        "revenue_month": round(dem * it["unit_price"], 2),
                    }
                )
        return hospitals, serves, consumes

    # ------------------------------------------------------------------------ lots
    def _build_lots(self, plants_of: dict[str, list[str]], consumes: list[dict]) -> tuple[list, list, list]:
        rng, p = self.rng, self.p
        as_of = self.as_of
        demand = defaultdict(int)
        hosp_by_item = defaultdict(list)
        for c in consumes:
            demand[c["item_sku"]] += c["monthly_demand"]
            hosp_by_item[c["item_sku"]].append((c["hospital_id"], c["monthly_demand"]))
        fin = sorted((i for i in self.net.items if i["type"] == "FINISHED"), key=lambda x: x["sku"])
        mean_dem = np.mean([demand[i["sku"]] for i in fin if demand[i["sku"]] > 0]) or 1
        lots, derived, delivered = [], [], []
        lot_seq = defaultdict(int)

        def lot_id(sku: str) -> str:
            lot_seq[sku] += 1
            return f"{sku}-L{lot_seq[sku]:04d}"

        def status_for(mfg: date, shelf_years: int) -> tuple[str, date]:
            exp = mfg + timedelta(days=365 * shelf_years)
            if exp < as_of:
                return "expired", exp
            r = rng.random()
            return ("quarantine" if r < 0.015 else "recalled" if r < 0.019 else "released"), exp

        # uses[(component_sku)] -> list of (child_lot_id, use_date, qty_needed)
        uses: dict[str, list[tuple[str, date, float]]] = defaultdict(list)
        span = 6 * 365
        for it in fin:
            sku = it["sku"]
            if demand[sku] == 0:
                continue
            n = int(np.clip(round(p.lots_per_finished * demand[sku] / mean_dem), 3, 4 * p.lots_per_finished))
            per_lot = max(5, math.ceil(demand[sku] * 72 / n))
            trace = [c for c, _ in self._children_qty(sku)][: 1 + int(rng.random() < 0.5)]
            hs = hosp_by_item[sku]
            hw = np.array([d for _, d in hs], dtype=float)
            hw = hw / hw.sum()
            for _ in range(n):
                mfg = as_of - timedelta(days=int(rng.integers(10, span)))
                st, exp = status_for(mfg, 5)
                qty = int(per_lot * rng.uniform(0.7, 1.3))
                lid = lot_id(sku)
                src = plants_of[sku][int(rng.integers(0, len(plants_of[sku])))]
                lots.append(
                    {
                        "lot_id": lid,
                        "item_sku": sku,
                        "qty": qty,
                        "mfg_date": mfg.isoformat(),
                        "expiry_date": exp.isoformat(),
                        "status": st,
                        "source_id": src,
                    }
                )
                for c in trace:
                    qty_per = dict(self._children_qty(sku))[c]
                    uses[c].append((lid, mfg, qty * qty_per))
                age = (as_of - mfg).days
                if st == "quarantine" or age < 20:
                    continue
                frac = (
                    float(rng.uniform(0.85, 1.0)) if age > 365 else age / 365 * float(rng.uniform(0.6, 1.0))
                )
                to_ship = int(qty * frac)
                k = int(min(len(hs), rng.integers(1, 4)))
                idx = rng.choice(len(hs), size=k, replace=False, p=hw)
                parts = rng.multinomial(to_ship, [1 / k] * k) if to_ship > 0 else [0] * k
                for j, q in zip(sorted(idx), parts, strict=True):
                    if q <= 0:
                        continue
                    d = mfg + timedelta(days=int(rng.integers(15, max(16, min(age, 400)))))
                    delivered.append(
                        {"lot_id": lid, "hospital_id": hs[int(j)][0], "date": d.isoformat(), "qty": int(q)}
                    )

        # components and raw: group downstream uses chronologically into lots (bottom-up by level)
        levels = sorted({i["level"] for i in self.net.items if i["type"] != "FINISHED"})
        by_level = defaultdict(list)
        for i in self.net.items:
            if i["type"] != "FINISHED":
                by_level[i["level"]].append(i["sku"])
        processed: set[str] = set()
        for lvl in levels:  # level 1 first: its lots create uses for deeper levels
            for sku in sorted(by_level[lvl]):
                processed.add(sku)
                self._lots_for_component(sku, uses, lots, derived, lot_id, status_for)
        # raw materials may receive uses from any level -> process anything left
        for sku in sorted(set(uses) - processed):
            self._lots_for_component(sku, uses, lots, derived, lot_id, status_for)
        return lots, derived, delivered

    def _lots_for_component(self, sku, uses, lots, derived, lot_id, status_for) -> None:
        rng, p = self.rng, self.p
        u = sorted(uses.get(sku, []), key=lambda x: x[1])
        if not u:
            return
        it = self.item_by_sku[sku]
        reuse = p.raw_lot_reuse if it["type"] == "RAW" else p.component_lot_reuse
        group = max(1, int(round(reuse)))
        kids = [c for c, _ in self._children_qty(sku)]
        primary = kids[0] if kids else None
        sups = self.suppliers_of.get(sku, [])
        sw = np.array([s["share_pct"] for s in sups], dtype=float)
        for g in range(0, len(u), group):
            chunk = u[g : g + group]
            mfg = chunk[0][1] - timedelta(days=int(rng.integers(15, 90)))
            need = sum(q for _, _, q in chunk)
            st, exp = status_for(mfg, 10 if it["type"] == "RAW" else 8)
            if st == "quarantine":
                st = "released"
            lid = lot_id(sku)
            src = sups[int(rng.choice(len(sups), p=sw / sw.sum()))]["supplier_id"] if sups else None
            lots.append(
                {
                    "lot_id": lid,
                    "item_sku": sku,
                    "qty": round(need * float(rng.uniform(1.05, 1.3)), 3),
                    "mfg_date": mfg.isoformat(),
                    "expiry_date": exp.isoformat(),
                    "status": st,
                    "source_id": src,
                }
            )
            for child_lot, _, q in chunk:
                derived.append({"child_lot_id": child_lot, "parent_lot_id": lid, "qty_used": round(q, 3)})
            if primary:
                qty_per = dict(self._children_qty(sku))[primary]
                uses[primary].append((lid, mfg, need * qty_per))

    # ------------------------------------------------------------------------ main
    def run(self) -> dict[str, pd.DataFrame]:
        cfg, rng = self.cfg, self.rng
        countries = self._countries()
        mun = anchors.read_municipalities()
        self._build_items_and_bom()
        self._build_suppliers(countries)
        self._build_buys_from()
        plants = self._build_plants(countries)
        dcs = self._build_dcs(mun)
        hospitals, serves, consumes = self._build_hospitals(mun, dcs)

        # plants manufacture finished items of their family
        fin = sorted((i for i in self.net.items if i["type"] == "FINISHED"), key=lambda x: x["sku"])
        demand = defaultdict(int)
        for c in consumes:
            demand[c["item_sku"]] += c["monthly_demand"]
        plants_by_fam = defaultdict(list)
        for pl in plants:
            plants_by_fam[pl["family"]].append(pl["id"])
        plant_w = {pl["id"]: float(rng.lognormal(0, 0.5)) for pl in plants}
        manufactures, plants_of = [], defaultdict(list)
        for it in fin:
            cands = plants_by_fam[it["family"]] or [pl["id"] for pl in plants]
            w = np.array([plant_w[c] for c in cands])
            k = 2 if (len(cands) > 1 and rng.random() < 0.12) else 1
            chosen = sorted(rng.choice(len(cands), size=k, replace=False, p=w / w.sum()))
            shares = _shares(rng, k)
            for j, sh in zip(chosen, shares, strict=True):
                pid = cands[int(j)]
                plants_of[it["sku"]].append(pid)
                manufactures.append(
                    {
                        "plant_id": pid,
                        "item_sku": it["sku"],
                        "share_pct": sh,
                        "capacity_month": int(max(10, demand[it["sku"]] * sh / 100 * rng.uniform(1.2, 2.0))),
                    }
                )
            it["pipeline_lead_days"] = round(
                float(rng.lognormal(math.log(12), 0.3)), 1
            )  # manufacturing cycle

        ports, ships = self._build_logistics(plants, dcs, countries)
        # transit days plant -> DC (min lead-time path) used for in-transit cover (TTS)
        adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for e in ships:
            adj[e["from_id"]].append((e["to_id"], e["lead_time_days"]))
        transit = {pl["id"]: self._dijkstra(adj, pl["id"]) for pl in plants}

        # stocks: each DC stocks what its primary hospitals consume
        primary_dc = {s["hospital_id"]: s["dc_id"] for s in serves if s["is_primary"]}
        dc_dem: dict[tuple[str, str], float] = defaultdict(float)
        for c in consumes:
            dc_dem[(primary_dc[c["hospital_id"]], c["item_sku"])] += c["monthly_demand"]
        inv = cfg.inventory
        stocks = []
        for (dc, sku), m in sorted(dc_dem.items()):
            add = m / 30.0
            cover = float(
                np.clip(rng.lognormal(math.log(inv.days_cover_median), inv.days_cover_sigma), 4, 180)
            )
            tdays = min(transit[pid].get(dc, math.inf) for pid in plants_of[sku])
            stocks.append(
                {
                    "dc_id": dc,
                    "item_sku": sku,
                    "on_hand": int(max(2, round(add * cover))),
                    "avg_daily_demand": round(add, 4),
                    "safety_stock": int(max(1, round(add * inv.safety_stock_days))),
                    "transit_days": round(tdays, 1) if math.isfinite(tdays) else None,
                }
            )

        # substitution between finished items of the same template family + a few raw alternatives
        subs = []
        for _cat, skus in sorted(self.finished_by_cat.items()):
            for s in skus:
                if rng.random() < 0.35:
                    others = [o for o in skus if o != s]
                    for o in rng.choice(
                        others, size=min(len(others), int(rng.integers(1, 3))), replace=False
                    ):
                        subs.append(
                            {
                                "from_sku": s,
                                "to_sku": str(o),
                                "requalification_days": int(rng.integers(20, 181)),
                            }
                        )
        for a, b, d in [
            ("RM-TI64", "RM-CPTI", 240),
            ("RM-SS316", "RM-TI64", 300),
            ("RM-PET", "RM-EPTFE", 365),
        ]:
            subs.append({"from_sku": a, "to_sku": b, "requalification_days": d})

        # criticality (finished: ANVISA class IV or top-20% revenue; components: sole-sourced or widely used)
        rev = defaultdict(float)
        for c in consumes:
            rev[c["item_sku"]] += c["revenue_month"]
        thr = np.quantile([rev[i["sku"]] for i in fin], 0.8) if fin else 0
        where_used = self._where_used_counts()
        for it in self.net.items:
            if it["type"] == "FINISHED":
                it["criticality"] = (
                    "HIGH" if (it["anvisa_risk_class"] == "IV" or rev[it["sku"]] >= thr) else "MEDIUM"
                )
            else:
                n_src = len(self.suppliers_of.get(it["sku"], []))
                wu = where_used.get(it["sku"], 0)
                it["criticality"] = "HIGH" if (n_src == 1 or wu >= 10) else "MEDIUM" if wu >= 3 else "LOW"
            it["revenue_month"] = round(rev.get(it["sku"], 0.0), 2) if it["type"] == "FINISHED" else None

        lots, derived, delivered = ([], [], [])
        if self.p.include_lots:
            lots, derived, delivered = self._build_lots(plants_of, consumes)

        t = {
            "countries": countries.drop(columns=["iso3"]).rename(columns={}),
            "ports": pd.DataFrame(ports),
            "suppliers": pd.DataFrame(self.net.suppliers),
            "items": pd.DataFrame(self.net.items).drop(columns=["raw_code"]),
            "plants": pd.DataFrame(plants),
            "dcs": pd.DataFrame(dcs),
            "hospitals": pd.DataFrame(hospitals),
            "lots": pd.DataFrame(
                lots, columns=["lot_id", "item_sku", "qty", "mfg_date", "expiry_date", "status", "source_id"]
            ),
            "supplies": pd.DataFrame(self.net.supplies),
            "buys_from": pd.DataFrame(self.net.buys_from),
            "bom": pd.DataFrame(self.net.bom),
            "manufactures": pd.DataFrame(manufactures),
            "ships_to": pd.DataFrame(ships),
            "stocks": pd.DataFrame(stocks),
            "serves": pd.DataFrame(serves),
            "consumes": pd.DataFrame(consumes),
            "can_substitute": pd.DataFrame(subs),
            "derived_from": pd.DataFrame(derived, columns=["child_lot_id", "parent_lot_id", "qty_used"]),
            "delivered_to": pd.DataFrame(delivered, columns=["lot_id", "hospital_id", "date", "qty"]),
        }
        t["planted_false_dual_source"] = pd.DataFrame(
            [
                {"item_sku": k, "child_sku": v[0], "upstream_supplier_id": v[1]}
                for k, v in sorted(self.planted_false_dual.items())
            ]
        )
        return t

    def _where_used_counts(self) -> dict[str, int]:
        """Number of finished items whose BOM contains each item (memoised DFS upward)."""
        memo: dict[str, set[str]] = {}

        def up(sku: str) -> set[str]:
            if sku in memo:
                return memo[sku]
            it = self.item_by_sku[sku]
            if it["type"] == "FINISHED":
                memo[sku] = {sku}
                return memo[sku]
            acc: set[str] = set()
            for par in self.parents_of.get(sku, []):
                acc |= up(par)
            memo[sku] = acc
            return acc

        return {s: len(up(s)) for s in self.item_by_sku}


def generate(cfg: NetworkConfig) -> dict[str, pd.DataFrame]:
    return Generator(cfg).run()
