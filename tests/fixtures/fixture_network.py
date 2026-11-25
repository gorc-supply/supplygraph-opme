"""Hand-built mini network with KNOWN answers for the analytics tests.

    R1 (titanium, CN) --> C2a (DE, sole source S-T2-007) --> C1a --> F1, F4
    R1 --------------------------------------------------> C1c --> F3
    R2 (PEEK, US) ----> C2b (S-T2-008 / S-T2-009 50/50) --> C1b --> F2

C1a looks dual-sourced (S-T1-001 + S-T1-002, both BR) but BOTH buy C2a only from S-T2-007:
the planted false dual-source. C1b is "fake dual" one level deeper: S-T1-003 buys from S-T2-008,
S-T1-004 from S-T2-009, and both T2 buy PEEK only from S-T3-002.

Known answers (asserted in tests/test_analytics_fixture.py):
* S-T2-007 down  -> exposed finished SKUs exactly {FG-T-0001, FG-T-0004}; only FG-T-0001 stocks out
  (TTS = 30 cover + 20 pipeline + 5 transit = 55 < 60) -> 5 days x 1 unit/day x R$1,000 = R$5,000.
* false dual-source (strict) -> {CP-T1-A: S-T2-007 & S-T3-001, CP-T1-B: S-T3-002}
* recall of RM-T-R1-L0001 -> 5 derived lots, 2 finished lots, 1 hospital, 3 units in stock.
* routes P-01 -> H-0001: fastest via FRA/GRU (air); avoiding GRU only the sea route remains.
"""

from __future__ import annotations

