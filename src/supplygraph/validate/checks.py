"""Graph data-quality checks. Each check is a .cypher file that returns the violating rows:
zero rows = pass. Used by `sgraph validate` and by tests/test_validation.py (fails the build)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from neo4j import Driver

from supplygraph.config import CYPHER_DIR, REPORTS_DIR
from supplygraph.db import run

CHECKS: dict[str, str] = {
    "01_bom_is_dag": "BOM (COMPONENT_OF) has no cycles",
    "02_finished_reaches_raw": "Every finished item has a BOM path down to raw material",
    "03_items_have_source": "Every item has a supplier (purchased) or a plant (finished)",
    "04_share_pct_sums_100": "Supplier shares sum to 100% per item (and per sub-tier buyer)",
    "05_no_orphans": "No orphan suppliers, hospitals without a DC, or DCs without stock",
    "06_lot_genealogy_to_raw": "Every finished lot traces back to a raw-material lot",
    "07_no_expired_released": "No expired lot is still 'released'",
    "08_deliveries_within_lot_qty": "Deliveries never exceed lot quantity",
    "09_genealogy_chronology": "Child lots are never older than their parent lots",
}


@dataclass
class CheckResult:
    name: str
    description: str
    violations: list[dict] = field(default_factory=list)
    ms: float = 0.0

    @property
    def passed(self) -> bool:
        return not self.violations


def run_check(driver: Driver, name: str, as_of: str) -> CheckResult:
    q = (CYPHER_DIR / "validation" / f"{name}.cypher").read_text(encoding="utf-8")
    t0 = time.perf_counter()
    rows = run(driver, q, {"as_of": as_of}, timeout=300)
    return CheckResult(name, CHECKS[name], rows, (time.perf_counter() - t0) * 1000)


def run_all(driver: Driver, as_of: str) -> list[CheckResult]:
    return [run_check(driver, n, as_of) for n in CHECKS]


def write_report(results: list[CheckResult], profile: str, counts: tuple[int, int]) -> str:
    lines = [
        "# Data quality report",
        "",
        f"- Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Profile: `{profile}`  ·  Graph: {counts[0]:,} nodes / {counts[1]:,} relationships",
        f"- Result: **{sum(r.passed for r in results)}/{len(results)} checks passed**",
        "",
        "| # | Check | Status | Violations | Time (ms) |",
        "|---|---|---|---:|---:|",
    ]
    for r in results:
        lines.append(
            f"| {r.name[:2]} | {r.description} | {'PASS' if r.passed else 'FAIL'} | {len(r.violations)} | {r.ms:.0f} |"
        )
    failed = [r for r in results if not r.passed]
    if failed:
        lines += ["", "## Sample violations", ""]
        for r in failed:
            lines.append(f"### {r.name}")
            for v in r.violations[:10]:
                lines.append(f"- `{v}`")
    lines += ["", "Each check lives in `cypher/validation/` and returns the violating rows (0 rows = pass)."]
    text = "\n".join(lines) + "\n"
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / "data_quality.md").write_text(text, encoding="utf-8")
    return text
