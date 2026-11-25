# ADR-006: Portable Neo4j when Docker Desktop is not installed

- Status: accepted
- Date: 2026-11-25

**Context.** The build machine had no Docker installed. The brief says not to block on things that depend on the
owner.

**Decision.** Keep `docker-compose.yml` as the primary path and add `sgraph setup-portable`: it downloads Eclipse
Temurin JDK 21 and the Neo4j Community 2026.10.2 zip (SHA-256 verified) plus the APOC and GDS jars into `.runtime/`
(git-ignored). `sgraph up` / `sgraph down` use Docker when available, otherwise the portable install.

**Consequences.** Everything in this repo was executed on the portable instance. The Docker path is exercised by CI
(Neo4j service container) but was not run locally. Installing Docker Desktop is a pending item.
