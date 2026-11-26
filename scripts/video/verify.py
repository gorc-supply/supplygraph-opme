"""Sample one frame every 5 s of a rendered video into a contact sheet (for visual review).

Usage: python scripts/video/verify.py <video.mp4> [step_seconds]  -> .video-build/verify/<name>_sheet_<n>.png
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()
BUILD = Path(__file__).resolve().parents[2] / ".video-build" / "verify"


def duration(p: Path) -> float:
    err = subprocess.run([FF, "-hide_banner", "-i", str(p)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def main(video: Path, step: float = 5.0) -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    total = duration(video)
    times = [t + 2.5 for t in range(0, int(total), int(step)) if t + 2.5 < total]
    thumbs = []
    for t in times:
        f = BUILD / f"{video.stem}_{t:05.1f}.png"
        subprocess.run(
            [FF, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(f)],
            check=True,
        )
        thumbs.append((t, Image.open(f)))
    w0, h0 = thumbs[0][1].size
    tw = 900
    th = int(h0 * tw / w0)
    per_sheet, cols = 6, 2
    font = (
        ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
        if Path("C:/Windows/Fonts/segoeuib.ttf").exists()
        else ImageFont.load_default()
    )
    for k in range(0, len(thumbs), per_sheet):
        chunk = thumbs[k : k + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 44) + 10), "white")
        d = ImageDraw.Draw(sheet)
        for i, (t, im) in enumerate(chunk):
            x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 44)
            sheet.paste(im.convert("RGB").resize((tw, th)), (x, y + 34))
            d.text((x, y), f"t = {t:.1f} s", font=font, fill=(200, 30, 30))
        out = BUILD / f"{video.stem}_sheet_{k // per_sheet + 1}.png"
        sheet.save(out)
        print(out)
    print(f"{video.name}: {total:.2f} s, {len(times)} frames sampled")


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 5.0)
