# Public demo: AuraDB Free + Streamlit Community Cloud

Both services are free and need no credit card. The app never runs GDS: every algorithm result is already
written in the graph (see [ADR-009](decisions/ADR-009-precompute-gds.md)).

## 1. AuraDB Free (about 5 minutes)

1. Sign in at <https://console.neo4j.io> and create an instance of type **AuraDB Free**.
2. Download the credentials file shown once at creation (URI `neo4j+s://xxxxxxxx.databases.neo4j.io`, user, password).
3. Fill `.env` (never committed):
   ```
   AURA_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
   AURA_USER=neo4j
   AURA_PASSWORD=...
   ```
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
   user = "neo4j"
   password = "..."
   database = "neo4j"
   ```
4. Deploy. Dependencies come from `requirements.txt` (the package itself with the `app` extra).

## Notes

- AuraDB Free pauses after a period of inactivity. The app shows a friendly message when the connection fails;
  resume the instance in the Aura console.
- Queries in the app are parameterised, cached for 10 minutes (`st.cache_data`) and time out after 30 s.
- To refresh the demo after changing the generator or the scoring weights: re-run locally, then `export-aura`.
