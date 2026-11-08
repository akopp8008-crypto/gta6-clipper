"""Safety rules that keep accounts alive.

* Rockstar removes standalone story cutscenes, endings and leaks
  ("Policy on posting copyrighted Rockstar Games material").
* Any GTA 6 footage from before launch (Nov 19, 2026) is a leak.
* YouTube: graphic game violence can only earn ads from about second 8.
* Only footage from sources we have permission for (own gameplay,
  clip campaigns, streamers who publicly allow clipping).
"""
from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .score import Moment
from .signals import Segment, keyword_score

GTA6_LAUNCH = dt.date(2026, 11, 19)
LETTERBOX_LIMIT = 0.15       # 15% of the frame height in black bars = cutscene
GRAPHIC_SAFE_SECOND = 8.0    # YouTube: graphic violence only after this point

KIND_WORDS = {
    "cop_escalation": ["cops", "police", "stars", "swat", "helicopter", "busted", "five stars", "six stars"],
    "chaos_fail": ["wasted", "crash", "flip", "fell", "dead", "ragdoll", "oops", "bro"],
    "npc_weirdness": ["npc", "lady", "guy", "florida", "why is he", "what is she"],
    "first_reaction": ["first time", "look at", "beautiful", "graphics", "vice city", "the map"],
    "insane_skill": ["clean", "perfect", "clutch", "lets go", "let's go", "escaped", "made it"],
    "wildlife": ["gator", "alligator", "swamp", "shark"],
}
GRAPHIC_WORDS = ["headshot", "blood", "decapitate", "chainsaw", "gore", "massacre"]


@dataclass
class Source:
    name: str
    kind: str                     # own | campaign | public_permission
    proof: str = ""               # link or screenshot path showing permission
    credit: str = ""              # @handle to tag in every post
    platforms: list[str] = field(default_factory=lambda: ["youtube", "tiktok", "instagram"])


def load_sources(path: str = "sources.toml") -> dict[str, Source]:
    if not Path(path).exists():
        return {}
    data = tomllib.loads(Path(path).read_text())
    return {name: Source(name=name, **cfg) for name, cfg in data.get("source", {}).items()}


def check_source(name: str, sources: dict[str, Source]) -> Source:
    """Refuse to clip anyone who is not on the permission list."""
    src = sources.get(name)
    if src is None:
        raise PermissionError(
            f"'{name}' is not in sources.toml. Add them only with permission: "
            "your own footage, a clip campaign, or a public 'clip me' statement (save the proof)."
        )
    if src.kind != "own" and not src.proof:
        raise PermissionError(f"'{name}' has no permission proof saved in sources.toml.")
    return src


def check_recorded_date(recorded: dt.date | None, game: str = "gta6") -> None:
    if game == "gta6" and recorded is not None and recorded < GTA6_LAUNCH:
        raise PermissionError("GTA 6 footage from before Nov 19, 2026 is a leak. Rockstar removes it.")


def words_in(transcript: list[Segment] | None, start: float, end: float) -> str:
    if not transcript:
        return ""
    return " ".join(s.text for s in transcript if s.end >= start and s.start <= end).lower()


def classify(m: Moment, text: str) -> str:
    best, best_hits = "chaos_fail", 0
    for kind, words in KIND_WORDS.items():
        hits = sum(text.count(w) for w in words)
        if hits > best_hits:
            best, best_hits = kind, hits
    if best_hits == 0 and m.signals.get("chat", 0) > 0:
        return "chat_moment"
    return best


def apply(
    moments: list[Moment],
    features: dict[str, np.ndarray],
    window: float,
    transcript: list[Segment] | None = None,
) -> list[Moment]:
    """Label each moment, block cutscenes, and fix graphic-violence timing."""
    bars = features.get("letterbox", np.zeros(0))
    for m in moments:
        text = words_in(transcript, m.start, m.end)
        m.kind = classify(m, text)
        i0, i1 = int(m.start // window), int(np.ceil(m.end / window))
        span = bars[i0:i1]
        if span.size and np.mean(span > LETTERBOX_LIMIT) > 0.5:
            m.blocked = "looks like a story cutscene (letterboxed); Rockstar removes these"
            continue
        if any(w in text for w in GRAPHIC_WORDS):
            m.kind += "+graphic"
            # Push the in-point back so the graphic part lands after second 8.
            need = m.peak - GRAPHIC_SAFE_SECOND
            if need < m.start:
                m.start = max(0.0, round(need, 2))
            if m.peak - m.start < GRAPHIC_SAFE_SECOND:
                m.blocked = "graphic violence in the first 7 seconds loses YouTube ads"
    return moments


__all__ = ["apply", "check_source", "check_recorded_date", "load_sources", "Source", "keyword_score"]
