"""Record each demo scene from the PUBLISHED app with Playwright (Chromium), one WebM per scene.

Usage: python scripts/video/record.py <pt|en> [scene,scene,...]
  - wakes the Streamlit Cloud app and warms every page (no cold start / loading screen on camera)
  - records the app itself (APP_URL, without the Streamlit Cloud frame) through the Chromium screencast (CDP):
    viewport 1440x720 CSS px at device scale 4/3 = 1920x960 physical px, i.e. the app shown at 133% so text is
    readable in a 1080p video (Playwright's built-in video ignores the device scale)
  - injects a visible cursor (headless Chromium draws none) and moves it smoothly to real element positions
  - writes .video-build/<lang>/raw/<scene>.webm + <scene>.json (ready offset, duration, checks)
Re-run with a scene list to re-record only the scenes that failed.
"""

from __future__ import annotations

import base64
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from storyboard import APP_URL, DEMO_URL, RECALL_LOT, SCENES, UI  # noqa: E402
from timeline import BUILD, scene_durations, sentence_starts  # noqa: E402

W, H = 1440, 720  # CSS px; x 4/3 device scale = 1920 x 960 physical px
SCALE = 4 / 3
FF = imageio_ffmpeg.get_ffmpeg_exe()
PATHS = {
    "overview": "",
    "explorer": "explorer",
    "simulator": "simulator",
    "recall": "recall",
    "ranking": "ranking",
}

INIT_JS = r"""
(() => {
  const css = `[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
               [data-testid="stHeaderActionElements"] { visibility: hidden !important; }`;
  const install = () => {
    if (!document.getElementById('__demo_css')) {
      const s = document.createElement('style'); s.id = '__demo_css'; s.textContent = css; document.head.appendChild(s);
    }
    if (document.getElementById('__cur')) return;
    const c = document.createElement('div'); c.id = '__cur';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 28 28"><path d="M4 2 L4 22.5 L9.4 17.4 L13.2 26 L16.8 24.4 L13.1 15.9 L20.4 15.9 Z" fill="#111827" stroke="#ffffff" stroke-width="1.8" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position: 'fixed', left: '-60px', top: '-60px', zIndex: 2147483647, pointerEvents: 'none',
                            transform: 'translate(-4px,-2px)', filter: 'drop-shadow(0 1px 2px rgba(0,0,0,.35))'});
    document.documentElement.appendChild(c);
    const r = document.createElement('div'); r.id = '__ripple';
    Object.assign(r.style, {position: 'fixed', width: '36px', height: '36px', borderRadius: '50%', border: '3px solid #257de0',
                            left: '-100px', top: '-100px', zIndex: 2147483646, pointerEvents: 'none', opacity: 0,
                            transform: 'translate(-50%,-50%)'});
    document.documentElement.appendChild(r);
  };
  window.__cursor = (x, y) => { install(); const c = document.getElementById('__cur'); c.style.left = x + 'px'; c.style.top = y + 'px'; };
  window.__click = (x, y) => { install(); const r = document.getElementById('__ripple'); r.style.left = x + 'px'; r.style.top = y + 'px';
    r.animate([{opacity: .9, transform: 'translate(-50%,-50%) scale(.5)'}, {opacity: 0, transform: 'translate(-50%,-50%) scale(1.7)'}], {duration: 500}); };
  document.addEventListener('DOMContentLoaded', install);
})();
"""


class Cursor:
    def __init__(self, page: Page, x: float = W * 0.55, y: float = H * 0.45):
        self.p, self.x, self.y = page, x, y
        self.p.evaluate("([x, y]) => window.__cursor(x, y)", [x, y])

    def move(self, x: float, y: float, secs: float = 0.9) -> None:
        steps = max(8, int(secs * 40))
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            t = i / steps
            e = 0.5 - 0.5 * math.cos(math.pi * t)  # ease in-out
            nx, ny = x0 + (x - x0) * e, y0 + (y - y0) * e
            self.p.mouse.move(nx, ny)
            self.p.evaluate("([x, y]) => window.__cursor(x, y)", [nx, ny])
            self.p.wait_for_timeout(secs * 1000 / steps)
        self.x, self.y = x, y

    def to(self, box: dict, fx: float = 0.5, fy: float = 0.5, secs: float = 0.9) -> None:
        self.move(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy, secs)

    def click(self) -> None:
        self.p.evaluate("([x, y]) => window.__click(x, y)", [self.x, self.y])
        self.p.mouse.click(self.x, self.y)


