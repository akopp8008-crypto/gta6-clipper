"""Read transcripts and chat logs, or make a transcript with Whisper."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .signals import Segment

_TS = r"(\d+):(\d{2}):(\d{2})(?:[.,](\d+))?"


def _secs(h, m, s, frac) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + (float("0." + frac) if frac else 0.0)


def read_srt(path: str) -> list[Segment]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    segs = []
    for block in re.split(r"\n\s*\n", text.strip()):
        m = re.search(_TS + r"\s*-->\s*" + _TS, block)
        if not m:
            continue
        g = m.groups()
        lines = block[m.end():].strip()
        segs.append(Segment(_secs(*g[:4]), _secs(*g[4:]), " ".join(lines.splitlines())))
    return segs


def read_chat(path: str) -> list[tuple[float, str]]:
    """Chat log in either format:

    * text lines: ``[01:02:03] user: message`` (TwitchDownloader / most tools)
    * JSON list of ``{"t": seconds, "text": "..."}``
    """
    p = Path(path)
    if p.suffix == ".json":
        return [(float(m["t"]), str(m["text"])) for m in json.loads(p.read_text())]
    out = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*\[" + _TS + r"\]\s*[^:]*:\s*(.*)", line)
        if m:
            g = m.groups()
            out.append((_secs(*g[:4]), g[4]))
    return out


# Names and jargon Whisper would otherwise mishear.
GTA_VOCAB = ("GTA 6, Grand Theft Auto, Vice City, Leonida, Lucia, Jason, Port Gellhorn, Ambrosia, "
             "wanted level, six stars, cops, SWAT, heist, Bleeter, NPC, gator, bayou, Keys")


def transcribe(video: str, model: str = "small") -> list[Segment]:
    """Speech to text with word timing, using faster-whisper if installed."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # pragma: no cover - optional dependency
        raise RuntimeError("Install faster-whisper for transcripts: pip install faster-whisper") from e
    wm = WhisperModel(model, compute_type="int8")
    segments, _ = wm.transcribe(video, vad_filter=True, initial_prompt=GTA_VOCAB, word_timestamps=True)
    return [Segment(s.start, s.end, s.text.strip(),
                    [(w.start, w.end, w.word.strip()) for w in (s.words or []) if w.word.strip()] or None)
            for s in segments]
