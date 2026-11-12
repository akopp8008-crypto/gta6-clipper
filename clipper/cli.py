"""Command line: clip → review → post → learn.

  python -m clipper clip VIDEO --source NAME [--chat chat.txt] [--srt subs.srt | --whisper] [--delete-source]
  python -m clipper approve clips/<run>/manifest.json 1 3 4      (or: all)
  python -m clipper post clips/<run>/manifest.json [--live]
  python -m clipper research                                      (needs YOUTUBE_API_KEY)
  python -m clipper tune                                          (after stats come in)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from . import hooks, inputs, playbook, render, rules, score

PLATFORMS = ["youtube", "tiktok", "instagram"]


def cmd_clip(a) -> int:
    sources = rules.load_sources(a.sources)
    src = rules.check_source(a.source, sources)
    rules.check_recorded_date(dt.date.fromisoformat(a.recorded) if a.recorded else None, a.game)

    transcript = inputs.read_srt(a.srt) if a.srt else (inputs.transcribe(a.video) if a.whisper else None)
    chat = inputs.read_chat(a.chat) if a.chat else None
    weights = score.load_weights(a.weights)
    moments, features, duration = score.analyze(a.video, window=a.window, transcript=transcript, chat=chat,
                                         weights=weights, max_clips=a.max * 2, threshold=a.threshold,
                                         spread_s=a.spread, min_gap_s=a.min_gap)
    moments = rules.apply(moments, features, a.window, transcript,
                          block_cutscenes=a.game.startswith("gta"))
    if a.ai:
        from . import ai_rank
        moments = ai_rank.rank(moments, transcript)

    run = Path(a.out) / f"{Path(a.video).stem}-{dt.datetime.now():%Y%m%d-%H%M%S}"
    run.mkdir(parents=True, exist_ok=True)
    manifest = {"video": a.video, "source": src.name, "credit": src.credit, "clips": []}
    cuts = [c.strip() for c in a.cuts.split(",") if c.strip()]
    made = 0
    queue = []
    for m in moments:
        if m.blocked or made >= a.max:
            queue.append((m, "blocked" if m.blocked else "skipped"))
            continue
        made += 1
        for c in cuts:
            v = score.shape_cut(m, c, transcript, duration)
            lo = playbook.CUTS.get(c, (0, 0))[0]
            if v.end - v.start < lo - 1:          # not enough run-up for this length
                continue
            queue.append((v, None))
    made = 0
    for m, skip in queue:
        entry = {"n": len(manifest["clips"]) + 1, **m.to_dict()}
        if skip:
            entry["status"] = skip
            manifest["clips"].append(entry)
            continue
        made += 1
        clip_id = f"{run.name}-{entry['n']:02d}-{m.cut}"
        hook = m.ai_hook or hooks.pick_hook(m.kind, clip_id, "tiktok", src.hooks)
        out = render.render(a.video, m, str(run / f"{clip_id}.mp4"), hook, transcript, facecam=a.facecam,
                            layout=a.layout)
        entry.update({
            "id": clip_id, "file": out, "status": "pending", "hook_variants": hooks.hook_variants(m.kind),
            "posts": {p: hooks.caption(m.kind, clip_id, p, src.credit, src.hooks, src.caption)
                      for p in PLATFORMS if p in src.platforms},
        })
        manifest["clips"].append(entry)
        print(f"#{entry['n']:>2} {m.kind:<16} {m.cut:<5} score {m.score:5.2f}  "
              f"{m.start:7.1f}-{m.end:7.1f}s ({m.end - m.start:4.1f}s) → {out}")
        if m.ai_reason:
            print(f"      AI: {m.ai_reason}")
        entry["check"] = playbook.check(out).issues
        for issue in entry["check"]:
            print(f"      check: {issue}")
    for e in manifest["clips"]:
        if e["status"] == "blocked":
            print(f"#{e['n']:>2} BLOCKED: {e['blocked']}")
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{made} clips ready for review: {run / 'manifest.json'}")
    if a.delete_source:
        delete_source(a.video, [e["file"] for e in manifest["clips"] if e.get("file")])
    return 0


def cmd_check(a) -> int:
    bad = 0
    for f in a.files:
        r = playbook.check(f)
        bad += not r.ok
        print(r.text())
    print(f"\n{len(a.files) - bad}/{len(a.files)} clips pass the playbook checks.")
    return 1 if bad else 0


def delete_source(video: str, clip_files: list[str]) -> bool:
    """Delete the raw recording, but only once every clip made from it is safely on disk."""
    if not clip_files:
        print(f"Kept {video}: no clips were made from it.")
        return False
    missing = [f for f in clip_files if not Path(f).is_file() or Path(f).stat().st_size == 0]
    if missing:
        print(f"Kept {video}: {len(missing)} clip file(s) missing or empty.")
        return False
    Path(video).unlink()
    print(f"Deleted the source recording {video} ({len(clip_files)} clips kept).")
    return True


def cmd_approve(a) -> int:
    p = Path(a.manifest)
    man = json.loads(p.read_text())
    pick = None if a.numbers == ["all"] else {int(n) for n in a.numbers}
    for c in man["clips"]:
        if c["status"] == "pending" and (pick is None or c["n"] in pick):
            c["status"] = "approved"
    p.write_text(json.dumps(man, indent=2))
    print(", ".join(str(c["n"]) for c in man["clips"] if c["status"] == "approved") or "nothing approved")
    return 0


def cmd_post(a) -> int:
    from .publish import instagram, tiktok, youtube
    p = Path(a.manifest)
    man = json.loads(p.read_text())
    for c in man["clips"]:
        if c["status"] != "approved":
            continue
        results = c.setdefault("results", {})
        for plat, meta in c["posts"].items():
            if plat not in a.platforms or plat in results and not results[plat].get("dry_run"):
                continue
            if plat == "youtube":
                r = youtube.upload(c["file"], meta["title"], meta["description"], live=a.live)
            elif plat == "tiktok":
                r = tiktok.upload(c["file"], meta["caption"], live=a.live)
            else:
                r = instagram.upload(c["file"], meta["caption"], live=a.live)
            results[plat] = r
            print(f"#{c['n']} {plat}: {'dry run (nothing posted)' if r.get('dry_run') else r}")
        if a.live:
            c["status"] = "posted"
    p.write_text(json.dumps(man, indent=2))
    if not a.live:
        print("\nDry run only. Add --live to really post.")
    return 0


def cmd_research(a) -> int:
    from .learn import youtube_research
    out = youtube_research.main(a.out)
    s = json.loads(Path(out).read_text())["summary"]
    print(json.dumps(s, indent=2))
    return 0


def cmd_tune(a) -> int:
    from .learn import tune
    print(json.dumps(tune.main(a.performance, a.weights), indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="clipper", description="GTA 6 auto-clipper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("clip", help="find and cut the best moments of a video")
    c.add_argument("video")
    c.add_argument("--source", required=True, help="name from sources.toml (who the footage belongs to)")
    c.add_argument("--sources", default="sources.toml")
    c.add_argument("--chat", help="chat log ([HH:MM:SS] user: msg) or JSON")
    c.add_argument("--srt", help="transcript as .srt")
    c.add_argument("--whisper", action="store_true", help="make a transcript with faster-whisper")
    c.add_argument("--recorded", help="date the footage was recorded, YYYY-MM-DD")
    c.add_argument("--game", default="gta6")
    c.add_argument("--weights", default="data/weights.json")
    c.add_argument("--window", type=float, default=2.0)
    c.add_argument("--threshold", type=float, default=2.0)
    c.add_argument("--max", type=int, default=8)
    c.add_argument("--spread", type=float, default=300.0,
                   help="seconds per 2-clip block (use ~30 for a short trailer)")
    c.add_argument("--min-gap", type=float, default=12.0, help="seconds between clip peaks")
    c.add_argument("--out", default="clips")
    c.add_argument("--ai", action="store_true", help="let Claude re-rank clips and write hooks (ANTHROPIC_API_KEY)")
    c.add_argument("--facecam", help="streamer cam area x:y:w:h in source pixels → cam-on-top layout")
    c.add_argument("--layout", default="zoom", choices=render.LAYOUTS,
                   help="zoom: 4:3 gameplay crop (default), blur: full 16:9, fill: centre crop to 9:16")
    c.add_argument("--cuts", default="punch,story",
                   help="lengths to cut each moment: punch (8-15 s), story (50-75 s), auto (as detected)")
    c.add_argument("--delete-source", action="store_true",
                   help="delete the input video after all clips render successfully")
    c.set_defaults(fn=cmd_clip)

    ck = sub.add_parser("check", help="check finished clips against the playbook (size, length, audio, ends)")
    ck.add_argument("files", nargs="+")
    ck.set_defaults(fn=cmd_check)

    ap_ = sub.add_parser("approve", help="mark clips as approved for posting")
    ap_.add_argument("manifest")
    ap_.add_argument("numbers", nargs="+")
    ap_.set_defaults(fn=cmd_approve)

    p = sub.add_parser("post", help="post approved clips (dry run unless --live)")
    p.add_argument("manifest")
    p.add_argument("--live", action="store_true")
    p.add_argument("--platforms", nargs="+", default=PLATFORMS)
    p.set_defaults(fn=cmd_post)

    r = sub.add_parser("research", help="learn what GTA Shorts win, via the YouTube API")
    r.add_argument("--out", default="data/youtube_research.json")
    r.set_defaults(fn=cmd_research)

    t = sub.add_parser("tune", help="retrain scoring weights from our clip results")
    t.add_argument("--performance", default="data/performance.jsonl")
    t.add_argument("--weights", default="data/weights.json")
    t.set_defaults(fn=cmd_tune)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except PermissionError as e:
        print(f"Refused: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
