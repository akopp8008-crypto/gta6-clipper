"""Optional second opinion from Claude on each candidate clip.

The signal scorer is good at "something loud happened". It can't tell a
funny moment from a boring loud one. Claude reads what was said around
each candidate and returns a viral score, a hook and a one-line reason
(the approach the top talk clippers on GitHub use).

Needs ANTHROPIC_API_KEY. Only transcript text and signal numbers are sent,
never video or audio.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .score import Moment
from .signals import Segment

MODEL = os.environ.get("CLIPPER_AI_MODEL", "claude-sonnet-5-5")

PROMPT = """You pick GTA 6 gameplay clips for TikTok, YouTube Shorts and Instagram Reels.
Funny or viral GTA clips: setup -> sudden chaos (crash, ragdoll, cops escalating, weird NPC) -> a real
reaction. Clips that need story context, or are story cutscenes, are bad.

For each candidate below you get its id, the moment type our detector guessed, the signal scores
(higher = louder / more chat / more motion) and what was said.

Return ONLY a JSON list, one object per candidate:
[{{"id": <id>, "viral": <0-10>, "hook": "<3-6 word on-screen hook>", "reason": "<one short sentence>"}}]

Candidates:
{items}"""


def _text_around(segments: list[Segment] | None, m: Moment) -> str:
    if not segments:
        return "(no transcript)"
    t = " ".join(s.text for s in segments if s.end >= m.start and s.start <= m.end)
    return t[:600] or "(silence)"


def rank(moments: list[Moment], segments: list[Segment] | None, weight: float = 0.5) -> list[Moment]:
    """Blend Claude's 0-10 viral score into each moment's score and attach hook + reason."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    live = [m for m in moments if not m.blocked]
    if not key or not live:
        return moments
    items = "\n".join(
        json.dumps({"id": i, "type": m.kind, "signals": m.signals, "said": _text_around(segments, m)})
        for i, m in enumerate(live)
    )
    body = json.dumps({
        "model": MODEL, "max_tokens": 2000,
        "messages": [{"role": "user", "content": PROMPT.format(items=items)}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        reply = json.loads(r.read())
    text = "".join(b.get("text", "") for b in reply.get("content", []))
    picks = parse(text)
    for p in picks:
        i = p.get("id")
        if isinstance(i, int) and 0 <= i < len(live):
            m = live[i]
            v = float(p.get("viral", 5))
            m.score = round(m.score * (1 - weight) + v * weight, 3)
            m.signals["ai_viral"] = v
            m.ai_hook = str(p.get("hook", ""))[:60] or None
            m.ai_reason = str(p.get("reason", ""))[:200] or None
    moments.sort(key=lambda m: (m.blocked is None, m.score), reverse=True)
    return moments


def parse(text: str) -> list[dict]:
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)]
