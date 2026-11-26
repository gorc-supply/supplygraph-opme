"""Pure, language-aware formatting helpers (no Streamlit import, unit-tested in tests/test_app_format.py).

pt: 60.560 · 43,6% · R$ 287,8 mi       en: 60,560 · 43.6% · R$ 287.8 M
`esc()` must wrap every string that Streamlit renders as Markdown (metric label/value, caption, help, ...):
an unescaped pair of "$" is rendered as LaTeX ("R$ ... R$" turned the overview caption into a formula).
"""

from __future__ import annotations

import math

_PT_SWAP = str.maketrans(",.", ".,")


def esc(text: object) -> str:
    """Escape dollar signs for Streamlit Markdown (prevents LaTeX rendering)."""
    return str(text).replace("\\$", "$").replace("$", "\\$")


def _missing(v: object) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def num(v: float | int | None, lang: str, decimals: int = 0) -> str:
    if _missing(v):
        return "–"
    s = f"{float(v):,.{decimals}f}"
    return s.translate(_PT_SWAP) if lang == "pt" else s


def integer(v: float | int | None, lang: str) -> str:
    return "–" if _missing(v) else num(round(float(v)), lang, 0)


def pct(v: float | None, lang: str, decimals: int = 0) -> str:
    """`v` already in percent points (43.6 -> '43,6%' / '43.6%')."""
    return "–" if _missing(v) else f"{num(v, lang, decimals)}%"


def money(v: float | None, lang: str) -> str:
    """Compact BRL: R$ 287,8 mi / R$ 23 mil (pt) - R$ 287.8 M / R$ 23 k (en)."""
    if _missing(v):
        return "–"
    v = float(v)
    units = (("bi", "B"), ("mi", "M"), ("mil", "k"))
    for (pt_u, en_u), scale, dec in zip(units, (1e9, 1e6, 1e3), (1, 1, 0), strict=True):
        if abs(v) >= scale:
            return f"R$ {num(v / scale, lang, dec)} {pt_u if lang == 'pt' else en_u}"
    return f"R$ {num(v, lang, 0)}"


def money_full(v: float | None, lang: str) -> str:
    """Full BRL amount for tables: R$ 1.234.567 (pt) / R$ 1,234,567 (en)."""
    return "–" if _missing(v) else f"R$ {num(v, lang, 0)}"