def wait_ready(page: Page, timeout: int = 240_000) -> None:
    """Ready = title rendered and NO running indicator / spinner / skeleton for 1.5 s in a row
    (Streamlit may start a cached computation a moment after the first paint)."""
    page.wait_for_selector('[data-testid="stMainBlockContainer"] h1', timeout=timeout)
    busy_js = """() => !!document.querySelector('[data-testid="stStatusWidget"], [data-testid="stSpinner"], [data-testid="stSkeleton"]')"""
    t0, calm_since = time.monotonic(), None
    while time.monotonic() - t0 < timeout / 1000:
        if page.evaluate(busy_js):
            calm_since = None
        elif calm_since is None:
            calm_since = time.monotonic()
        elif time.monotonic() - calm_since >= 1.5:
            return
        page.wait_for_timeout(150)
    raise TimeoutError("app did not become idle")


def check_clean(page: Page) -> list[str]:
    """Problems visible on screen: exceptions, error boxes, spinners, connection errors."""
    js = """() => {
      const bad = [];
      if (document.querySelector('[data-testid="stException"]')) bad.push('exception');
      if (document.querySelector('[data-testid="stAlertContentError"], .stAlert [kind="error"]')) bad.push('error box');
      if (document.querySelector('[data-testid="stSpinner"], [data-testid="stSkeleton"]')) bad.push('spinner');
      const t = document.body.innerText;
      if (/Traceback|ModuleNotFoundError|Não consegui conectar|Could not connect/.test(t)) bad.push('error text');
      return bad; }"""
    return page.evaluate(js)


def metric_boxes(page: Page) -> list[dict]:
    return [m.bounding_box() for m in page.locator('[data-testid="stMain"] [data-testid="stMetric"]').all()]


def metric_values(page: Page) -> list[str]:
    return [
        v.inner_text().strip()
        for v in page.locator('[data-testid="stMain"] [data-testid="stMetricValue"]').all()
    ]


def smooth_scroll(
    page: Page, dy: float, secs: float = 1.2, at: tuple[float, float] = (W * 0.6, H * 0.6)
) -> None:
    page.mouse.move(*at)
    steps = max(10, int(secs * 30))
    for _ in range(steps):
        page.mouse.wheel(0, dy / steps)
        page.wait_for_timeout(secs * 1000 / steps)


def bar_point(page: Page, country: str, trace: int) -> dict | None:
    """Bounding box of a Plotly bar (trace 0 = graph view, 1 = ERP view) on the row labelled `country`:
    find the y-axis tick with that label, then the bar of the trace whose vertical centre is closest."""
    return page.evaluate(
        """([country, trace]) => {
      const ticks = [...document.querySelectorAll('.js-plotly-plot .yaxislayer-above .ytick text')];
      const tick = ticks.find(t => t.textContent.trim() === country);
      const traces = document.querySelectorAll('.js-plotly-plot .barlayer .trace');
      if (!tick || !traces[trace]) return null;
      const ty = tick.getBoundingClientRect(); const cy = ty.top + ty.height / 2;
      let best = null, dist = 1e9;
      for (const p of traces[trace].querySelectorAll('.point path')) {
        const r = p.getBoundingClientRect(); const d = Math.abs(r.top + r.height / 2 - cy);
        if (d < dist) { dist = d; best = {x: r.left, y: r.top, width: Math.max(r.width, 4), height: r.height}; } }
      return dist < 40 ? best : null; }""",
        [country, trace],
    )


