import datetime as dt
import json
import subprocess

import numpy as np
import pytest

from clipper import cli, hooks, inputs, render, rules, score, signals
from clipper.learn import tune, youtube_research


@pytest.fixture(scope="session")
def video(tmp_path_factory):
    """60 s fake gameplay: quiet, a loud red 'crash' at 30-32 s, letterboxed 'cutscene' 44-56 s
    with a second loud bang at 50 s."""
    p = tmp_path_factory.mktemp("v") / "game.mp4"
    vf = ("drawbox=x=0:y=0:w=iw:h=ih:color=red:t=fill:enable='between(t,30,32)',"
          "drawbox=x=0:y=0:w=iw:h=70:color=black:t=fill:enable='between(t,44,56)',"
          "drawbox=x=0:y=290:w=iw:h=70:color=black:t=fill:enable='between(t,44,56)'")
    af = ("[1:a]volume='if(between(t,30,32)+between(t,50,51),1.0,0)':eval=frame[s];"
          "[0:a][s]amix=inputs=2:normalize=0[a]")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "anoisesrc=d=60:a=0.01:r=16000",
        "-f", "lavfi", "-i", "sine=f=500:d=60:r=16000",
        "-f", "lavfi", "-i", "testsrc2=s=640x360:d=60:r=15",
        "-filter_complex", af + f";[2:v]{vf}[v]", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(p)], check=True)
    return str(p)


def test_finds_the_crash_and_blocks_the_cutscene(video):
    transcript = [signals.Segment(29.5, 32.0, "bro no way the cops"),
                  signals.Segment(50.0, 51.0, "oh my god")]
    moments, feats, dur = score.analyze(video, transcript=transcript)
    assert 59 < dur < 61
    assert moments, "should find at least one moment"
    best = moments[0]
    assert best.start <= 30 <= best.end
    moments = rules.apply(moments, feats, 2.0, transcript)
    crash = [m for m in moments if m.start <= 31 <= m.end][0]
    assert crash.blocked is None
    assert crash.kind == "cop_escalation"
    cut = [m for m in moments if m.start <= 50 <= m.end and not (m.start <= 31 <= m.end)]
    assert cut and cut[0].blocked and "cutscene" in cut[0].blocked


def test_chat_spike_is_a_signal():
    chat = [(t, "hi") for t in range(0, 60, 5)] + [(40 + i * 0.1, "LMAO clip it 💀") for i in range(20)]
    s = signals.chat_signal(chat, 2.0, 60)
    assert int(np.argmax(s)) == 20


def test_render_makes_vertical_clip(video, tmp_path):
    m = score.Moment(start=27, end=34, peak=31, score=5)
    out = render.render(video, m, str(tmp_path / "c.mp4"), "He didn't see it coming",
                        [signals.Segment(29.5, 32, "bro no way")])
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height:format=duration", "-of", "json", out],
                          capture_output=True, text=True, check=True).stdout
    j = json.loads(info)
    assert (j["streams"][0]["width"], j["streams"][0]["height"]) == (1080, 1920)
    assert 6.5 < float(j["format"]["duration"]) < 7.5


def test_source_permission_rules(tmp_path):
    (tmp_path / "s.toml").write_text('[source.me]\nkind="own"\n[source.rando]\nkind="campaign"\n')
    srcs = rules.load_sources(str(tmp_path / "s.toml"))
    assert rules.check_source("me", srcs).kind == "own"
    with pytest.raises(PermissionError):
        rules.check_source("rando", srcs)          # no proof saved
    with pytest.raises(PermissionError):
        rules.check_source("nobody", srcs)         # not on the list
    with pytest.raises(PermissionError):
        rules.check_recorded_date(dt.date(2026, 11, 1))   # pre-launch = leak
    rules.check_recorded_date(dt.date(2026, 11, 19))


def test_graphic_violence_pushed_past_second_8():
    m = score.Moment(start=20, end=30, peak=25, score=4)
    rules.apply([m], {"letterbox": np.zeros(30)}, 2.0, [signals.Segment(24, 26, "headshot blood")])
    assert "graphic" in m.kind and m.peak - m.start >= 8 and m.blocked is None


def test_hooks_differ_per_platform():
    caps = {p: hooks.pick_hook("chaos_fail", "clip-01", p) for p in ["youtube", "tiktok", "instagram"]}
    assert all(1 <= len(h.split()) <= 6 for h in caps.values())
    yt = hooks.caption("chaos_fail", "clip-01", "youtube", "@streamer")
    assert yt["title"].startswith("GTA 6") and "@streamer" in yt["description"]


