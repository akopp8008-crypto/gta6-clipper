"""Turn signals into ranked clip candidates ("moments")."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
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
    ai_hook: str | None = None   # hook suggested by the AI ranker
    ai_reason: str | None = None # why the AI ranker liked it
    cut: str = "auto"            # "punch" (8-15 s), "story" (50-75 s) or "auto"

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


def find_peaks(score: np.ndarray, min_gap: int, threshold: float,
               spread: int | None = None, per_spread: int = 2) -> list[int]:
    """Best peaks first, at least ``min_gap`` windows apart, and at most
    ``per_spread`` peaks inside any ``spread``-window stretch so clips come
    from the whole stream, not one wild minute."""
    order = np.argsort(score)[::-1]
    chosen: list[int] = []
    for i in order:
        if score[i] < threshold:
            break
        if not all(abs(i - j) >= min_gap for j in chosen):
            continue
        if spread and sum(abs(i - j) < spread for j in chosen) >= per_spread:
            continue
        chosen.append(int(i))
    return chosen


def snap(start: float, end: float, segments: list[sig.Segment] | None,
         loud: np.ndarray | None, window: float, reach: float = 3.0) -> tuple[float, float]:
    """Move cuts so they never land mid-sentence (or, without a transcript,
    land on the quietest nearby moment)."""
    if segments:
        for seg in segments:
            if seg.start < start < seg.end and start - seg.start <= reach:
                start = seg.start
            if seg.start < end < seg.end and seg.end - end <= reach:
                end = seg.end
        return start, end
    if loud is not None and len(loud):
        def quiet(t, lo, hi):
            i0, i1 = max(0, int((t + lo) // window)), min(len(loud), int((t + hi) // window) + 1)
            if i1 <= i0:
                return t
            k = i0 + int(np.argmin(loud[i0:i1]))
            return k * window
        start = min(start, quiet(start, -reach, 0.01))
        end = max(end, quiet(end, 0, reach) + window)
    return start, end


def shape_cut(m: Moment, cut: str, segments: list[sig.Segment] | None = None,
              duration: float | None = None) -> Moment:
    """Re-cut a moment to one of the lengths that win (see playbook.CUTS).

    The payoff and reaction (peak -> m.end) are always kept; only the setup in
    front of it grows or shrinks. Mid-length clips (16-45 s) lose on Shorts, so
    a punch cut gets tighter and a story cut gets the whole run-up.
    """
    from .playbook import CUTS
    if cut not in CUTS:
        return replace(m, cut="auto")
    lo, hi = CUTS[cut]
    # Punch keeps 1-2 s of reaction after the payoff, not a long tail.
    end = min(m.end, m.peak + 6.0) if cut == "punch" else m.end + 1.5
    if duration is not None:
        end = min(end, duration)
    # Punch: the setup line (~6 s) before the peak. Story: ~45 s of run-up.
    start = m.peak - (6.0 if cut == "punch" else 45.0)
    start = min(start, end - lo)                 # long enough
    start = max(start, end - hi)                 # not too long
    if "graphic" in m.kind:                      # keep violence past second 8 (YouTube ads)
        start = min(start, m.peak - 8.5)
    start = max(0.0, start)
    start, end2 = snap(start, end, segments, None, 2.0)
    if end2 - start > hi + 2:                    # snapping must not blow the budget
        start, end2 = max(0.0, end - hi), end
    if duration is not None:
        end2 = min(end2, duration)
    return replace(m, start=round(start, 2), end=round(end2, 2), cut=cut)


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
    segments: list[sig.Segment] | None = None,
    raw_loudness: np.ndarray | None = None,
    spread_s: float = 300.0,
) -> list[Moment]:
    weights = weights or DEFAULT_WEIGHTS
    score = combine(features, weights)
    peaks = find_peaks(score, max(1, int(min_gap_s / window)), threshold,
                       spread=int(spread_s / window))[:max_clips]
    moments = []
    for i in peaks:
        peak_t = (i + 0.5) * window
        # Let the reaction finish: extend while the next window is still hot.
        j = i
        while j + 1 < len(score) and score[j + 1] > threshold * 0.6 and (j - i) * window < 15:
            j += 1
        start, end = snap(i * window - pre, (j + 1) * window + post, segments, raw_loudness, window)
        start, end = max(0.0, start), min(duration, end)
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
        "loudness": sig.vs_baseline(loud, window),
        "rise": sig.audio_rise(loud),
        "motion": sig.scene_motion(video, window, duration),
    }
    if transcript:
        features["words"] = sig.transcript_signal(transcript, window, duration)
    if chat:
        features["chat"] = sig.chat_signal(chat, window, duration)
    features["letterbox"] = sig.letterbox_ratio(video, window, duration)
    scoring = {k: v for k, v in features.items() if k != "letterbox"}
    moments = build_moments(scoring, window, duration, weights, segments=transcript,
                            raw_loudness=loud, **kw)
    return moments, features, duration