# ------------------------------------------------------------------------------------------ scenes
def scene_overview(page: Page, cur: Cursor, at, lang: str) -> dict:
    boxes = metric_boxes(page)
    cur.to(boxes[2], 0.4, 0.6, 1.1)  # suppliers tier 1 (direct suppliers)
    at(1.8)
    cur.to(boxes[0], 0.4, 0.6, 1.0)
    at(4.4)
    chart = page.locator(".js-plotly-plot").first.bounding_box()
    smooth_scroll(page, chart["y"] - 70, 1.4)  # bring the ERP x graph chart into view
    page.wait_for_timeout(300)
    erp = bar_point(page, "China", 1)
    graph = bar_point(page, "China", 0)
    at(starts[2] - 0.3)
    cur.to(erp, 0.5 if erp["width"] < 20 else 0.7, 0.5, 1.0)  # ERP view: China 0.4%
    at(starts[3] - 0.3)
    cur.to(graph, 0.85, 0.5, 1.0)  # graph view: 43.6%
    at(starts[4] - 0.4)
    smooth_scroll(page, -(chart["y"] - 70), 1.2)  # back to the KPI cards
    page.wait_for_timeout(250)
    fd = (
        page.locator('[data-testid="stMain"] [data-testid="stMetric"]')
        .filter(has_text=UI[lang]["false_dual"])
        .first
    )
    cur.to(fd.bounding_box(), 0.35, 0.65, 1.0)
    vals = metric_values(page)
    return {"metrics": vals, "expect_ok": "66 / 224 (29%)" in vals and ("60.560" in vals or "60,560" in vals)}


def scene_explorer(page: Page, cur: Cursor, at, lang: str) -> dict:
    """Starts with the graph filling the screen (pre-scrolled before the ready mark, see PRE_SCROLL)."""
    frame = page.locator('[data-testid="stMain"] iframe').first
    fb = frame.bounding_box()
    cur.to(fb, 0.30, 0.35, 1.3)
    at(2.0)
    cur.to(fb, 0.50, 0.45, 1.4)
    at(starts[0] + 2.4)
    legend_loc = page.locator('[data-testid="stMain"] [data-testid="stHtml"]').last
    smooth_scroll(page, legend_loc.bounding_box()["y"] - (H - 170), 1.0)  # reveal the community legend
    cur.to(legend_loc.bounding_box(), 0.25, 0.5, 0.9)
    at(starts[1] - 0.1)
    smooth_scroll(page, frame.bounding_box()["y"] - 8, 1.0)  # back to the graph
    fb = frame.bounding_box()
    cur.to(fb, 0.42, 0.40, 1.2)
    at(starts[1] + 2.0)
    cur.to(fb, 0.60, 0.55, 1.2)
    return {"legend": legend_loc.inner_text()[:160]}


def scene_simulator(page: Page, cur: Cursor, at, lang: str) -> dict:
    sel = page.locator('[data-testid="stMain"] [data-testid="stSelectbox"]').first.bounding_box()
    sld = page.locator('[data-testid="stMain"] [data-testid="stSlider"]').first.bounding_box()
    boxes = metric_boxes(page)
    cur.to(sel, 0.35, 0.7, 1.1)  # S-T3-003
    at(2.6)
    cur.to(sld, 0.97, 0.55, 1.1)  # TTR = 180
    at(starts[1] - 0.2)
    cur.to(boxes[3], 0.3, 0.65, 1.0)  # first stock-out: day 35
    at(starts[2] - 0.2)
    cur.to(boxes[2], 0.3, 0.65, 0.9)  # 164 / 167 implants
    at(starts[2] + 2.0)
    cur.to(boxes[1], 0.3, 0.65, 0.8)  # 1,400 hospitals
    at(starts[3] - 0.2)
    cur.to(boxes[0], 0.3, 0.65, 0.9)  # R$ 242.2 M
    at(starts[3] + 1.6)
    chart_loc = page.locator(".js-plotly-plot").first
    smooth_scroll(page, chart_loc.bounding_box()["y"] - 90, 1.0)
    cur.to(chart_loc.bounding_box(), 0.30, 0.55, 0.9)
    vals = metric_values(page)
    return {
        "metrics": vals,
        "expect_ok": vals[:4]
        in (["R$ 242,2 mi", "1.400", "164 / 167", "35"], ["R$ 242.2 M", "1,400", "164 / 167", "35"]),
    }


