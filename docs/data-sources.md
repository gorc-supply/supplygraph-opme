# Data sources

**Rule of the project:** the network is synthetic. Real open data is used only to *calibrate* it, and every place
where a real number enters is listed here. Extraction metadata is versioned in
[`data/reference/sources.json`](../data/reference/sources.json). Refresh with `sgraph fetch-anchors`.

| Source | What was used | URL | Extracted | Licence / terms | File |
|---|---|---|---|---|---|
| **Siscomex Portal Único - Classif** (Receita Federal) | Official NCM table, chapter 90.21, to validate the implant codes (9021.10, 9021.31, 9021.39, 9021.90 and their 8-digit items) | `portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json` | 2026-11-25 (table "vigente em 25/11/2026", Resolução Gecex nº 926/2026) | Brazilian federal open data | `ncm_9021_siscomex.csv` |
| **UN Comtrade** public preview API, reporter = Brazil | 2024 imports of HS 902110, 902131, 902139, 902190 by partner country (CIF/FOB US$, kg). Used to weight the country of plants and tier-1 suppliers. Total CIF 2024: US$ 693.5 M; top origins: USA 28.5%, Germany 13.1%, Ireland 10.2%, Mexico 9.9%, Switzerland 6.7% | `comtradeapi.un.org/public/v1/preview/C/A/HS` | 2026-11-25 | UN Comtrade terms of use (free preview endpoint) | `br_imports_9021_by_origin_2024.csv` |
| **IBGE** - SIDRA table 4709 (Censo 2022), Localidades API, Malhas v3 metadata | Resident population 2022, UF and centroid (lat/lon) of the 1,500 most populous municipalities. Used to place DCs (largest municipality of each configured UF) and to draw hospital locations proportional to population | `apisidra.ibge.gov.br/values/t/4709/...`, `servicodados.ibge.gov.br/api/v1/localidades/municipios`, `servicodados.ibge.gov.br/api/v3/malhas/municipios/{id}/metadados` | 2026-11-25 | IBGE open data | `ibge_municipalities_top.csv` |

## ComexStat (MDIC) - preferred source, unavailable at extraction time

The brief asked for ComexStat. On 2026-11-25 the ComexStat API (`api-comexstat.mdic.gov.br`) answered **HTTP 503**
and the bulk download site (`balanca.economia.gov.br`) served an **expired TLS certificate**; the project does not
disable certificate verification. The fetcher (`supplygraph.generate.anchors.fetch_imports`) tries ComexStat first
and falls back to UN Comtrade, where the reporter is Brazil (the same customs flow as Brazil reports it). Re-run
`sgraph fetch-anchors` when ComexStat is back; the CSV will be replaced and `sources.json` updated.
See [ADR-007](decisions/ADR-007-comtrade-fallback.md).

## Everything else is synthetic

Supplier names (`Synth ... 007 (DE)`), hospital names (`Synthetic Hospital 0001 (city/UF)`), prices in R$, demand,
inventory, lead times, shares, `financial_risk`, `geo_risk_score` (a distance-to-Brazil proxy plus noise, **not** a
geopolitical assessment), lots and genealogy are generated from [`config/network.yaml`](../config/network.yaml)
with seed 42. Country mixes for tier-2 and tier-3 are explicit assumptions in that file.

Port and airport codes (IATA, UN/LOCODE) and country names are public identifiers.
