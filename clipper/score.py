"""Turn signals into ranked clip candidates ("moments")."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import signals as sig

DEFAULT_WEIGHTS = {
    "loudness": 1.0,   # how loud versus the rest of the video
    "rise": 1.0,       # sudden jump in loudness
    "motion": 0.8,     # scene change / crash
    "words": 1.2,      # reaction words in the transcript
    "chat": 1.5,       # chat speed and "clip it" emotes
}


@dataclass
class Moment:
    start: float
    end: float
    peak: float
    score: float
    signals: dict[str, float] = field(default_factory=dict)
    kind: str = "chaos"
    blocked: str | None = None   # reason the safety filters refused it

    def to_dict(self):
        return asdict(self)


def load_weights(path: str | None) -> dict[str, float]:
    w = dict(DEFAULT_WEIGHTS)
    if path and Path(path).exists():
        w.update(json.loads(Path(path).read_text()))
    return w


def combine(features: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    """Weighted sum of z-scored signals; agreement between signals adds a bonus."""
    n = max(len(v) for v in features.values())
    total = np.zeros(n)
    agree = np.zeros(n)
    for name, values in features.items():
        v = np.zeros(n)
        v[: len(values)] = values
        if not np.any(v):
            continue
        z = np.clip(sig.robust_z(v), -3, 6)
        total += weights.get(name, 0.0) * z
        agree += z > 1.5
    # Two signals spiking together is much more reliable than one.
    return total + 0.75 * np.clip(agree - 1, 0, None)


def find_peaks(score: np.ndarray, min_gap: int, threshold: float) -> list[int]:
    order = np.argsort(score)[::-1]
    chosen: list[int] = []
    for i in order:
        if score[i] < threshold:
            break
        if all(abs(i - j) >= min_gap for j in chosen):
            chosen.append(int(i))
    return chosen


def build_moments(
    features: dict[str, np.ndarray],
    window: float,
    duration: float,
    weights: dict[str, float] | None = None,
    pre: float = 5.0,
    post: float = 3.0,
    min_gap_s: float = 12.0,
    threshold: float = 2.0,
    max_clips: int = 20,
) -> list[Moment]:
    weights = weights or DEFAULT_WEIGHTS
    score = combine(features, weights)
    peaks = find_peaks(score, max(1, int(min_gap_s / window)), threshold)[:max_clips]
    moments = []
    for i in peaks:
        peak_t = (i + 0.5) * window
        # Let the reaction finish: extend while the next window is still hot.
        j = i
        while j + 1 < len(score) and score[j + 1] > threshold * 0.6 and (j - i) * window < 15:
            j += 1
        start = max(0.0, i * window - pre)
        end = min(duration, (j + 1) * window + post)
        moments.append(Moment(
            start=round(start, 2), end=round(end, 2), peak=round(peak_t, 2),
            score=round(float(score[i]), 3),
            signals={k: round(float(v[i]) if i < len(v) else 0.0, 3) for k, v in features.items()},
        ))
    return moments


def analyze(
    video: str,
    window: float = 2.0,
    transcript: list[sig.Segment] | None = None,
    chat: list[tuple[float, str]] | None = None,
    weights: dict[str, float] | None = None,
    **kw,
) -> tuple[list[Moment], dict[str, np.ndarray], float]:
    duration = sig.probe_duration(video)
    audio = sig.extract_audio(video)
    loud = sig.audio_loudness(audio, window)
    features = {
        "loudness": loud,
        "rise": sig.audio_rise(loud),
        "motion": sig.scene_motion(video, window, duration),
    }
    if transcript:
        features["words"] = sig.transcript_signal(transcript, window, duration)
    if chat:
        features["chat"] = sig.chat_signal(chat, window, duration)
    features["letterbox"] = sig.letterbox_ratio(video, window, duration)
    scoring = {k: v for k, v in features.items() if k != "letterbox"}
    moments = build_moments(scoring, window, duration, weights, **kw)
    return moments, features, duration
