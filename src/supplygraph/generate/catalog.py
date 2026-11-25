"""Static catalogs used by the generator.

Facts here are public identifiers only (country codes and names, approximate capital coordinates,
IATA airport codes, UN/LOCODE seaport codes, official NCM codes validated against Siscomex).
Everything numeric that describes the *business* (prices, risk, demand) is a synthetic assumption.
"""

from __future__ import annotations

# iso2, iso3, name, region, approx. capital lat, lon
COUNTRIES: list[tuple[str, str, str, str, float, float]] = [
    ("BR", "BRA", "Brazil", "South America", -15.79, -47.88),
    ("AR", "ARG", "Argentina", "South America", -34.60, -58.38),
    ("US", "USA", "United States", "North America", 38.90, -77.04),
    ("MX", "MEX", "Mexico", "North America", 19.43, -99.13),
    ("CA", "CAN", "Canada", "North America", 45.42, -75.70),
    ("CR", "CRI", "Costa Rica", "Central America", 9.93, -84.08),
    ("DE", "DEU", "Germany", "Europe", 52.52, 13.40),
    ("IE", "IRL", "Ireland", "Europe", 53.35, -6.26),
    ("CH", "CHE", "Switzerland", "Europe", 46.95, 7.45),
    ("FR", "FRA", "France", "Europe", 48.86, 2.35),
    ("DK", "DNK", "Denmark", "Europe", 55.68, 12.57),
    ("IT", "ITA", "Italy", "Europe", 41.90, 12.50),
    ("GB", "GBR", "United Kingdom", "Europe", 51.51, -0.13),
    ("ES", "ESP", "Spain", "Europe", 40.42, -3.70),
    ("NL", "NLD", "Netherlands", "Europe", 52.37, 4.90),
    ("BE", "BEL", "Belgium", "Europe", 50.85, 4.35),
    ("SE", "SWE", "Sweden", "Europe", 59.33, 18.07),
    ("PT", "PRT", "Portugal", "Europe", 38.72, -9.14),
    ("IL", "ISR", "Israel", "Middle East", 31.77, 35.21),
    ("CN", "CHN", "China", "Asia", 39.90, 116.40),
    ("IN", "IND", "India", "Asia", 28.61, 77.21),
    ("KR", "KOR", "South Korea", "Asia", 37.57, 126.98),
    ("JP", "JPN", "Japan", "Asia", 35.68, 139.69),
    ("TH", "THA", "Thailand", "Asia", 13.76, 100.50),
    ("MY", "MYS", "Malaysia", "Asia", 3.14, 101.69),
    ("SG", "SGP", "Singapore", "Asia", 1.35, 103.82),
]

# Origin gateways per country: (code, name, type). IATA for airports, UN/LOCODE for seaports.
PORTS: dict[str, list[tuple[str, str, str]]] = {
    "US": [
        ("MEM", "Memphis Intl. Airport", "air"),
        ("MIA", "Miami Intl. Airport", "air"),
        ("USSAV", "Port of Savannah", "sea"),
    ],
    "MX": [("MEX", "Mexico City Intl. Airport", "air"), ("MXZLO", "Port of Manzanillo", "sea")],
    "CA": [("YYZ", "Toronto Pearson Airport", "air")],
    "CR": [("SJO", "San Jose Juan Santamaria Airport", "air")],
    "AR": [("EZE", "Buenos Aires Ezeiza Airport", "air"), ("ARBUE", "Port of Buenos Aires", "sea")],
    "DE": [("FRA", "Frankfurt Airport", "air"), ("DEHAM", "Port of Hamburg", "sea")],
    "IE": [("DUB", "Dublin Airport", "air")],
    "CH": [("ZRH", "Zurich Airport", "air")],
    "FR": [("CDG", "Paris Charles de Gaulle Airport", "air"), ("FRLEH", "Port of Le Havre", "sea")],
    "DK": [("CPH", "Copenhagen Airport", "air")],
    "IT": [("MXP", "Milan Malpensa Airport", "air"), ("ITGOA", "Port of Genoa", "sea")],
    "GB": [("LHR", "London Heathrow Airport", "air"), ("GBFXT", "Port of Felixstowe", "sea")],
    "ES": [("MAD", "Madrid Barajas Airport", "air"), ("ESVLC", "Port of Valencia", "sea")],
    "NL": [("AMS", "Amsterdam Schiphol Airport", "air"), ("NLRTM", "Port of Rotterdam", "sea")],
    "BE": [("BRU", "Brussels Airport", "air"), ("BEANR", "Port of Antwerp", "sea")],
    "SE": [("ARN", "Stockholm Arlanda Airport", "air")],
    "PT": [("LIS", "Lisbon Airport", "air")],
    "IL": [("TLV", "Tel Aviv Ben Gurion Airport", "air")],
    "CN": [("PVG", "Shanghai Pudong Airport", "air"), ("CNSHA", "Port of Shanghai", "sea")],
    "IN": [("BOM", "Mumbai Airport", "air"), ("INNSA", "Port of Nhava Sheva", "sea")],
    "KR": [("ICN", "Seoul Incheon Airport", "air"), ("KRPUS", "Port of Busan", "sea")],
    "JP": [("NRT", "Tokyo Narita Airport", "air"), ("JPTYO", "Port of Tokyo", "sea")],
    "TH": [("BKK", "Bangkok Suvarnabhumi Airport", "air")],
    "MY": [("KUL", "Kuala Lumpur Airport", "air")],
    "SG": [("SIN", "Singapore Changi Airport", "air"), ("SGSIN", "Port of Singapore", "sea")],
}

