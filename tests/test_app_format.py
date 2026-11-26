"""Language-aware formatting used by the Streamlit app (app/fmt.py) - pure functions, no Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import fmt  # noqa: E402


@pytest.mark.parametrize(("v", "pt", "en"), [(60560, "60.560", "60,560"), (238873, "238.873", "238,873"),
                                              (0, "0", "0"), (999, "999", "999")])
def test_integer(v, pt, en):
    assert fmt.integer(v, "pt") == pt and fmt.integer(v, "en") == en


def test_decimals_and_percent():
    assert fmt.num(1234.5, "pt", 1) == "1.234,5" and fmt.num(1234.5, "en", 1) == "1,234.5"
    assert fmt.pct(43.6, "pt", 1) == "43,6%" and fmt.pct(43.6, "en", 1) == "43.6%"
    assert fmt.pct(29.46, "pt") == "29%"


@pytest.mark.parametrize(("v", "pt", "en"), [
    (287_786_870, "R$ 287,8 mi", "R$ 287.8 M"),
    (1_234_000_000, "R$ 1,2 bi", "R$ 1.2 B"),
    (23_459, "R$ 23 mil", "R$ 23 k"),
    (950, "R$ 950", "R$ 950"),
])
def test_money(v, pt, en):
    assert fmt.money(v, "pt") == pt and fmt.money(v, "en") == en


def test_money_full():
    assert fmt.money_full(1_234_567, "pt") == "R$ 1.234.567" and fmt.money_full(1_234_567, "en") == "R$ 1,234,567"


def test_missing_values():
    assert fmt.integer(None, "pt") == "–" and fmt.money(float("nan"), "en") == "–"


def test_escape_dollar_for_markdown():
    assert fmt.esc("Receita (R$): R$ 287,8 mi") == r"Receita (R\$): R\$ 287,8 mi"
    assert fmt.esc(r"R\$ 1") == r"R\$ 1"  # idempotent: never double-escapes
