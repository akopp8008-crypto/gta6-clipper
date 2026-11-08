"""Raw signals pulled from a gameplay video, one value per time window.

Every function returns a numpy array with one value per window of
``window`` seconds, so the scorer can line them up and add them.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16_000


def probe_duration(video: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", video],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def n_windows(duration: float, window: float) -> int:
    return max(1, int(np.ceil(duration / window)))


def extract_audio(video: str, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Decode the audio track to mono float32 in [-1, 1]."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(sr),
         "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def robust_z(x: np.ndarray) -> np.ndarray:
    """How unusual each value is versus the whole video (median/MAD z-score)."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    med = np.median(x)
    mad = np.median(np.abs(x - med)) * 1.4826
    if mad < 1e-9:
        mad = np.std(x) or 1.0
    return (x - med) / mad


def audio_loudness(samples: np.ndarray, window: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Loudness (dB RMS) per window. Screams, crashes and explosions spike here."""
    hop = int(window * sr)
    count = max(1, int(np.ceil(len(samples) / hop)))
    out = np.full(count, -90.0)
    for i in range(count):
        chunk = samples[i * hop:(i + 1) * hop]
        if chunk.size:
            rms = np.sqrt(np.mean(chunk.astype(np.float64) ** 2))
            out[i] = 20 * np.log10(max(rms, 1e-5))
    return out


def vs_baseline(values: np.ndarray, window: float, baseline_s: float = 120.0) -> np.ndarray:
    """Loudness compared with the streamer's *normal level* around that moment.

    A shout stands out even in a loud game, and calm talk in a quiet intro
    does not (idea from kiy0ni/auto-video-editor).
    """
    half = max(1, int(baseline_s / window / 2))
    out = np.empty_like(values, dtype=float)
    for i in range(len(values)):
        out[i] = values[i] - np.median(values[max(0, i - half): i + half + 1])
    return out


def audio_rise(loudness: np.ndarray) -> np.ndarray:
    """Jump in loudness versus the previous window: sudden events beat steady noise."""
    if loudness.size == 0:
        return loudness
    prev = np.concatenate([[loudness[0]], loudness[:-1]])
    return np.clip(loudness - prev, 0, None)


_SCENE_RE = re.compile(r"pts_time:([\d.]+).*?lavfi\.scene_score=([\d.]+)", re.S)


def scene_motion(video: str, window: float, duration: float, fps: int = 4) -> np.ndarray:
    """Biggest scene-change score per window (crashes, explosions, hard cuts)."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-an",
         "-vf", f"fps={fps},scale=320:-2,select='gte(scene,0)',metadata=print:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    out = np.zeros(n_windows(duration, window))
    text = proc.stdout
    # metadata=print writes "frame:N pts:.. pts_time:T" then "lavfi.scene_score=S"
    for block in text.split("frame:")[1:]:
        m = _SCENE_RE.search(block)
        if m:
            t, s = float(m.group(1)), float(m.group(2))
            i = min(int(t // window), len(out) - 1)
            out[i] = max(out[i], s)
    return out


_CROP_RE = re.compile(r"\bt:([\d.]+).*?crop=(\d+):(\d+):(\d+):(\d+)")


def letterbox_ratio(video: str, window: float, duration: float) -> np.ndarray:
    """Share of the frame height that is black bars, per window.

    GTA story cutscenes play letterboxed. Rockstar takes down standalone
    cutscenes, so windows with big bars get blocked by the filters.
    """
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", video, "-an",
         "-vf", "fps=1,cropdetect=limit=24:round=2:reset=1", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    height = None
    hm = re.search(r"Stream .*Video:.*?, (\d{2,5})x(\d{2,5})", proc.stderr)
    if hm:
        height = int(hm.group(2))
    out = np.zeros(n_windows(duration, window))
    if not height:
        return out
    for m in _CROP_RE.finditer(proc.stderr):
        t, h = float(m.group(1)), int(m.group(3))
        i = min(int(t // window), len(out) - 1)
        out[i] = max(out[i], 1 - h / height)
    return out


@dataclass
class Segment:
    start: float
    end: float
    text: str


# Words people say (or type) when something funny or crazy happens.
REACTION_WORDS = {
    "no way": 3, "bro": 2, "what": 1.5, "wait": 1.5, "oh my god": 3, "omg": 3,
    "run": 1.5, "go go go": 2, "watch this": 2.5, "nah": 2, "yo": 1,
    "why": 1.5, "how": 1.5, "help": 2, "cops": 1.5, "police": 1.5,
    "stars": 1.5, "wasted": 3, "busted": 3, "i'm dead": 3, "lmao": 3,
    "haha": 2, "hahaha": 3, "dude": 1.5, "insane": 2.5, "crazy": 2,
}


def keyword_score(text: str, words: dict[str, float] = REACTION_WORDS) -> float:
    t = " " + re.sub(r"[^a-z' ]", " ", text.lower()) + " "
    return sum(w * t.count(f" {k} ") for k, w in words.items())


def transcript_signal(segments: list[Segment], window: float, duration: float) -> np.ndarray:
    out = np.zeros(n_windows(duration, window))
    for seg in segments:
        i = min(int(seg.start // window), len(out) - 1)
        out[i] += keyword_score(seg.text)
    return out


CHAT_EMOTES = {"lmao": 2, "lol": 1, "kekw": 2, "omegalul": 2, "lul": 1,
               "pog": 1.5, "poggers": 1.5, "clip": 3, "clip it": 4, "w": 0.5,
               "wtf": 2, "no way": 2, "?": 0.5, "💀": 2, "😂": 2}


def chat_signal(messages: list[tuple[float, str]], window: float, duration: float) -> np.ndarray:
    """Chat speed plus 'clip it' / laughing emotes per window."""
    out = np.zeros(n_windows(duration, window))
    for t, msg in messages:
        i = min(int(t // window), len(out) - 1)
        low = msg.lower()
        bonus = sum(w for k, w in CHAT_EMOTES.items() if k in low.split() or (len(k) > 2 and k in low))
        out[i] += 1 + bonus
    return out
