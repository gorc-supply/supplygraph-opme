"""Shared fixtures. Tests marked `neo4j` need a running Neo4j and WIPE the configured database,
so they only run when SGRAPH_TEST_ALLOW_RESET=1 (set in CI; set it locally on purpose)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def _neo4j_ok() -> tuple[bool, str]:
    if os.getenv("SGRAPH_TEST_ALLOW_RESET") != "1":
        return False, "set SGRAPH_TEST_ALLOW_RESET=1 to run tests that wipe the Neo4j database"
    try:
        from supplygraph.db import get_driver

        d = get_driver()
        d.verify_connectivity()
        d.close()
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"Neo4j not reachable: {e}"


def pytest_collection_modifyitems(config, items):
    ok, why = _neo4j_ok()
    if ok:
        return
    skip = pytest.mark.skip(reason=why)
    for it in items:
        if "neo4j" in it.keywords:
            it.add_marker(skip)


@pytest.fixture(scope="session")
def driver():
    from supplygraph.db import get_driver

    d = get_driver()
    yield d
    d.close()
