"""Real open-data anchors used to calibrate the synthetic network.

Sources (all free, no key):
* Siscomex "Classif" public NCM table  -> validates the NCM codes used for implant SKUs.
* ComexStat API (MDIC)                -> Brazilian imports of NCM 9021.* by country of origin.
* UN Comtrade public preview API       -> same flow (reporter = Brazil) used as fallback when
                                          ComexStat is unavailable. Brazil's own customs data is
                                          what Brazil reports to UN Comtrade.
* IBGE SIDRA (table 4709, Censo 2022) + IBGE Malhas v3 metadata -> population and centroid of
  municipalities, used to place DCs and hospitals.

Every fetch writes a versioned CSV in data/reference/ plus an entry in sources.json with the
extraction timestamp and status, so the generator never needs the network to run.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from supplygraph.config import REFERENCE_DIR

UA = {"User-Agent": "supplygraph-opme/0.1 (open-data research client)"}
NCM_URL = "https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json?perfil=PUBLICO"
COMEXSTAT_URL = "https://api-comexstat.mdic.gov.br/general?language=en"
COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
SIDRA_POP_URL = "https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022/f/c"
IBGE_MUN_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
IBGE_META_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{id}/metadados"

OPME_HS6 = ["902110", "902131", "902139", "902190"]
OPME_NCM_PREFIXES = ("9021.10", "9021.31", "9021.39", "9021.90")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sources_path() -> Path:
    return REFERENCE_DIR / "sources.json"


def _record(key: str, entry: dict) -> None:
    path = _sources_path()
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[key] = entry
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------- NCM (Siscomex)
def fetch_ncm() -> pd.DataFrame:
    r = requests.get(NCM_URL, headers=UA, timeout=120)
    r.raise_for_status()
    payload = r.json()
    rows = [
        {
            "ncm": n["Codigo"],
            "description_pt": n["Descricao"].replace("<i>", "").replace("</i>", ""),
            "valid_from": n["Data_Inicio"],
            "valid_to": n["Data_Fim"],
        }
        for n in payload["Nomenclaturas"]
        if n["Codigo"].startswith("9021")
    ]
    df = pd.DataFrame(rows)
    out = REFERENCE_DIR / "ncm_9021_siscomex.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    _record(
        "ncm",
        {
            "source": "Siscomex Portal Unico - Classif (Receita Federal), public NCM table",
            "url": NCM_URL,
            "extracted_at": _now(),
            "status": "ok",
            "version": f"{payload.get('Data_Ultima_Atualizacao_NCM')} / {payload.get('Ato')}",
            "rows": len(df),
            "file": out.name,
        },
    )
    return df


# ------------------------------------------------------------------- imports by origin country
def _try_comexstat(year: int) -> pd.DataFrame | None:
    body = {
        "flow": "import",
        "monthDetail": False,
        "period": {"from": f"{year}-01", "to": f"{year}-12"},
        "filters": [{"filter": "heading", "values": ["9021"]}],
        "details": ["country", "ncm"],
        "metrics": ["metricFOB", "metricKG", "metricCIF"],
    }
    try:
        r = requests.post(COMEXSTAT_URL, json=body, headers=UA, timeout=60)
        if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            return None
        rows = r.json().get("data", {}).get("list", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["year"] = year
        df["source"] = "ComexStat"
        return df
    except (requests.RequestException, ValueError):
        return None


def _comtrade(year: int) -> pd.DataFrame:
    frames = []
    for hs in OPME_HS6:
        params = {
            "reporterCode": 76,
            "period": year,
            "flowCode": "M",
            "cmdCode": hs,
            "customsCode": "C00",
            "motCode": 0,
            "partner2Code": 0,
            "includeDesc": "true",
        }
        for attempt in range(5):
            r = requests.get(COMTRADE_URL, params=params, headers=UA, timeout=60)
            if r.status_code == 429:
                time.sleep(3 + attempt * 2)
                continue
            r.raise_for_status()
            break
        data = r.json().get("data", [])
        frames.append(pd.DataFrame(data))
        time.sleep(2.5)  # public preview endpoint is rate limited
    df = pd.concat(frames, ignore_index=True)
    keep = df[df["partnerCode"] != 0]
    out = keep[
        ["refYear", "cmdCode", "cmdDesc", "partnerISO", "partnerDesc", "cifvalue", "fobvalue", "netWgt"]
    ].rename(
        columns={
            "refYear": "year",
            "cmdCode": "hs6",
            "cmdDesc": "hs6_desc",
            "partnerISO": "partner_iso3",
            "partnerDesc": "partner_name",
            "cifvalue": "cif_usd",
            "fobvalue": "fob_usd",
            "netWgt": "net_kg",
        }
    )
    out["source"] = "UN Comtrade (reporter: Brazil)"
    return out


def fetch_imports(year: int) -> pd.DataFrame:
    """ComexStat first; UN Comtrade (Brazil as reporter) when ComexStat is down."""
    out_path = REFERENCE_DIR / f"br_imports_9021_by_origin_{year}.csv"
    cs = _try_comexstat(year)
    if cs is not None:
        cs.to_csv(out_path, index=False, encoding="utf-8")
        _record(
            "imports",
            {
                "source": "ComexStat (MDIC)",
                "url": COMEXSTAT_URL,
                "extracted_at": _now(),
                "status": "ok",
                "year": year,
                "file": out_path.name,
            },
        )
        return cs
    df = _comtrade(year)
    df.to_csv(out_path, index=False, encoding="utf-8")
    _record(
        "imports",
        {
            "source": "UN Comtrade public preview API, reporter=Brazil (76), flow=M, HS6 902110/902131/902139/902190",
            "url": COMTRADE_URL,
            "extracted_at": _now(),
            "status": "fallback: ComexStat API unavailable (HTTP 503) and ComexStat bulk files served an expired TLS "
            "certificate at extraction time",
            "year": year,
            "rows": len(df),
            "file": out_path.name,
        },
    )
    return df


# ---------------------------------------------------------------------------------- IBGE
def fetch_ibge(n_top: int = 1500) -> pd.DataFrame:
    pop = requests.get(SIDRA_POP_URL, headers=UA, timeout=180).json()[1:]
    pop_df = pd.DataFrame(
        {"ibge_code": [int(p["D1C"]) for p in pop], "population_2022": [p["V"] for p in pop]}
    )
    pop_df["population_2022"] = pd.to_numeric(pop_df["population_2022"], errors="coerce")
    mun = requests.get(IBGE_MUN_URL, headers=UA, timeout=120).json()
    mun_df = pd.DataFrame(
        {
            "ibge_code": [m["id"] for m in mun],
            "municipality": [m["nome"] for m in mun],
            "uf": [
                ((m.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF", {}).get("sigla")
                or ((m.get("regiao-imediata") or {}).get("regiao-intermediaria") or {})
                .get("UF", {})
                .get("sigla")
                for m in mun
            ],
        }
    )
    df = mun_df.merge(pop_df, on="ibge_code").sort_values("population_2022", ascending=False).head(n_top)

    def centroid(code: int) -> tuple[int, float | None, float | None]:
        for attempt in range(4):
            try:
                r = requests.get(IBGE_META_URL.format(id=code), headers=UA, timeout=30)
                c = r.json()[0]["centroide"]
                return code, c["latitude"], c["longitude"]
            except (requests.RequestException, ValueError, KeyError, IndexError):
                time.sleep(1 + attempt)
        return code, None, None

    with ThreadPoolExecutor(max_workers=8) as ex:
        cents = list(ex.map(centroid, df["ibge_code"].tolist()))
    cdf = pd.DataFrame(cents, columns=["ibge_code", "lat", "lon"])
    df = df.merge(cdf, on="ibge_code").dropna(subset=["lat", "lon"]).reset_index(drop=True)
    out = REFERENCE_DIR / "ibge_municipalities_top.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    _record(
        "ibge",
        {
            "source": "IBGE - SIDRA table 4709 (Censo 2022 resident population) + Localidades API + Malhas v3 "
            "metadata (municipality centroid)",
            "url": f"{SIDRA_POP_URL} ; {IBGE_MUN_URL} ; {IBGE_META_URL}",
            "extracted_at": _now(),
            "status": "ok",
            "rows": len(df),
            "file": out.name,
        },
    )
    return df


def fetch_all(year: int, n_municipalities: int = 1500) -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    fetch_ncm()
    fetch_imports(year)
    fetch_ibge(n_municipalities)


# ------------------------------------------------------------------------------ readers
def read_ncm() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "ncm_9021_siscomex.csv", dtype=str)


def read_imports(year: int) -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / f"br_imports_9021_by_origin_{year}.csv")


def read_municipalities() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "ibge_municipalities_top.csv")


def validate_ncm_codes(codes: list[str]) -> dict[str, bool]:
    """Return {code: is_valid} against the official Siscomex table (codes like 9021.31.10)."""
    valid = set(read_ncm()["ncm"])
    return {c: c in valid for c in codes}
