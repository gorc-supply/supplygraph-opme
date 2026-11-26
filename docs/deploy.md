# Public demo: AuraDB Free + Streamlit Community Cloud

Live at **https://supplygraph-opme.streamlit.app** (`?lang=en` for English).

Both services are free and need no credit card. The app never runs GDS: every algorithm result is already
written in the graph (see [ADR-009](decisions/ADR-009-precompute-gds.md)).

## 1. AuraDB Free (about 5 minutes)

1. Sign in at <https://console.neo4j.io> and create an instance of type **AuraDB Free**.
2. Download the credentials file shown once at creation (URI `neo4j+s://xxxxxxxx.databases.neo4j.io`, user, password).
3. Fill `.env` (never committed):
   ```
   AURA_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
   AURA_USER=xxxxxxxx              # new instances use the instance id as user...
   AURA_PASSWORD=...
   AURA_DATABASE=xxxxxxxx          # ...and as database name
   ```
   TLS is verified with the OS trust store plus certifi ([ADR-014](decisions/ADR-014-tls-certifi.md)); if the
   connection fails with a certificate error, update the package (`uv sync`), never disable verification.
4. With the local graph loaded and analysed (`sgraph all` or `sgraph load` + `sgraph analyze`):
   ```powershell
   uv run sgraph export-aura --dry-run   # checks the 200k nodes / 400k relationships limits
   uv run sgraph export-aura             # copies nodes, relationships and GDS properties (~5-10 min)
   ```

## 2. Streamlit Community Cloud (about 5 minutes)

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns the repository.
2. **Create app** -> repository `gorc-supply/supplygraph-opme`, branch `main`, main file `app/streamlit_app.py`.
3. **Advanced settings -> Secrets**, paste (values from the Aura credentials file):
   ```toml
   [neo4j]
   uri = "neo4j+s://xxxxxxxx.databases.neo4j.io"
   user = "xxxxxxxx"
   password = "..."
   database = "xxxxxxxx"
   ```
4. Deploy. Dependencies come from **`app/requirements.txt`**: Community Cloud looks in the entrypoint's folder
   first and only then in the repository root, where `uv.lock` would win and install the whole pipeline (GDS client,
   DuckDB, matplotlib) without the app libraries. The app file lists only what the app imports; the local
   `supplygraph` package is read from `src/` (see `app/common.py`).

## Notes

- To run the app on your machine against Aura (same data as the public demo):
  `$env:SGRAPH_APP_TARGET="aura"; uv run streamlit run app/streamlit_app.py` (uses the `AURA_*` values in `.env`).
- AuraDB Free pauses after a period of inactivity. The app shows a friendly message when the connection fails;
  resume the instance in the Aura console.
- Queries in the app are parameterised, cached for 10 minutes (`st.cache_data`) and time out after 30 s.
- To refresh the demo after changing the generator or the scoring weights: re-run locally, then `export-aura`.

## 3. Keep the AuraDB Free instance alive

AuraDB Free pauses after **72 hours** without activity and **deletes** an instance that stays paused for more
than **30 days** (Neo4j docs, *Instance actions*); a paused instance refuses connections. The workflow
[`.github/workflows/aura-keepalive.yml`](../.github/workflows/aura-keepalive.yml) runs one cheap read query
(`scripts/aura_keepalive.py`) **every 2 days** (a weekly run would always find the instance already paused).
If it fails, GitHub e-mails you: resume the instance at <https://console.neo4j.io> within 30 days.

Repository secrets (Settings -> Secrets and variables -> Actions -> New repository secret), values from the Aura
credentials file / your `.env`: `AURA_URI`, `AURA_USER`, `AURA_PASSWORD`, `AURA_DATABASE`.
Test it once with `gh workflow run aura-keepalive.yml` and `gh run watch`.

Caveats: the Neo4j docs do not define exactly what counts as "activity" (a query is the reasonable reading,
confirm in the console after a few days); GitHub disables scheduled workflows in public repositories after
60 days without repository activity (re-enable them in the Actions tab).