# Brazilian entry gateways: code, name, type, approx lat, lon
BR_PORTS: list[tuple[str, str, str, float, float]] = [
    ("GRU", "Sao Paulo Guarulhos Airport", "air", -23.43, -46.47),
    ("VCP", "Campinas Viracopos Airport", "air", -23.01, -47.13),
    ("GIG", "Rio de Janeiro Galeao Airport", "air", -22.81, -43.25),
    ("BRSSZ", "Port of Santos", "sea", -23.96, -46.33),
    ("BRPNG", "Port of Paranagua", "sea", -25.50, -48.52),
    ("BRITJ", "Port of Itajai", "sea", -26.90, -48.66),
    ("BRSUA", "Port of Suape", "sea", -8.39, -34.96),
]

# Raw materials: code -> (name, unit cost per kg in BRL [synthetic], family)
RAW_MATERIALS: dict[str, tuple[str, float, str]] = {
    "TI64": ("Titanium alloy Ti-6Al-4V ELI bar (ASTM F136)", 95.0, "ORTHO"),
    "CPTI": ("Commercially pure titanium grade 4 bar", 70.0, "ORTHO"),
    "COCR": ("Cobalt-chromium-molybdenum alloy bar (ASTM F1537)", 120.0, "ORTHO"),
    "SS316": ("Stainless steel 316LVM bar (ASTM F138)", 25.0, "ORTHO"),
    "UHMWPE": ("UHMWPE resin, implant grade (ASTM F648)", 60.0, "ORTHO"),
    "PEEK": ("PEEK polymer, implant grade", 900.0, "ORTHO"),
    "HA": ("Hydroxyapatite powder for plasma coating", 300.0, "ORTHO"),
    "PMMA": ("PMMA bone-cement powder", 150.0, "ORTHO"),
    "L605": ("Cobalt-chromium L605 micro-tube", 4000.0, "CARDIO"),
    "NITI": ("Nitinol (NiTi) tube and wire", 3500.0, "CARDIO"),
    "PTIR": ("Platinum-iridium radiopaque marker wire", 30000.0, "CARDIO"),
    "PLGA": ("Biodegradable drug-carrier polymer (PLGA)", 8000.0, "CARDIO"),
    "LIMUS": ("Antiproliferative drug substance (limus class)", 50000.0, "CARDIO"),
    "PYC": ("Pyrolytic carbon", 2500.0, "CARDIO"),
    "BOVPER": ("Bovine pericardium tissue", 1500.0, "CARDIO"),
    "PET": ("Medical-grade PET polyester yarn", 200.0, "CARDIO"),
    "EPTFE": ("Expanded PTFE membrane", 2200.0, "CARDIO"),
    "SIL": ("Implant-grade silicone", 180.0, "CARDIO"),
}

