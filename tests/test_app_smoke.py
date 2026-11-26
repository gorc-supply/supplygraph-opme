"""Smoke test: every Streamlit page renders without exceptions against the loaded + analysed graph.
Needs Neo4j with the `full` (or `ci`) network loaded; run after `sgraph all`. Does NOT wipe the database."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = ["overview.py", "explorer.py", "simulator.py", "recall.py", "ranking.py", "about.py"]


def _db_has_data() -> bool:
    if os.getenv("SGRAPH_APP_SMOKE") != "1":
        return False
    try:
        from supplygraph.db import get_driver, run

        d = get_driver()
        n = run(d, "MATCH (s:Supplier) WHERE s.criticality_index IS NOT NULL RETURN count(s) AS n")[0]["n"]
        d.close()
        return n > 0
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _db_has_data(), reason="set SGRAPH_APP_SMOKE=1 with an analysed graph loaded")
@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("lang", ["pt", "en"])
def test_page_renders(page, lang):
    import sys

    from streamlit.testing.v1 import AppTest

    if str(APP) not in sys.path:  # streamlit puts the main script dir (app/) on sys.path
        sys.path.insert(0, str(APP))
    at = AppTest.from_file(str(APP / "views" / page), default_timeout=120)
    at.session_state["lang"] = lang
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    # Every Markdown-rendered string must escape "$" (a pair of "R$" becomes a LaTeX formula otherwise).
    unescaped = [s for s in _markdown_texts(at) if re.search(r"(?<!\\)\$", s)]
    assert not unescaped, unescaped
    if page == "overview.py":  # thousands separator follows the language (60.560 / 60,560)
        nodes = next(m.value for m in at.metric if m.label in ("Nós", "Nodes"))
        assert re.fullmatch(r"\d{1,3}(\.\d{3})+" if lang == "pt" else r"\d{1,3}(,\d{3})+", nodes), nodes


def _markdown_texts(at) -> list[str]:
    out: list = []
    for coll in (at.title, at.header, at.subheader, at.caption, at.markdown, at.info, at.success, at.warning):
        out += [e.value for e in coll]
    for m in at.metric:
        out += [m.label, m.value, getattr(m.proto, "help", "")]
    for coll in (at.selectbox, at.radio, at.slider, at.text_input, at.number_input, at.multiselect, at.button):
        out += [x for w in coll for x in (w.label, getattr(w.proto, "help", ""))]
    return [s for s in out if isinstance(s, str)]
