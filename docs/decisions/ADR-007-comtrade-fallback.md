# ADR-007: UN Comtrade (reporter Brazil) as fallback for ComexStat

- Status: accepted
- Date: 2026-11-25

**Context.** On 2026-11-25 the ComexStat API returned HTTP 503 and its bulk files were served with an expired TLS
certificate. Disabling certificate checks is not acceptable.

**Decision.** `fetch_imports` tries ComexStat first; on failure it uses the UN Comtrade public preview API with
Brazil as reporter for HS 902110/902131/902139/902190, year 2024, and records the fallback in `sources.json`.

**Consequences.** HS6 granularity (not NCM 8 digits) for the country weights. The NCM codes themselves are still
validated against the official Siscomex table.
