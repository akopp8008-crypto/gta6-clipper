"""The clipping playbook as code: targets every clip should hit, plus a checker.

Numbers come from research/Clipping playbook.md (in the project files). Most are
rules of thumb from creator blogs and our own YouTube research run, not official
platform specs, so `tune` and our own view counts get the final say.

    python -m clipper check clip.mp4 [more.mp4 ...]
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field

W, H = 1080, 1920

# Where the apps draw buttons, names and captions over the video (1080x1920).
# Union of TikTok, Reels and Shorts, rounded up. Text and faces stay inside.
SAFE = {"top": 220, "bottom": 480, "left": 90, "right": 150}

# Our 186-Short GTA sample (2026-11-08): under 15 s and over 60 s win, 16-45 s loses.
CUTS = {
    "punch": (8.0, 15.0),    # one beat: setup line -> payoff -> reaction
    "story": (50.0, 75.0),   # one whole story with a payoff at the end
}
DEAD_ZONE = (16.0, 45.0)
MAX_SECONDS = 180.0          # Shorts and Reels cap; TikTok Creator Rewards needs 60 s+

TARGET_LUFS = -14.0          # what the apps normalise to; quieter clips sound weak
HASHTAGS_MAX = 5             # 3-5; more dilutes what the app thinks the clip is about
TITLE_WORDS_MAX = 9          # median for top GTA Shorts in our sample

# Local-time posting windows (gaming, weak evidence). Consistency beats the exact minute.
POST_WINDOWS = {
    "tiktok": "Tue-Thu 7-10 PM, weekends 9 AM",
    "youtube": "weekdays 2-4 PM, Fri-Sat 4-7 PM",
    "instagram": "weekdays 11 AM-1 PM or 6 PM",
}
# Our research run: top GTA Shorts most often went up at these UTC hours.
YOUTUBE_TOP_HOURS_UTC = (17, 0, 5)


def cut_type(seconds: float) -> str:
    for name, (lo, hi) in CUTS.items():
        if lo <= seconds < hi + 1:               # a few frames over still counts
            return name
    if DEAD_ZONE[0] <= seconds <= DEAD_ZONE[1] + 1:
        return "dead-zone"
    return "other"


@dataclass
class Report:
    path: str
    seconds: float = 0.0
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def text(self) -> str:
        head = f"{'OK  ' if self.ok else 'FIX '} {self.path}  ({self.seconds:.1f}s, {cut_type(self.seconds)})"
        return "\n".join([head] + [f"   ✗ {i}" for i in self.issues] + [f"   · {n}" for n in self.notes])


def _probe(path: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _loudness(path: str) -> float | None:
    """Integrated loudness (LUFS) of the whole clip."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
                        "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", p.stderr)
    return float(m[-1]) if m else None


def _frame_brightness(path: str, t: float) -> float | None:
    """Average luma (0-255) of the frame at t seconds."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-v", "info", "-ss", f"{max(0.0, t):.2f}", "-i", path,
                        "-frames:v", "1", "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"YAVG=(\d+(?:\.\d+)?)", p.stderr)
    return float(m.group(1)) if m else None


def _frame_diff(path: str, a: float, b: float) -> float | None:
    """How different two frames are (0 = identical, ~1 = totally different). Catches freeze frames."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-ss", f"{max(0.0, a):.2f}", "-i", path,
                        "-ss", f"{max(0.0, b):.2f}", "-i", path, "-filter_complex",
                        "[0:v]trim=end_frame=1,scale=270:480[x];[1:v]trim=end_frame=1,scale=270:480[y];"
                        "[x][y]ssim=stats_file=-", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"All:(\d+(?:\.\d+)?)", p.stdout + p.stderr)
    return 1 - float(m.group(1)) if m else None


def check(path: str) -> Report:
    """Check one finished clip against the playbook."""
    r = Report(path)
    info = _probe(path)
    r.seconds = float(info.get("format", {}).get("duration", 0))
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))

    if (v.get("width"), v.get("height")) != (W, H):
        r.issues.append(f"size is {v.get('width')}x{v.get('height')}, needs {W}x{H} (9:16)")
    num, _, den = (v.get("r_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den or 1)
    if fps < 23:
        r.issues.append(f"{fps:.0f} fps looks choppy; use the source rate (24/30/60)")

    kind = cut_type(r.seconds)
    if kind == "dead-zone":
        r.issues.append(f"{r.seconds:.0f}s sits in the 16-45 s dead zone; trim to 8-15 s or grow to 50-75 s")
    elif kind == "other" and r.seconds < CUTS["punch"][0]:
        r.notes.append("under 8 s: fine for a loop, but make sure the setup is still there")
    elif r.seconds > MAX_SECONDS:
        r.issues.append("over 3 minutes: Shorts and Reels treat it as a normal video")
    if r.seconds >= 60:
        r.notes.append("60 s+: eligible for TikTok Creator Rewards")

    first = _frame_brightness(path, 0.0)
    if first is not None and first < 18:
        r.issues.append("first frame is (nearly) black; open on action, never a fade from black")
    if r.seconds > 2:
        d = _frame_diff(path, r.seconds - 1.6, r.seconds - 0.1)
        if d is not None and d < 0.004:
            r.issues.append("last 1.5 s look frozen; end on moving footage (a real reaction)")

    if not has_audio:
        r.issues.append("no audio track")
    else:
        lufs = _loudness(path)
        if lufs is not None:
            if lufs < TARGET_LUFS - 4:
                r.issues.append(f"too quiet ({lufs:.1f} LUFS); normalise to about {TARGET_LUFS:.0f}")
            elif lufs > TARGET_LUFS + 3:
                r.issues.append(f"too loud ({lufs:.1f} LUFS); normalise to about {TARGET_LUFS:.0f}")
            else:
                r.notes.append(f"loudness {lufs:.1f} LUFS")
    return r


def check_text(title: str = "", caption: str = "") -> list[str]:
    """Lint a title or caption against the playbook."""
    issues = []
    if title:
        if len(title.split()) > TITLE_WORDS_MAX + 3:
            issues.append(f"title has {len(title.split())} words; top GTA Shorts use about {TITLE_WORDS_MAX}")
        if title.rstrip().endswith("?"):
            issues.append("title is a question; questions underperformed in our GTA sample, use a statement or POV")
    text = f"{title} {caption}"
    tags = re.findall(r"#\w+", text)
    if len(tags) > HASHTAGS_MAX:
        issues.append(f"{len(tags)} hashtags; keep 3-{HASHTAGS_MAX}")
    if any(t.lower() in ("#fyp", "#foryou", "#viral") for t in tags):
        issues.append("#fyp/#viral tell the app nothing about the clip; use topic tags")
    return issues
