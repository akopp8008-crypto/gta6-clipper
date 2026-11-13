"""Cut a moment into a 1080x1920 vertical clip with a hook and captions."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .playbook import SAFE, TARGET_LUFS, H, W
from .score import Moment
from .signals import REACTION_WORDS, Segment

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,3,6,0,8,{L},{R},{TOP},1
Style: Cap,DejaVu Sans,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,7,2,2,{L},{R},{BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(L=SAFE["left"], R=SAFE["right"], TOP=SAFE["top"] + 40, BOTTOM=SAFE["bottom"] + 60)

# Captions are white; words that carry the moment pop in yellow.
HIGHLIGHT = "{\\c&H00E5FF&}"
POP = "{\\fscx118\\fscy118\\t(0,90,\\fscx100\\fscy100)}"
_KEY = {w for w in REACTION_WORDS if " " not in w} | {"gta", "cops", "wanted", "stars", "dead", "insane"}


def _ts(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def _timed_words(seg: Segment) -> list[tuple[float, float, str]]:
    if seg.words:
        return list(seg.words)
    words = seg.text.split()
    step = (seg.end - seg.start) / max(1, len(words))
    return [(seg.start + i * step, seg.start + (i + 1) * step, w) for i, w in enumerate(words)]


def caption_chunks(segments: list[Segment], start: float, end: float, words_per: int = 3):
    """Split speech into 1-3 word pop-up captions.

    Uses real word timing when the transcript has it. A chunk also breaks at a
    pause or at the end of a sentence, so a caption never straddles two thoughts.
    """
    for seg in segments:
        if seg.end < start or seg.start > end:
            continue
        chunk: list[tuple[float, float, str]] = []
        words = _timed_words(seg)
        for i, w in enumerate(words):
            chunk.append(w)
            nxt = words[i + 1] if i + 1 < len(words) else None
            if (len(chunk) >= words_per or nxt is None or nxt[0] - w[1] > 0.4
                    or w[2][-1:] in ".?!,"):
                a, b = chunk[0][0], chunk[-1][1]
                if nxt is not None:
                    b = max(b, min(nxt[0], b + 0.25))
                if b >= start and a <= end:
                    yield max(a, start) - start, min(b, end) - start, " ".join(x[2] for x in chunk).upper()
                chunk = []


def styled(text: str) -> str:
    """Escape a caption and colour its key words."""
    out = []
    for word in _esc(text).split():
        bare = "".join(ch for ch in word.lower() if ch.isalnum() or ch == "'")
        hot = bare in _KEY or any(ch.isdigit() for ch in bare) or word.endswith("!")
        out.append(f"{HIGHLIGHT}{word}{{\\c&HFFFFFF&}}" if hot else word)
    return POP + " ".join(out)


def build_ass(hook: str, duration: float, segments: list[Segment] | None,
              start: float, end: float, hook_seconds: float | None = None) -> str:
    lines = [ASS_HEADER]
    hook_end = duration if hook_seconds is None else min(duration, hook_seconds)
    lines.append(f"Dialogue: 1,{_ts(0)},{_ts(hook_end)},Hook,,0,0,0,,{_esc(hook)}\n")
    for a, b, txt in caption_chunks(segments or [], start, end):
        lines.append(f"Dialogue: 0,{_ts(a)},{_ts(b)},Cap,,0,0,0,,{styled(txt)}\n")
    return "".join(lines)


LAYOUTS = ("zoom", "blur", "fill")


def layout_filter(ass_arg: str, facecam: str | None, layout: str = "zoom") -> str:
    """Layouts.

    * zoom (default): gameplay cropped to 4:3 so it fills 42% more of the phone, blurred copy behind.
      Small gameplay in a sea of blur is the most common "low effort" tell.
    * blur: full 16:9 gameplay in the middle, blurred copy behind it.
    * fill: centre crop to full 9:16 (one subject in the middle, e.g. skydiving, driving).
    * facecam: streamer cam on top, gameplay below (facecam = "x:y:w:h" in source pixels).
    """
    if facecam:
        x, y, w, h = facecam.split(":")
        cam_h, game_h = 640, H - 640
        return (
            f"[0:v]split=2[c][g];"
            f"[c]crop={w}:{h}:{x}:{y},scale={W}:{cam_h}:force_original_aspect_ratio=increase,crop={W}:{cam_h}[cam];"
            f"[g]scale=-2:{game_h},crop={W}:{game_h}[game];"
            f"[cam][game]vstack=inputs=2,setsar=1,ass='{ass_arg}'[v]"
        )
    if layout == "fill":
        return f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,ass='{ass_arg}'[v]"
    fg = ("crop='min(iw,ih*4/3)':ih,scale=" + f"{W}:-2" if layout == "zoom"
          else f"scale={W}:-2:force_original_aspect_ratio=decrease")
    return (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2,eq=brightness=-0.08[bgb];"
        f"[fg]{fg}[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,ass='{ass_arg}'[v]"
    )


def audio_filter(dur: float) -> str:
    """Even loudness on every clip (apps normalise to about -14 LUFS) and a 0.25 s
    tail fade so the last frame doesn't click. Short on purpose: a long fade kills the loop."""
    fade = max(0.0, dur - 0.25)
    return (f"[0:a]loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11,aresample=48000,"
            f"afade=t=out:st={fade:.2f}:d=0.25[a]")


def _has_audio(video: str) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", video], capture_output=True, text=True).stdout
    return bool(out.strip())


def render(video: str, m: Moment, out: str, hook: str,
           segments: list[Segment] | None = None, crf: int = 21, facecam: str | None = None,
           layout: str = "zoom") -> str:
    """Cut the moment and lay it out 1080x1920 with hook and captions."""
    out_p = Path(out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    dur = m.end - m.start
    ass = out_p.with_suffix(".ass")
    ass.write_text(build_ass(hook, dur, segments, m.start, m.end), encoding="utf-8")
    ass_arg = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    vf = layout_filter(ass_arg, facecam, layout)
    has_audio = _has_audio(video)
    if has_audio:
        vf += ";" + audio_filter(dur)
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{m.start:.2f}", "-t", f"{dur:.2f}", "-i", video,
        "-filter_complex", vf, "-map", "[v]", "-map", "[a]" if has_audio else "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-r", "30",
        str(out_p),
    ]
    subprocess.run(cmd, check=True)
    return str(out_p)