def scene_recall(page: Page, cur: Cursor, at, lang: str) -> dict:
    box_in = page.locator('[data-testid="stMain"] [data-testid="stTextInput"] input').first
    cur.to(box_in.bounding_box(), 0.25, 0.5, 0.9)
    cur.click()
    page.keyboard.press("Control+A")
    page.keyboard.type(RECALL_LOT, delay=40)
    btn = page.locator('[data-testid="stMain"] button').filter(has_text=UI[lang]["trace"]).first
    cur.to(btn.bounding_box(), 0.5, 0.5, 0.6)
    cur.click()
    page.wait_for_timeout(400)
    wait_ready(page)
    page.wait_for_function(
        "(lot) => document.body.innerText.includes(lot + ' ')", arg="RM-TI64", timeout=60000
    )
    boxes = metric_boxes(page)
    at(starts[1] - 0.2)
    cur.to(boxes[1], 0.3, 0.65, 0.9)  # 105 implant lots
    at(starts[1] + 2.4)
    cur.to(boxes[2], 0.3, 0.65, 0.8)  # 180 hospitals (26)
    at(starts[2] - 0.2)
    cur.to(boxes[3], 0.3, 0.65, 0.9)  # 684 units
    at(starts[2] + 2.0)
    vals = metric_values(page)
    smooth_scroll(page, 260, 1.0)  # the hospitals on the map
    return {"metrics": vals, "expect_ok": vals[1:4] == ["105", "180 (26)", "684"]}


def scene_ranking(page: Page, cur: Cursor, at, lang: str) -> dict:
    boxes = metric_boxes(page)
    table = page.locator('[data-testid="stMain"] [data-testid="stDataFrame"]').first.bounding_box()
    cur.to(table, 0.30, 0.18, 1.1)  # top rows
    at(2.0)
    cur.to(boxes[1], 0.3, 0.65, 0.9)  # Tier 2/3 in the top 10
    before = metric_values(page)
    at(starts[1] - 0.3)
    slider = (
        page.locator('[data-testid="stSidebar"] [data-testid="stSlider"]')
        .filter(has_text=UI[lang]["rev_slider"])
        .first
    )
    # Streamlit 1.67 slider (react-aria): group > track div > thumb div > div > input[type=range]
    value_input = slider.locator('input[type="range"]').first
    thumb = value_input.locator("xpath=../..")
    track = slider.locator('[role="group"] > div[data-orientation="horizontal"]').first.bounding_box()
    tb = thumb.bounding_box()
    cur.to(tb, 0.5, 0.5, 1.0)
    page.mouse.down()
    target_x = track["x"] + track["width"] * 0.60
    cur.move(target_x, cur.y, 1.4)  # drag revenue-at-risk weight 35% -> ~60%
    page.mouse.up()
    page.wait_for_timeout(300)
    wait_ready(page)
    page.wait_for_timeout(500)
    cur.to(metric_boxes(page)[1], 0.3, 0.65, 1.0)
    after = metric_values(page)
    return {
        "before": before,
        "after": after,
        "weight": value_input.get_attribute("value"),
        "expect_ok": before[1].startswith("10") and after[1].startswith("10"),
    }