def test_inputs(tmp_path):
    (tmp_path / "a.srt").write_text("1\n00:00:01,500 --> 00:00:03,000\nbro what\n\n2\n00:01:00,000 --> 00:01:02,000\nno way\n")
    segs = inputs.read_srt(str(tmp_path / "a.srt"))
    assert segs[0].start == 1.5 and segs[1].text == "no way"
    (tmp_path / "c.txt").write_text("[00:00:40] bob: LMAO\n[01:00:00] amy: clip it\n")
    assert inputs.read_chat(str(tmp_path / "c.txt")) == [(40.0, "LMAO"), (3600.0, "clip it")]


def test_youtube_research_helpers():
    ts = youtube_research.comment_timestamps(["0:12 💀", "0:12 lmao", "1:05 the npc", "12345"])
    assert ts.most_common(1)[0] == (12, 2)
    assert youtube_research.iso_seconds("PT1M5S") == 65
    s = youtube_research.summarize([
        {"title": "GTA 6 cops are INSANE", "seconds": 20, "views": 900, "published": "2026-11-20T18:00:00Z",
         "hot_position": [0.4]},
        {"title": "boring video", "seconds": 58, "views": 10, "published": "2026-11-20T03:00:00Z"}])
    assert s["top_avg_seconds"] == 20


def test_tune_moves_weights_toward_what_worked():
    rows = [{"signals": {"chat": c, "loudness": 1.0}, "views": 10 ** (2 + c), "avg_view_pct": 0.6}
            for c in np.linspace(0, 3, 10)]
    new = tune.fit(rows, {"chat": 1.0, "loudness": 1.0})
    assert new["chat"] > 1.0


def test_cli_end_to_end(video, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sources.toml").write_text('[source.me]\nkind="own"\n')
    assert cli.main(["clip", video, "--source", "me", "--max", "2", "--recorded", "2026-11-19"]) == 0
    man = next((tmp_path / "clips").glob("*/manifest.json"))
    assert cli.main(["approve", str(man), "all"]) == 0
    assert cli.main(["post", str(man)]) == 0
    out = capsys.readouterr().out
    assert "dry run" in out
    data = json.loads(man.read_text())
    assert any(c.get("results", {}).get("youtube", {}).get("dry_run") for c in data["clips"])
    assert cli.main(["clip", video, "--source", "stranger"]) == 2


def test_peaks_are_spread_across_the_stream():
    s = np.zeros(400)
    s[[10, 20, 30, 40, 300]] = [9, 8, 7, 6, 5]
    picks = score.find_peaks(s, min_gap=5, threshold=1, spread=150, per_spread=2)
    assert picks == [10, 20, 300]


def test_cuts_snap_to_sentence_edges():
    segs = [signals.Segment(8.0, 12.5, "bro watch this jump"), signals.Segment(20, 23, "no way")]
    assert score.snap(10.0, 21.0, segs, None, 2.0) == (8.0, 23)


def test_loudness_vs_baseline_finds_shout_in_loud_game():
    loud = np.array([-10.0] * 50 + [-30.0] * 50)
    loud[75] = -12          # a shout in the quiet half
    rel = signals.vs_baseline(loud, 2.0, baseline_s=40)
    assert int(np.argmax(rel[50:])) + 50 == 75


def test_ai_rank_blends_scores(monkeypatch):
    from clipper import ai_rank
    ms = [score.Moment(0, 10, 5, 2.0), score.Moment(20, 30, 25, 3.0)]
    reply = {"content": [{"type": "text", "text": '[{"id":0,"viral":10,"hook":"Cops lost it","reason":"Huge fail"},'
                                                  '{"id":1,"viral":0,"hook":"meh","reason":"Boring"}]'}]}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return json.dumps(reply).encode()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(ai_rank.urllib.request, "urlopen", lambda *a, **k: R())
    out = ai_rank.rank(ms, None)
    assert out[0].ai_hook == "Cops lost it" and out[0].score == 6.0
    assert ai_rank.parse("junk") == []


def test_facecam_layout(video, tmp_path):
    m = score.Moment(start=27, end=30, peak=28, score=5)
    out = render.render(video, m, str(tmp_path / "f.mp4"), "Hook", facecam="0:0:200:150")
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height", "-of", "csv=p=0", out], capture_output=True, text=True).stdout
    assert info.strip() == "1080,1920"


def test_delete_source_only_after_clips_exist(tmp_path):
    from clipper.cli import delete_source
    video = tmp_path / "rec.mp4"
    video.write_bytes(b"raw")
    clip = tmp_path / "c1.mp4"
    assert delete_source(str(video), []) is False and video.exists()
    assert delete_source(str(video), [str(clip)]) is False and video.exists()
    clip.write_bytes(b"clip")
    assert delete_source(str(video), [str(clip)]) is True
    assert not video.exists() and clip.exists()
