"""Shared timeline: scene durations and absolute narration/subtitle cues, derived from the TTS durations."""

from __future__ import annotations

import json
from pathlib import Path

from storyboard import INTRO_S, OUTRO_S, SCENES

BUILD = Path(__file__).resolve().parents[2] / ".video-build"
LEAD, GAP, TAIL = 0.5, 0.25, 0.7  # silence before the first sentence, between sentences, after the last
MIN_SCENE = {"explorer": 11.0}  # the graph needs time to be looked at
LEAD_SCENE = {"recall": 2.0}  # recall: typing the lot + tracing happen before the first sentence


def timings(lang: str) -> dict:
    return json.loads((BUILD / lang / "timings.json").read_text(encoding="utf-8"))


def scene_durations(lang: str) -> dict[str, float]:
    t = timings(lang)
    out = {}
    for s in SCENES:
        d = LEAD_SCENE.get(s, LEAD) + sum(x["duration"] for x in t[s]) + GAP * (len(t[s]) - 1) + TAIL
        out[s] = round(max(d, MIN_SCENE.get(s, 0.0)), 2)
    return out


def sentence_starts(lang: str, scene: str) -> list[float]:
    """Start of each sentence relative to the scene start."""
    starts, cur = [], LEAD_SCENE.get(scene, LEAD)
    for x in timings(lang)[scene]:
        starts.append(round(cur, 3))
        cur += x["duration"] + GAP
    return starts


def cues(lang: str) -> list[dict]:
    """Absolute cues for the whole video: {start, end, audio, subtitle}."""
    t, durs = timings(lang), scene_durations(lang)
    out, offset = [], INTRO_S
    for s in SCENES:
        for x, st in zip(t[s], sentence_starts(lang, s), strict=True):
            out.append(
                {
                    "scene": s,
                    "start": round(offset + st, 3),
                    "end": round(offset + st + x["duration"], 3),
                    "audio": x["file"],
                    "subtitle": x["subtitle"],
                }
            )
        offset += durs[s]
    for x in t["outro"]:  # outro narration, no subtitle (the card already shows the links)
        out.append(
            {
                "scene": "outro",
                "start": round(offset + 0.3, 3),
                "end": round(offset + 0.3 + x["duration"], 3),
                "audio": x["file"],
                "subtitle": x["subtitle"],
            }
        )
    return out


def total_duration(lang: str) -> float:
    return round(INTRO_S + sum(scene_durations(lang).values()) + OUTRO_S, 2)
