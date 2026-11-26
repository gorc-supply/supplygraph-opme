"""Keep the AuraDB Free instance active: one cheap read query, run by .github/workflows/aura-keepalive.yml.

AuraDB Free pauses after 72 hours without activity and DELETES an instance that stays paused for more
than 30 days (Neo4j docs, "Instance actions"). A paused instance refuses connections, so this job must run
more often than every 72 h; if it ever fails, the GitHub failure e-mail is the alarm to resume the instance
in the console before the 30 days run out.

Reads AURA_URI / AURA_USER / AURA_PASSWORD / AURA_DATABASE from the environment (GitHub secrets) and
connects through supplygraph.db.get_driver (TLS always verified, ADR-014). Never prints credentials.
"""

from __future__ import annotations

import sys

from neo4j.exceptions import AuthError, ServiceUnavailable

from supplygraph.config import neo4j_settings
from supplygraph.db import get_driver, run

CONSOLE = "https://console.neo4j.io"


def main() -> int:
    try:
        settings = neo4j_settings("aura")
    except RuntimeError as e:  # secrets missing
        print(f"::error::{e}")
        return 2
    try:
        with get_driver(settings) as d:
            d.verify_connectivity()
            # count-store lookups: answered from metadata, effectively free
            nodes = run(d, "MATCH (n) RETURN count(n) AS c", timeout=60)[0]["c"]
            rels = run(d, "MATCH ()-[r]->() RETURN count(r) AS c", timeout=60)[0]["c"]
    except AuthError:
        print("::error::AuraDB rejected the credentials - check the AURA_USER / AURA_PASSWORD secrets.")
        return 1
    except ServiceUnavailable:
        print("::error::AuraDB did not answer. A Free instance pauses after 72 h without activity and is deleted "
              f"after 30 days paused: resume it now at {CONSOLE}.")
        return 1
    print(f"AuraDB OK: {nodes:,} nodes, {rels:,} relationships")
    if nodes == 0:
        print("::warning::The instance is reachable but empty - run `uv run sgraph export-aura` to restore the demo data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
