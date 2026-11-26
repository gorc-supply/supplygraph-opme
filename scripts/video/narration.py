"""Generate the narration with edge-tts: one MP3 per sentence (exact durations -> exact subtitle timing).

Usage: python scripts/video/narration.py [pt|en]   -> .video-build/<lang>/tts/*.mp3 + timings.json
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).parent))
from storyboard import NARRATION, RATES, VOICES  # noqa: E402

BUILD = Path(__file__).resolve().parents[2] / ".video-build"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def media_duration(path: Path) -> float:
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def synth(text: str, voice: str, rate: str, out: Path) -> None:
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(str(out))
            if out.stat().st_size > 1000:
                return
        except Exception as e:  # noqa: BLE001 - network hiccups: retry
            print(f"  retry {attempt + 1} ({type(e).__name__})")
            await asyncio.sleep(2 + attempt * 2)
    raise RuntimeError(f"edge-tts failed for: {text[:40]}")


async def main(lang: str) -> None:
    out_dir = BUILD / lang / "tts"
    out_dir.mkdir(parents=True, exist_ok=True)
    timings: dict[str, list[dict]] = {}
    for scene, sentences in NARRATION[lang].items():
        timings[scene] = []
        for i, (speech, subtitle) in enumerate(sentences):
            mp3 = out_dir / f"{scene}_{i}.mp3"
            await synth(speech, VOICES[lang], RATES[lang], mp3)
            d = media_duration(mp3)
            timings[scene].append({"file": mp3.name, "duration": round(d, 3), "subtitle": subtitle})
            print(f"{lang} {scene}[{i}] {d:5.2f}s  {subtitle or ''}")
    (BUILD / lang / "timings.json").write_text(
        json.dumps(timings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "pt"))
