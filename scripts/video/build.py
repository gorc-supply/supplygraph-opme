"""Assemble the demo videos with ffmpeg (imageio-ffmpeg binary, no admin rights needed).

Usage: python scripts/video/build.py <pt|en> [--extras]
Layout 16:9 (1920x1080): app recording 1920x960 on top + a 120 px caption band at the bottom, so captions
never cover numbers on screen. Captions are rendered with Pillow (semi-transparent box) and overlaid with
ffmpeg; narration sentences are placed at their cue times. Encoding: H.264 CRF 23 veryfast + AAC, faststart.
--extras (pt only): 4:5 feed version and poster.png. Every run also writes the README GIF of that language.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from storyboard import DEMO_URL, INTRO_S, OUTRO, OUTRO_S, REPO_URL, SCENES, TITLE  # noqa: E402
from timeline import BUILD, cues, scene_durations, sentence_starts, total_duration  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "portfolio" / "video"
BG = (15, 23, 42)  # #0f172a
BG_HEX = "0x0f172a"
FONTS = (
    Path("C:/Windows/Fonts")
    if Path("C:/Windows/Fonts").exists()
    else Path("/usr/share/fonts/truetype/dejavu")
)
F_BOLD = next((FONTS / f for f in ("segoeuib.ttf", "DejaVuSans-Bold.ttf") if (FONTS / f).exists()), None)
F_SEMI = next(
    (FONTS / f for f in ("seguisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf") if (FONTS / f).exists()), None
)
F_REG = next((FONTS / f for f in ("segoeui.ttf", "DejaVuSans.ttf") if (FONTS / f).exists()), None)
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30"]
AAC = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000"]


def ff(*args: str) -> None:
    r = subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True
    )
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:])


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


# ------------------------------------------------------------------------------------------ images
def card(lang: str, kind: str, w: int = 1920, h: int = 1080) -> Path:
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    s = w / 1920
    # discreet network motif (palette: blue #257de0 / orange #f47230)
    pts = [(0.12, 0.22), (0.2, 0.12), (0.27, 0.27), (0.85, 0.75), (0.92, 0.86), (0.78, 0.88), (0.88, 0.62)]
    for a, b in [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5), (3, 6)]:
        d.line(
            [(pts[a][0] * w, pts[a][1] * h), (pts[b][0] * w, pts[b][1] * h)],
            fill=(51, 65, 85),
            width=max(2, int(3 * s)),
        )
    for i, (x, y) in enumerate(pts):
        r = int((14 if i in (0, 3) else 9) * s)
        d.ellipse(
            [x * w - r, y * h - r, x * w + r, y * h + r], fill=(37, 125, 224) if i % 3 else (244, 114, 48)
        )

    def center(text: str, y: float, f: ImageFont.FreeTypeFont, fill) -> None:
        tw = d.textlength(text, font=f)
        d.text(((w - tw) / 2, y), text, font=f, fill=fill)

    if kind == "intro":
        t, sub, name = TITLE[lang]
        center(t, h * 0.36, font(F_BOLD, int(112 * s)), (255, 255, 255))
        center(sub, h * 0.36 + 150 * s, font(F_REG, int(50 * s)), (203, 213, 225))
        center(name, h * 0.36 + 250 * s, font(F_SEMI, int(42 * s)), (147, 197, 253))
    else:
        demo_label, code_label = OUTRO[lang]
        center(demo_label, h * 0.25, font(F_REG, int(44 * s)), (203, 213, 225))
        center(
            DEMO_URL.removeprefix("https://"), h * 0.25 + 64 * s, font(F_BOLD, int(64 * s)), (255, 255, 255)
        )
        center(code_label, h * 0.25 + 200 * s, font(F_REG, int(44 * s)), (203, 213, 225))
        center(REPO_URL, h * 0.25 + 264 * s, font(F_BOLD, int(64 * s)), (255, 255, 255))
        center(
            "Gabriel Cunha · SupplyGraph OPME", h * 0.25 + 420 * s, font(F_SEMI, int(38 * s)), (147, 197, 253)
        )
    out = BUILD / lang / f"card_{kind}_{w}x{h}.png"
    img.save(out)
    return out


def caption_png(text: str, path: Path, max_w: int, size: int) -> tuple[int, int]:
    f = font(F_SEMI, size)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    words, lines, cur = text.split(), [], ""
    for wd in words:  # wrap to max_w
        nxt = (cur + " " + wd).strip()
        if probe.textlength(nxt, font=f) <= max_w - 60 or not cur:
            cur = nxt
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    lh = int(size * 1.28)
    tw = int(max(probe.textlength(ln, font=f) for ln in lines))
    pw, ph = tw + 56, lh * len(lines) + 26
    img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=16, fill=(0, 0, 0, 165))  # semi-transparent band
    for i, ln in enumerate(lines):
        lw = d.textlength(ln, font=f)
        d.text(((pw - lw) / 2, 11 + i * lh), ln, font=f, fill=(255, 255, 255, 255))
    img.save(path)
    return pw, ph


# ------------------------------------------------------------------------------------------ video
def scene_clips(lang: str) -> list[Path]:
    durs = scene_durations(lang)
    clips = []
    for s in SCENES:
        meta = json.loads((BUILD / lang / "raw" / f"{s}.json").read_text(encoding="utf-8"))
        out = BUILD / lang / f"clip_{s}.mp4"
        ff(
            "-ss",
            f"{meta['ready']:.3f}",
            "-i",
            str(BUILD / lang / "raw" / meta.get("video", f"{s}.webm")),
            "-t",
            f"{durs[s]:.3f}",
            "-vf",
            # screencast frames are full-range JPEG (yuvj420p): convert to tv-range yuv420p like the cards, otherwise
            # ffmpeg reconfigures the filter graph at the concat boundary and the caption overlays vanish
            f"tpad=stop_mode=clone:stop_duration=4,fps=30,scale=in_range=pc:out_range=tv,"
            f"pad=1920:1080:0:0:color={BG_HEX},format=yuv420p",
            "-color_range",
            "tv",
            "-t",
            f"{durs[s]:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "16",
            str(out),
        )
        clips.append(out)
    return clips


def card_clip(png: Path, secs: float, out: Path) -> Path:
    fade_out = max(secs - 0.45, 0)
    ff(
        "-loop",
        "1",
        "-i",
        str(png),
        "-t",
        f"{secs}",
        "-vf",
        f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out}:d=0.45",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "16",
        str(out),
    )
    return out


def clean_master(lang: str) -> Path:
    parts = [
        card_clip(card(lang, "intro"), INTRO_S, BUILD / lang / "clip_intro.mp4"),
        *scene_clips(lang),
        card_clip(card(lang, "outro"), OUTRO_S, BUILD / lang / "clip_outro.mp4"),
    ]
    lst = BUILD / lang / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    out = BUILD / lang / "master_clean.mp4"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out))
    return out


def narration_inputs(lang: str, first: int) -> tuple[list[str], str]:
    """ffmpeg inputs + filter that places every sentence at its cue time and normalises loudness.
    `first` = index of the first narration input in the ffmpeg command."""
    inputs, chains, labels = [], [], []
    for i, c in enumerate(cues(lang)):
        inputs += ["-i", str(BUILD / lang / "tts" / c["audio"])]
        ms = int(c["start"] * 1000)
        chains.append(f"[{first + i}:a]aresample=48000,adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    total = total_duration(lang)
    filt = (
        ";".join(chains)
        + ";"
        + "".join(labels)
        + (
            f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad,atrim=0:{total},"
            "loudnorm=I=-16:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[aout]"
        )
    )
    return inputs, filt


def burn(lang: str, master: Path, out: Path, narrated: bool, layout: str = "16x9") -> None:
    total = total_duration(lang)
    cs = [c for c in cues(lang) if c["subtitle"]]
    cap_dir = BUILD / lang / f"captions_{layout}"
    cap_dir.mkdir(exist_ok=True)
    args = ["-i", str(master)]
    if layout == "16x9":
        base = "[0:v]null[v0]"
        max_w, size, band_cy = 1800, 46, 1020
    else:  # 4:5 feed: title on top, 16:9 video centred, captions below
        title = Image.new("RGBA", (1080, 250), (0, 0, 0, 0))
        d = ImageDraw.Draw(title)
        t, sub, _ = TITLE[lang]
        for txt, f, y, col in (
            (t, font(F_BOLD, 72), 70, (255, 255, 255)),
            (sub, font(F_REG, 34), 165, (203, 213, 225)),
        ):
            d.text(((1080 - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=col)
        title.save(cap_dir / "title.png")
        args += ["-loop", "1", "-i", str(cap_dir / "title.png")]
        base = (
            f"color=c={BG_HEX}:s=1080x1350:r=30:d={total}[bg];[0:v]scale=1080:608[sv];"
            "[bg][sv]overlay=0:262[b1];[b1][1:v]overlay=0:0[v0]"
        )
        max_w, size, band_cy = 1000, 46, 945
    n_in = lambda: args.count("-i")  # noqa: E731 - index of the next ffmpeg input
    first_cap = n_in()
    filters, last = [base], "v0"
    for i, c in enumerate(cs):
        png = cap_dir / f"cap_{i:02d}.png"
        pw, ph = caption_png(c["subtitle"], png, max_w, size)
        args += ["-loop", "1", "-i", str(png)]  # looped still: survives any filter-graph reconfiguration
        x = f"(main_w-{pw})/2"
        y = int(band_cy - ph / 2)
        filters.append(
            f"[{last}][{first_cap + i}:v]overlay={x}:{y}:enable='between(t,{c['start']},{c['end'] + 0.25})'[v{i + 1}]"
        )
        last = f"v{i + 1}"
    # Pass 1: captioned picture only. Mixing the narration into this same graph shifted it ~0.5 s early
    # (the many looped PNG inputs skew ffmpeg's input sync), so audio is rendered and muxed separately.
    silent_video = BUILD / lang / f"burned_{layout}.mp4"
    ff(
        *args,
        "-filter_complex",
        ";".join(filters),
        "-map",
        f"[{last}]",
        "-an",
        "-t",
        f"{total}",
        *ENC,
        str(silent_video),
    )
    # Pass 2: audio track on its own (narration placed at cue times, or digital silence).
    track = BUILD / lang / ("narration.wav" if narrated else "silence.wav")
    if narrated:
        a_inputs, a_filter = narration_inputs(lang, 0)
        ff(*a_inputs, "-filter_complex", a_filter, "-map", "[aout]", "-ar", "48000", str(track))
    else:
        ff(
            "-f",
            "lavfi",
            "-t",
            f"{total}",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            str(track),
        )
    # Pass 3: plain mux, picture copied untouched.
    ff(
        "-i",
        str(silent_video),
        "-i",
        str(track),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        *AAC,
        "-t",
        f"{total}",
        "-movflags",
        "+faststart",
        str(out),
    )


def srt(lang: str) -> Path:
    def ts(t: float) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"

    cs = [c for c in cues(lang) if c["subtitle"]]
    body = "\n".join(
        f"{i}\n{ts(c['start'])} --> {ts(c['end'] + 0.25)}\n{c['subtitle']}\n" for i, c in enumerate(cs, 1)
    )
    out = OUT / f"supplygraph-demo-{lang}.srt"
    out.write_text(body, encoding="utf-8")
    return out


def poster(lang: str, narrated: Path) -> None:
    t_chart = INTRO_S + sentence_starts(lang, "overview")[3] + 1.6  # graph-view China bar highlighted
    ff("-ss", f"{t_chart:.2f}", "-i", str(narrated), "-frames:v", "1", str(OUT / "poster.png"))


def gif(lang: str, silent: Path) -> Path:
    """10 s README GIF (ERP 0.4% -> graph 43.6%), from the version without narration."""
    out = OUT / f"supplygraph-demo-{lang}.gif"
    t0 = INTRO_S + sentence_starts(lang, "overview")[2] - 0.6
    pal = BUILD / lang / "palette.png"
    vf = "fps=10,scale=960:-1:flags=lanczos"
    clip = ["-ss", f"{t0:.2f}", "-t", "10", "-i", str(silent)]
    ff(*clip, "-vf", f"{vf},palettegen=stats_mode=diff:max_colors=128", str(pal))
    ff(
        *clip,
        "-i",
        str(pal),
        "-lavfi",
        f"{vf}[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
        str(out),
    )
    return out


def main(lang: str, with_extras: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = clean_master(lang)
    narrated = OUT / f"supplygraph-demo-{lang}-1080p.mp4"
    silent = (
        OUT / f"supplygraph-demo-{lang}-1080p-sem-narracao.mp4"
        if lang == "pt"
        else OUT / f"supplygraph-demo-{lang}-1080p-no-narration.mp4"
    )
    burn(lang, master, narrated, narrated=True)
    burn(lang, master, silent, narrated=False)
    srt(lang)
    print(f"{lang}: {narrated.name}, {silent.name}, {gif(lang, silent).name} ({total_duration(lang)} s)")
    if with_extras:
        burn(lang, master, OUT / f"supplygraph-demo-{lang}-4x5.mp4", narrated=True, layout="4x5")
        poster(lang, narrated)
        print(f"{lang}: 4x5, poster.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pt", "--extras" in sys.argv)
