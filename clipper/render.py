"""Cut a moment into a 1080x1920 vertical clip with a hook and captions."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .score import Moment
from .signals import Segment

W, H = 1080, 1920

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,3,6,0,8,60,60,260,1
Style: Cap,DejaVu Sans,72,&H0000F0FF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,7,2,2,60,60,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def caption_chunks(segments: list[Segment], start: float, end: float, words_per: int = 3):
    """Split speech into 2-3 word pop-up captions (word-synced beats block text)."""
    for seg in segments:
        if seg.end < start or seg.start > end:
            continue
        words = seg.text.split()
        if not words:
            continue
        step = (seg.end - seg.start) / max(1, len(words))
        for k in range(0, len(words), words_per):
            a = seg.start + k * step
            b = min(seg.end, a + step * words_per)
            if b < start or a > end:
                continue
            yield max(a, start) - start, min(b, end) - start, " ".join(words[k:k + words_per]).upper()


def build_ass(hook: str, duration: float, segments: list[Segment] | None,
              start: float, end: float, hook_seconds: float | None = None) -> str:
    lines = [ASS_HEADER]
    hook_end = duration if hook_seconds is None else min(duration, hook_seconds)
    lines.append(f"Dialogue: 1,{_ts(0)},{_ts(hook_end)},Hook,,0,0,0,,{_esc(hook)}\n")
    for a, b, txt in caption_chunks(segments or [], start, end):
        lines.append(f"Dialogue: 0,{_ts(a)},{_ts(b)},Cap,,0,0,0,,{_esc(txt)}\n")
    return "".join(lines)


def render(video: str, m: Moment, out: str, hook: str,
           segments: list[Segment] | None = None, crf: int = 21) -> str:
    """Blurred-fill vertical layout: full gameplay in the middle, no black bars."""
    out_p = Path(out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    dur = m.end - m.start
    ass = out_p.with_suffix(".ass")
    ass.write_text(build_ass(hook, dur, segments, m.start, m.end), encoding="utf-8")
    ass_arg = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    vf = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2,eq=brightness=-0.08[bgb];"
        f"[fg]scale={W}:-2:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,ass='{ass_arg}'[v]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{m.start:.2f}", "-t", f"{dur:.2f}", "-i", video,
        "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-r", "30",
        str(out_p),
    ]
    subprocess.run(cmd, check=True)
    return str(out_p)