# Implant categories. NCM codes validated against the Siscomex table (data/reference/ncm_9021_siscomex.csv).
CATEGORIES: dict[str, dict] = {
    "HIP": {
        "family": "ORTHO",
        "ncm": ["9021.31.10", "9021.31.90"],
        "anvisa": "III",
        "templates": [
            "Cementless femoral stem",
            "Cemented femoral stem",
            "Acetabular cup",
            "CoCr femoral head",
            "UHMWPE acetabular liner",
            "Bipolar head",
        ],
        "raw": ["TI64", "COCR", "UHMWPE", "HA", "PMMA"],
        "price": (6000, 18000),
        "demand": 1.6,
        "weight": 0.17,
    },
    "KNEE": {
        "family": "ORTHO",
        "ncm": ["9021.31.90"],
        "anvisa": "III",
        "templates": [
            "Femoral component",
            "Tibial baseplate",
            "Tibial insert",
            "Patellar component",
            "Revision stem extension",
        ],
        "raw": ["COCR", "TI64", "UHMWPE", "PMMA"],
        "price": (7000, 20000),
        "demand": 1.4,
        "weight": 0.15,
    },
    "SPINE": {
        "family": "ORTHO",
        "ncm": ["9021.10.10"],
        "anvisa": "III",
        "templates": [
            "PEEK interbody cage",
            "Polyaxial pedicle screw",
            "Spinal rod",
            "Anterior cervical plate",
            "Set screw",
        ],
        "raw": ["PEEK", "TI64", "CPTI", "COCR"],
        "price": (1500, 12000),
        "demand": 2.2,
        "weight": 0.14,
    },
    "TRAUMA": {
        "family": "ORTHO",
        "ncm": ["9021.10.20"],
        "anvisa": "III",
        "templates": [
            "Locking compression plate",
            "Cortical screw",
            "Intramedullary nail",
            "Cannulated screw",
            "External fixator pin",
        ],
        "raw": ["TI64", "SS316", "CPTI"],
        "price": (400, 6000),
        "demand": 4.0,
        "weight": 0.16,
    },
    "STENT": {
        "family": "CARDIO",
        "ncm": ["9021.90.12"],
        "anvisa": "IV",
        "templates": [
            "Drug-eluting coronary stent",
            "Bare-metal coronary stent",
            "Peripheral self-expanding stent",
        ],
        "raw": ["L605", "NITI", "PTIR", "PLGA", "LIMUS"],
        "price": (3000, 9000),
        "demand": 2.5,
        "weight": 0.16,
    },
    "VALVE": {
        "family": "CARDIO",
        "ncm": ["9021.39.11", "9021.39.19"],
        "anvisa": "IV",
        "templates": [
            "Mechanical heart valve",
            "Bovine pericardial valve",
            "Annuloplasty ring",
            "Transcatheter valve system",
        ],
        "raw": ["PYC", "TI64", "BOVPER", "PET", "NITI", "COCR"],
        "price": (15000, 60000),
        "demand": 0.6,
        "weight": 0.11,
    },
    "VASCULAR": {
        "family": "CARDIO",
        "ncm": ["9021.39.30", "9021.90.13"],
        "anvisa": "IV",
        "templates": ["Knitted vascular graft", "Endovascular stent-graft", "Septal occluder"],
        "raw": ["PET", "EPTFE", "NITI", "SIL"],
        "price": (8000, 40000),
        "demand": 0.8,
        "weight": 0.11,
    },
}

L1_DESCRIPTORS = [
    "machined body",
    "coated body",
    "articulating insert",
    "locking assembly",
    "frame",
    "delivery system",
    "leaflet set",
    "sterile barrier pack",
    "polished bearing",
    "porous shell",
]
DEEP_DESCRIPTORS = [
    "near-net forging",
    "precision blank",
    "sub-assembly",
    "laser-cut tube",
    "surface-treated part",
    "polymer moulding",
    "coating feedstock",
    "wire sub-assembly",
    "heat-treated bar",
    "cut-to-length stock",
]
COMMON_DEEP = {
    "ORTHO": [
        "Ti64 forged blank",
        "Ti64 bar cut-to-length",
        "CoCr investment casting",
        "HA plasma-spray feedstock",
        "UHMWPE compression-moulded block",
    ],
    "CARDIO": ["NiTi laser-cut tube", "L605 drawn tube", "PET woven fabric", "Pt-Ir marker band"],
}

SUPPLIER_WORDS = {
    1: ["Precision Implants", "Medical Machining", "Ortho Components", "Cardio Components", "Surgical Parts"],
    2: ["Forge Works", "Alloy Processing", "Coating Services", "Tube Drawing", "Polymer Moulding"],
    3: ["Titanium Mill", "Specialty Alloys", "Biomaterials", "Medical Polymers", "Tissue Processing"],
}