class Screencast:
    """CDP screencast: JPEG frames in physical pixels with wall-clock timestamps (frames come only on change)."""

    def __init__(self, page: Page, out_dir: Path):
        self.dir = out_dir
        shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True)
        self.frames: list[tuple[float, Path]] = []
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on_frame)
        self.cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 92,
                "maxWidth": round(W * SCALE),
                "maxHeight": round(H * SCALE),
                "everyNthFrame": 1,
            },
        )

    def _on_frame(self, params: dict) -> None:
        path = self.dir / f"{len(self.frames):05d}.jpg"
        path.write_bytes(base64.b64decode(params["data"]))
        self.frames.append((params["metadata"]["timestamp"], path))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

    def stop(self) -> None:
        self.cdp.send("Page.stopScreencast")

    def render(self, start: float, duration: float, out: Path) -> int:
        """Constant 30 fps clip [start, start+duration] (epoch seconds), holding frames between changes."""
        before = [f for f in self.frames if f[0] <= start]
        inside = [f for f in self.frames if start < f[0] < start + duration]
        seq = ([(start, before[-1][1])] if before else []) + inside
        if not seq:
            raise RuntimeError("no screencast frames captured")
        lines = []
        for i, (ts, path) in enumerate(seq):
            nxt = seq[i + 1][0] if i + 1 < len(seq) else start + duration
            lines.append(f"file '{path.as_posix()}'\nduration {max(nxt - ts, 0.001):.4f}\n")
        lines.append(f"file '{seq[-1][1].as_posix()}'\n")
        lst = self.dir / "frames.txt"
        lst.write_text("".join(lines), encoding="utf-8")
        r = subprocess.run(
            [
                FF,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-vf",
                "fps=30,scale=1920:960:flags=lanczos,format=yuv420p",
                "-t",
                f"{duration:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "14",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode:
            raise RuntimeError(r.stderr[-2000:])
        return len(seq)


SCENE_FN = {
    "overview": scene_overview,
    "explorer": scene_explorer,
    "simulator": scene_simulator,
    "recall": scene_recall,
    "ranking": scene_ranking,
}
starts: list[float] = []


def wake_and_warm(browser, lang: str) -> None:
    ctx = browser.new_context(viewport={"width": W, "height": H})
    pg = ctx.new_page()
    pg.goto(f"{DEMO_URL}/?lang={lang}", wait_until="load", timeout=180_000)
    t0 = time.time()
    while time.time() - t0 < 300:  # sleeping app -> click "Yes, get this app back up!"
        if any("/~/+/" in f.url for f in pg.frames):
            break
        for f in pg.frames:
            try:
                if f.get_by_text("get this app back up").count():
                    f.get_by_role("button").first.click()
            except Exception:  # noqa: BLE001
                pass
        pg.wait_for_timeout(5000)
    for scene in SCENES:  # warm every page (Streamlit cache + Aura) in the same language
        pg.goto(f"{APP_URL}{PATHS[scene]}?lang={lang}", wait_until="load", timeout=180_000)
        wait_ready(pg)
        if scene == "recall":
            pg.locator('[data-testid="stTextInput"] input').first.fill(RECALL_LOT)
            pg.locator("button").filter(has_text=UI[lang]["trace"]).first.click()
            pg.wait_for_timeout(500)
            wait_ready(pg)
        pg.wait_for_timeout(1500)
        print(f"  warmed {scene}: {check_clean(pg) or 'clean'}")
    ctx.close()


def record(lang: str, scenes: list[str]) -> None:
    global starts
    durs = scene_durations(lang)
    raw = BUILD / lang / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        wake_and_warm(browser, lang)
        for scene in scenes:
            ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
            ctx.add_init_script(INIT_JS)
            page = ctx.new_page()
            cast = Screencast(page, BUILD / lang / "frames" / scene)
            page.goto(f"{APP_URL}{PATHS[scene]}?lang={lang}", wait_until="load", timeout=180_000)
            wait_ready(page)
            page.wait_for_timeout(
                9000 if scene == "explorer" else 1200
            )  # explorer: graph layout settles + refit
            page.evaluate(
                "() => { const m = document.querySelector('[data-testid=\"stMain\"]'); if (m) m.scrollTo(0, 0); }"
            )
            if scene == "explorer":  # PRE_SCROLL: the graph fills the screen from the first frame
                fy = page.locator('[data-testid="stMain"] iframe').first.bounding_box()["y"]
                page.mouse.move(W * 0.5, H * 0.5)
                page.mouse.wheel(0, fy - 8)
                page.wait_for_timeout(700)
            cur = Cursor(page)
            page.wait_for_timeout(300)
            t0 = time.monotonic()
            ready_epoch = time.time()
            starts = sentence_starts(lang, scene)

            def at(sec: float, _t0=t0, _page=page) -> None:
                wait = sec - (time.monotonic() - _t0)
                if wait > 0:
                    _page.wait_for_timeout(wait * 1000)

            info = SCENE_FN[scene](page, cur, at, lang)
            at(durs[scene] + 0.3)
            problems = check_clean(page)
            page.screenshot(path=str(raw / f"{scene}_end.png"))
            cast.stop()
            n = cast.render(ready_epoch, durs[scene], raw / f"{scene}.mp4")
            ctx.close()
            meta = {
                "scene": scene,
                "lang": lang,
                "video": f"{scene}.mp4",
                "ready": 0.0,
                "duration": durs[scene],
                "frames": n,
                "fps_effective": round(n / durs[scene], 1),
                "problems": problems,
                **info,
            }
            (raw / f"{scene}.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            ok = not problems and info.get("expect_ok", True)
            print(
                f"{'OK  ' if ok else 'FAIL'} {lang}/{scene}: dur={durs[scene]}s frames={n} ({meta['fps_effective']}/s) "
                f"{problems} { {k: v for k, v in info.items() if k != 'expect_ok'} }"
            )
        browser.close()


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "pt"
    sel = sys.argv[2].split(",") if len(sys.argv) > 2 else SCENES
    record(lang, sel)