import pandas as pd


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def fixture_tables() -> dict[str, pd.DataFrame]:
    countries = _df([
        {"iso2": c, "name": n, "region": r, "geo_risk_score": g}
        for c, n, r, g in [("BR", "Brazil", "South America", 0.1), ("DE", "Germany", "Europe", 0.3),
                           ("CN", "China", "Asia", 0.5), ("US", "United States", "North America", 0.2)]
    ])
    item = dict(anvisa_risk_class=None, ncm=None, unit_cost=10.0, criticality="LOW", revenue_month=None)
    items = _df([
        {**item, "sku": "RM-T-R1", "name": "Ti bar", "type": "RAW", "category": "RAW", "family": "ORTHO", "level": 3,
         "unit_price": None, "pipeline_lead_days": 30.0},
        {**item, "sku": "RM-T-R2", "name": "PEEK", "type": "RAW", "category": "RAW", "family": "ORTHO", "level": 3,
         "unit_price": None, "pipeline_lead_days": 30.0},
        {**item, "sku": "CP-T2-A", "name": "Forged blank", "type": "COMPONENT", "category": "HIP", "family": "ORTHO",
         "level": 2, "unit_price": None, "pipeline_lead_days": 15.0},
        {**item, "sku": "CP-T2-B", "name": "PEEK moulding", "type": "COMPONENT", "category": "SPINE",
         "family": "ORTHO", "level": 2, "unit_price": None, "pipeline_lead_days": 15.0},
        {**item, "sku": "CP-T1-A", "name": "Machined stem body", "type": "COMPONENT", "category": "HIP",
         "family": "ORTHO", "level": 1, "unit_price": None, "pipeline_lead_days": 10.0},
        {**item, "sku": "CP-T1-B", "name": "Cage body", "type": "COMPONENT", "category": "SPINE", "family": "ORTHO",
         "level": 1, "unit_price": None, "pipeline_lead_days": 10.0},
        {**item, "sku": "CP-T1-C", "name": "Plate body", "type": "COMPONENT", "category": "TRAUMA",
         "family": "ORTHO", "level": 1, "unit_price": None, "pipeline_lead_days": 10.0},
        {**item, "sku": "FG-T-0001", "name": "Hip stem", "type": "FINISHED", "category": "HIP", "family": "ORTHO",
         "level": 0, "unit_price": 1000.0, "pipeline_lead_days": 10.0, "revenue_month": 30000.0},
        {**item, "sku": "FG-T-0002", "name": "Spine cage", "type": "FINISHED", "category": "SPINE",
         "family": "ORTHO", "level": 0, "unit_price": 1000.0, "pipeline_lead_days": 10.0, "revenue_month": 30000.0},
        {**item, "sku": "FG-T-0003", "name": "Trauma plate", "type": "FINISHED", "category": "TRAUMA",
         "family": "ORTHO", "level": 0, "unit_price": 1000.0, "pipeline_lead_days": 10.0, "revenue_month": 30000.0},
        {**item, "sku": "FG-T-0004", "name": "Hip stem long", "type": "FINISHED", "category": "HIP",
         "family": "ORTHO", "level": 0, "unit_price": 1000.0, "pipeline_lead_days": 10.0, "revenue_month": 30000.0},
    ])
    bom = _df([
        {"child_sku": "RM-T-R1", "parent_sku": "CP-T2-A", "qty_per": 0.5},
        {"child_sku": "RM-T-R2", "parent_sku": "CP-T2-B", "qty_per": 0.2},
        {"child_sku": "CP-T2-A", "parent_sku": "CP-T1-A", "qty_per": 2.0},
        {"child_sku": "CP-T2-B", "parent_sku": "CP-T1-B", "qty_per": 1.0},
        {"child_sku": "RM-T-R1", "parent_sku": "CP-T1-C", "qty_per": 0.3},
        {"child_sku": "CP-T1-A", "parent_sku": "FG-T-0001", "qty_per": 1.0},
        {"child_sku": "CP-T1-A", "parent_sku": "FG-T-0004", "qty_per": 1.0},
        {"child_sku": "CP-T1-B", "parent_sku": "FG-T-0002", "qty_per": 1.0},
        {"child_sku": "CP-T1-C", "parent_sku": "FG-T-0003", "qty_per": 1.0},
    ])
    sup = [("S-T1-001", 1, "BR"), ("S-T1-002", 1, "BR"), ("S-T1-003", 1, "BR"), ("S-T1-004", 1, "BR"),
           ("S-T1-005", 1, "BR"), ("S-T2-007", 2, "DE"), ("S-T2-008", 2, "DE"), ("S-T2-009", 2, "US"),
           ("S-T3-001", 3, "CN"), ("S-T3-002", 3, "US")]
    suppliers = _df([{"id": i, "name": i, "tier": t, "country_iso2": c, "family": "ORTHO", "financial_risk": 0.2,
                      "capacity_month": 1000, "is_certified": True} for i, t, c in sup])

    def s(sid, sku, share, lead=10.0):
        return {"supplier_id": sid, "item_sku": sku, "share_pct": share, "lead_time_days": lead, "unit_price": 10.0,
                "moq": 10}

    supplies = _df([
        s("S-T1-001", "CP-T1-A", 50.0), s("S-T1-002", "CP-T1-A", 50.0),
        s("S-T1-003", "CP-T1-B", 60.0), s("S-T1-004", "CP-T1-B", 40.0),
        s("S-T1-005", "CP-T1-C", 100.0),
        s("S-T2-007", "CP-T2-A", 100.0),
        s("S-T2-008", "CP-T2-B", 50.0), s("S-T2-009", "CP-T2-B", 50.0),
        s("S-T3-001", "RM-T-R1", 100.0), s("S-T3-002", "RM-T-R2", 100.0),
    ])

    def b(buyer, seller, sku, for_sku, share=100.0):
        return {"buyer_id": buyer, "seller_id": seller, "item_sku": sku, "for_sku": for_sku, "share_pct": share,
                "lead_time_days": 10.0}

    buys_from = _df([
        b("S-T1-001", "S-T2-007", "CP-T2-A", "CP-T1-A"), b("S-T1-002", "S-T2-007", "CP-T2-A", "CP-T1-A"),
        b("S-T1-003", "S-T2-008", "CP-T2-B", "CP-T1-B"), b("S-T1-004", "S-T2-009", "CP-T2-B", "CP-T1-B"),
        b("S-T1-005", "S-T3-001", "RM-T-R1", "CP-T1-C"),
        b("S-T2-007", "S-T3-001", "RM-T-R1", "CP-T2-A"),
        b("S-T2-008", "S-T3-002", "RM-T-R2", "CP-T2-B"), b("S-T2-009", "S-T3-002", "RM-T-R2", "CP-T2-B"),
    ])
    plants = _df([{"id": "P-01", "name": "Plant DE", "country_iso2": "DE", "family": "ORTHO"},
                  {"id": "P-02", "name": "Plant BR", "country_iso2": "BR", "family": "ORTHO"}])
    manufactures = _df([
        {"plant_id": "P-01", "item_sku": "FG-T-0001", "share_pct": 100.0, "capacity_month": 100},
        {"plant_id": "P-01", "item_sku": "FG-T-0004", "share_pct": 100.0, "capacity_month": 100},
        {"plant_id": "P-02", "item_sku": "FG-T-0002", "share_pct": 100.0, "capacity_month": 100},
        {"plant_id": "P-02", "item_sku": "FG-T-0003", "share_pct": 100.0, "capacity_month": 100},
    ])
    ports = _df([
        {"code": "FRA", "name": "Frankfurt", "country_iso2": "DE", "type": "air"},
        {"code": "DEHAM", "name": "Hamburg", "country_iso2": "DE", "type": "sea"},
        {"code": "GRU", "name": "Guarulhos", "country_iso2": "BR", "type": "air"},
        {"code": "BRSSZ", "name": "Santos", "country_iso2": "BR", "type": "sea"},
    ])
    dcs = _df([{"id": "DC-SP1", "name": "DC Sao Paulo", "uf": "SP", "municipality": "Sao Paulo", "lat": -23.6,
                "lon": -46.6}])
    hospitals = _df([{"id": "H-0001", "name": "Test Hospital", "uf": "SP", "municipality": "Sao Paulo", "lat": -23.5,
                      "lon": -46.6, "type": "private", "size_index": 1.0}])

    def e(f, ft, t, tt, mode, lt, cost):
        return {"from_id": f, "from_type": ft, "to_id": t, "to_type": tt, "mode": mode, "lead_time_days": lt,
                "cost_per_unit": cost}

    ships_to = _df([
        e("P-01", "Plant", "FRA", "Port", "road", 1.0, 2.0), e("FRA", "Port", "GRU", "Port", "air", 3.0, 25.0),
        e("GRU", "Port", "DC-SP1", "DC", "road", 1.0, 4.0),
        e("P-01", "Plant", "DEHAM", "Port", "road", 1.0, 2.0), e("DEHAM", "Port", "BRSSZ", "Port", "sea", 25.0, 6.0),
        e("BRSSZ", "Port", "DC-SP1", "DC", "road", 2.0, 4.0),
        e("P-02", "Plant", "DC-SP1", "DC", "road", 1.0, 3.0),
    ])
    stocks = _df([
        {"dc_id": "DC-SP1", "item_sku": "FG-T-0001", "on_hand": 30, "avg_daily_demand": 1.0, "safety_stock": 14,
         "transit_days": 5.0},
        {"dc_id": "DC-SP1", "item_sku": "FG-T-0004", "on_hand": 200, "avg_daily_demand": 1.0, "safety_stock": 14,
         "transit_days": 5.0},
        {"dc_id": "DC-SP1", "item_sku": "FG-T-0002", "on_hand": 30, "avg_daily_demand": 1.0, "safety_stock": 14,
         "transit_days": 1.0},
        {"dc_id": "DC-SP1", "item_sku": "FG-T-0003", "on_hand": 30, "avg_daily_demand": 1.0, "safety_stock": 14,
         "transit_days": 1.0},
    ])
    serves = _df([{"dc_id": "DC-SP1", "hospital_id": "H-0001", "lead_time_days": 1.0, "cost_per_unit": 15.0,
                   "is_primary": True}])
    consumes = _df([{"hospital_id": "H-0001", "item_sku": f"FG-T-000{k}", "monthly_demand": 30,
                     "revenue_month": 30000.0} for k in (1, 2, 3, 4)])
    can_substitute = _df([{"from_sku": "FG-T-0001", "to_sku": "FG-T-0002", "requalification_days": 3}])
    lots = _df([
        {"lot_id": "RM-T-R1-L0001", "item_sku": "RM-T-R1", "qty": 100.0, "mfg_date": "2026-01-01",
         "expiry_date": "2036-01-01", "status": "released", "source_id": "S-T3-001"},
        {"lot_id": "CP-T2-A-L0001", "item_sku": "CP-T2-A", "qty": 50.0, "mfg_date": "2026-02-01",
         "expiry_date": "2034-02-01", "status": "released", "source_id": "S-T2-007"},
        {"lot_id": "CP-T1-A-L0001", "item_sku": "CP-T1-A", "qty": 20.0, "mfg_date": "2026-03-01",
         "expiry_date": "2034-03-01", "status": "released", "source_id": "S-T1-001"},
        {"lot_id": "FG-T-0001-L0001", "item_sku": "FG-T-0001", "qty": 8.0, "mfg_date": "2026-04-01",
         "expiry_date": "2031-04-01", "status": "released", "source_id": "P-01"},
        {"lot_id": "CP-T1-C-L0001", "item_sku": "CP-T1-C", "qty": 20.0, "mfg_date": "2026-02-15",
         "expiry_date": "2034-02-15", "status": "released", "source_id": "S-T1-005"},
        {"lot_id": "FG-T-0003-L0001", "item_sku": "FG-T-0003", "qty": 4.0, "mfg_date": "2026-03-15",
         "expiry_date": "2031-03-15", "status": "released", "source_id": "P-02"},
    ])
    derived_from = _df([
        {"child_lot_id": "CP-T2-A-L0001", "parent_lot_id": "RM-T-R1-L0001", "qty_used": 25.0},
        {"child_lot_id": "CP-T1-A-L0001", "parent_lot_id": "CP-T2-A-L0001", "qty_used": 40.0},
        {"child_lot_id": "FG-T-0001-L0001", "parent_lot_id": "CP-T1-A-L0001", "qty_used": 8.0},
        {"child_lot_id": "CP-T1-C-L0001", "parent_lot_id": "RM-T-R1-L0001", "qty_used": 6.0},
        {"child_lot_id": "FG-T-0003-L0001", "parent_lot_id": "CP-T1-C-L0001", "qty_used": 4.0},
    ])
    delivered_to = _df([
        {"lot_id": "FG-T-0001-L0001", "hospital_id": "H-0001", "date": "2026-05-01", "qty": 5},
        {"lot_id": "FG-T-0003-L0001", "hospital_id": "H-0001", "date": "2026-05-01", "qty": 4},
    ])
    return {
        "countries": countries, "ports": ports, "suppliers": suppliers, "items": items, "plants": plants, "dcs": dcs,
        "hospitals": hospitals, "lots": lots, "supplies": supplies, "buys_from": buys_from, "bom": bom,
        "manufactures": manufactures, "ships_to": ships_to, "stocks": stocks, "serves": serves, "consumes": consumes,
        "can_substitute": can_substitute, "derived_from": derived_from, "delivered_to": delivered_to,
    }
