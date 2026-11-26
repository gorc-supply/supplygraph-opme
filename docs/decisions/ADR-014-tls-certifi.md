# ADR-014: Verified TLS with the OS trust store plus certifi, in one connection helper

- Status: accepted
- Date: 2026-11-25

**Context.** The first `sgraph export-aura` on the build machine (Windows 11) failed to connect to AuraDB Free with
`ServiceUnavailable`. The real cause was the TLS handshake: `self-signed certificate in certificate chain`.
Inspection showed the certificate is the legitimate one (`*.databases.neo4j.io`, issued by SSL.com TLS Issuing RSA
CA R1, valid until 2027-05), so there was no interception: the SSL.com root simply is not in the certificate store
Python reads on that Windows installation. The same handshake verified fine against certifi's Mozilla CA bundle.

**Decision.**
- `supplygraph.db.get_driver` is the single place where drivers are created; the CLI, the loader, `export-aura`
  and the Streamlit app all use it.
- For `neo4j+s://` and `bolt+s://` URIs the helper switches to the plain scheme and passes its own `ssl_context`
  (the driver only accepts `ssl_context` with plain schemes). The context is `ssl.create_default_context()`
  (OS roots, `CERT_REQUIRED`, hostname check) **plus** `certifi.where()`. Certificate and hostname verification are
  always on; the helper raises if a context ever is not verifying, and refuses `+ssc` URIs (which accept any
  certificate).
- `certifi` is a declared dependency, so Linux (CI, Streamlit Cloud) gets the same bundle; plain `neo4j://` for the
  local database is unchanged.
- The helper also remembers each driver's database, because a new AuraDB instance's database is named after the
  instance id (not `neo4j`): set `AURA_DATABASE` / the `database` secret accordingly.

**Rejected.** Disabling verification or using `+ssc` (insecure); asking every user to install the SSL.com root in
Windows (works for this machine only); an `SSL_CERT_FILE` environment variable (easy to forget, not visible in code).

**Consequences.** Covered by `tests/test_tls.py` (no network, runs in CI). Running the app locally against Aura:
set `SGRAPH_APP_TARGET=aura` (uses `AURA_*` from `.env`) or create `.streamlit/secrets.toml`.
