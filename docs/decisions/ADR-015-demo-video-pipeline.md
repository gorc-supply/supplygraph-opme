# ADR-015: A scripted, reproducible demo video (Playwright + edge-tts + ffmpeg)

- Status: accepted
- Date: 2026-11-25

**Context.** The portfolio needs a ~90 s demo video (PT and EN, 16:9 and a 4:5 feed cut), produced with free tools
only and without a manual screen recording. It must show the real published app, with the numbers of the README,
and must never show credentials, terminals or personal data.

**Decision.**
- **Recording** (`scripts/video/record.py`): Playwright + headless Chromium records the *published* demo, at its
  inner URL (`supplygraph-opme.streamlit.app/~/+/`), so the Streamlit Cloud frame and the account avatar never
  appear. Before recording, the app is woken up and every page is visited once (no cold start on camera). Each scene
  is recorded separately and checked: the expected numbers must be on screen and no error, spinner or skeleton may be
  visible, otherwise only that scene is re-recorded.
- **Legibility:** viewport 1440×720 CSS px at device scale 4/3, captured through the Chromium screencast (CDP
  `Page.startScreencast`) at 1920×960 physical px; Playwright's built-in video ignores the device scale and made text
  too small. The bottom 120 px of the 1080p frame are a dark band for subtitles, so captions never cover the app.
- **Cursor:** headless Chromium draws no cursor; an injected one moves with ease-in-out to real element positions
  (bar of a Plotly chart, metric, slider handle), with a click ripple.
- **Narration** (`scripts/video/narration.py`): edge-tts, `pt-BR-AntonioNeural` (+10%) and `en-US-AndrewNeural`
  (+4%), one MP3 per sentence. Sentence durations drive the timeline (`timeline.py`), so the subtitles, the `.srt`
  files and the voice share the same cue times by construction.
- **Editing** (`scripts/video/build.py`): ffmpeg from `imageio-ffmpeg` (pip, no admin rights). Intro (3 s) and outro
  (4 s) cards and caption boxes are drawn with Pillow. Output H.264 CRF 23 `veryfast` + AAC, `+faststart`. The
  captioned picture and the audio are rendered in separate passes and then muxed with the video copied: in a single
  pass with the looped caption PNGs, ffmpeg shifted the narration ~0.5 s early. Measured sync after the fix: speech
  starts 0.1-0.3 s after its caption (the TTS clips' leading silence).
- **Honesty on screen:** the hosted demo runs on AuraDB Free over the network, so the recall shows ~0.7-0.9 s query
  time; the narration says "in under a second", and the README keeps the 19 ms measured locally.
- **Verification** (`scripts/video/verify.py`): contact sheets with one frame every 5 s for each rendered video,
  reviewed for errors, spinners, legibility, numbers and any secret, terminal or personal data.
- **Distribution:** MP4s are GitHub Release assets (`v1.0-demo`), not Git history; only the GIF, the poster and the
  `.srt` files are versioned. The toolchain lives in its own venv (`scripts/video/requirements.txt`), not in the app
  or project dependencies.

**Rejected.** Manual screen recording (not reproducible); recording the local app (the published one is what the
viewer will open); Playwright's built-in video (low resolution); subtitles overlaid on the app area (they hid
numbers); MP4s in Git or Git LFS (repo weight, LFS quota).

**Consequences.** The whole video can be rebuilt after an app change with four commands (see
`docs/portfolio/video-script-90s.md`). It depends on the public demo being up and on edge-tts (an unofficial client
of a free Microsoft service); if edge-tts stops working, the silent versions with burned-in subtitles still build.
