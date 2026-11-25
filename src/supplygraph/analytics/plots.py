"""Static charts for docs/README (matplotlib). Palette: validated reference palette
(series-1 blue #257de0, series-2 orange #f47230, sequential blue ramp, gray text inks)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

BLUE, ORANGE, AQUA = "#257de0", "#f47230", "#00b894"
TEXT, TEXT2, GRID = "#191919", "#666666", "#e6e6e6"
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue", ["#f4f8fd", "#cce3fd", "#9dc8f7", "#6aabf1", "#338ced", "#2370cd", "#1757ac", "#0e3d7e"]
)


def _style(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, loc="left", fontsize=13, color=TEXT, fontweight="bold", pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=TEXT2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TEXT2, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def erp_vs_graph(
    df: pd.DataFrame, out: Path, value_erp: str, value_graph: str, title: str, subtitle: str, top: int = 10
) -> None:
    d = df.sort_values(value_graph, ascending=False).head(top).iloc[::-1]
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(8.5, 0.45 * len(d) + 1.6), dpi=150)
    h = 0.36
    ax.barh(y + h / 2 + 0.02, d[value_graph], height=h, color=BLUE, label="Graph view (all tiers)")
    ax.barh(y - h / 2 - 0.02, d[value_erp], height=h, color=ORANGE, label="ERP view (tier-1 + plant)")
    for yi, (e, g) in enumerate(zip(d[value_erp], d[value_graph], strict=True)):
        ax.text(g + 0.8, yi + h / 2, f"{g:.0f}%", va="center", fontsize=8.5, color=TEXT)
        ax.text(e + 0.8, yi - h / 2, f"{e:.0f}%", va="center", fontsize=8.5, color=TEXT2)
    ax.set_yticks(y, d["country"])
    ax.set_xlabel("% of monthly revenue", color=TEXT2, fontsize=9)
    ax.set_xlim(0, max(100, d[value_graph].max() * 1.1))
    _style(ax, title, subtitle)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def heatmap(pivot: pd.DataFrame, out: Path, title: str, subtitle: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 0.32 * len(pivot) + 2.4), dpi=150)
    im = ax.imshow(pivot.to_numpy() / 1e6, aspect="auto", cmap=SEQ)
    ax.set_yticks(range(len(pivot)), pivot.index, fontsize=8)
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=60, ha="right", fontsize=7.5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, loc="left", fontsize=13, color=TEXT, fontweight="bold", pad=22)
    ax.text(0, 1.01, subtitle, transform=ax.transAxes, fontsize=9.5, color=TEXT2)
    ax.tick_params(colors=TEXT2)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("Revenue at risk (R$ M, synthetic)", color=TEXT2, fontsize=8.5)
    cb.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def tts_ttr(impact: pd.DataFrame, ttr: int, out: Path, title: str, subtitle: str) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    ok = impact[impact.tts_days >= ttr]
    bad = impact[impact.tts_days < ttr]
    ax.scatter(
        ok.tts_days,
        ok.daily_demand * 30,
        s=12,
        color="#9c9c9c",
        alpha=0.6,
        label="Survives (TTS >= TTR)",
        linewidths=0,
    )
    ax.scatter(
        bad.tts_days,
        bad.daily_demand * 30,
        s=14,
        color=ORANGE,
        alpha=0.85,
        label="Stock-out (TTS < TTR)",
        linewidths=0,
    )
    ax.axvline(ttr, color=TEXT, linewidth=1.2, linestyle="--")
    ax.text(ttr + 1, ax.get_ylim()[1] * 0.95, f"TTR = {ttr} days", fontsize=9, color=TEXT, va="top")
    ax.set_xlabel("Time-to-Survive (days of stock + pipeline) per SKU x DC", color=TEXT2, fontsize=9)
    ax.set_ylabel("Monthly demand at the DC (units)", color=TEXT2, fontsize=9)
    _style(ax, title, subtitle)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def timeline(tl: pd.DataFrame, out: Path, title: str, subtitle: str) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 3.8), dpi=150)
    ax.plot(tl.day, tl.cumulative_revenue_lost / 1e6, color=BLUE, linewidth=2)
    ax.fill_between(tl.day, tl.cumulative_revenue_lost / 1e6, color=BLUE, alpha=0.08)
    ax.set_xlabel("Days since disruption", color=TEXT2, fontsize=9)
    ax.set_ylabel("Cumulative revenue lost (R$ M)", color=TEXT2, fontsize=9)
    _style(ax, title, subtitle)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def bar_ms(
    df: pd.DataFrame,
    x: str,
    groups: list[str],
    out: Path,
    title: str,
    subtitle: str,
    ylabel: str,
    log: bool = False,
) -> None:
    """Grouped bars (one per engine) for the benchmark."""
    colors = [BLUE, ORANGE, AQUA]
    cats = df[x].tolist()
    n = len(groups)
    w = 0.8 / n
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    xs = np.arange(len(cats))
    for k, g in enumerate(groups):
        ax.bar(xs + (k - (n - 1) / 2) * w, df[g], width=w - 0.03, color=colors[k], label=g)
    ax.set_xticks(xs, cats, rotation=30, ha="right", fontsize=8)
    if log:
        ax.set_yscale("log")
    ax.set_ylabel(ylabel, color=TEXT2, fontsize=9)
    _style(ax, title, subtitle)
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out, facecolor="white")
    plt.close(fig)
