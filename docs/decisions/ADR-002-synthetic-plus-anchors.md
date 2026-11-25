# ADR-002: Synthetic network with real open-data anchors

- Status: accepted
- Date: 2026-11-25

**Context.** Real multi-tier supplier maps are confidential; a public portfolio cannot use them.

**Decision.** Generate the network with a fixed seed from `config/network.yaml` and calibrate only what open data
can support: country weights (Brazil's 2024 imports of NCM 9021 by origin), implant NCM codes (Siscomex),
municipality population and coordinates (IBGE). Everything else is an explicit, documented assumption.

**Consequences.** Results illustrate the method, not the market. Every number in the README is labelled synthetic.
