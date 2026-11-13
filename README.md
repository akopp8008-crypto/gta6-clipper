# GTA 6 Clipper

Finds the best moments in GTA gameplay or streams, cuts them into 1080x1920 vertical clips with a
hook and word-by-word captions, and posts them to **YouTube Shorts, TikTok and Instagram Reels**.
It learns from YouTube (official API) and from how its own clips perform.

GTA 6 launches **Nov 19, 2026** (PS5 / Xbox Series X|S). Until then, tune it on GTA 5 / GTA Online footage.
Research and the full plan live in the Obsidian vault: `Research Library/GTA 6 Clipping`.

## How it works

```
footage ─► signals ─► score ─► safety rules ─► render ─► review ─► post ─► stats ─► tune
```

| Step | File | What it does |
|---|---|---|
| Signals | `clipper/signals.py` | Per 2-second window: loudness, sudden loudness jumps, scene change (crashes), reaction words in the transcript, chat speed + "clip it"/LMAO emotes, letterbox bars |
| Score | `clipper/score.py` | Loudness vs. the streamer's normal level, weighted outlier-robust sum, bonus when 2+ signals spike together; peaks 12 s apart and max 2 per 5 minutes; 5 s of setup; cuts snap to sentence ends (or the quietest point) |
| AI rank | `clipper/ai_rank.py` | Optional (`--ai`): Claude reads what was said around each candidate and returns a viral score, hook and reason. Only text is sent |
| Rules | `clipper/rules.py` | Only sources in `sources.toml` with saved permission; blocks letterboxed story cutscenes and pre-launch (leaked) GTA 6 footage; pushes graphic violence past second 8 for YouTube ads; labels the moment type (cops, fail, NPC, first reaction, skill, wildlife) |
| Cuts | `clipper/score.py` | Each moment is cut twice: **punch** (8-15 s) and **story** (50-75 s). The 16-45 s middle loses on Shorts |
| Render | `clipper/render.py` | 9:16 with gameplay cropped to 4:3 (`--layout zoom`, or `blur` / `fill`), or cam on top (`--facecam x:y:w:h`); hook text and 1-3 word captions (real word timing, yellow key words) inside the apps' safe zone; loudness -14 LUFS |
| Hooks | `clipper/hooks.py` | 3-7 word on-screen hooks, POV/statement YouTube titles, searchable TikTok/IG first lines, send/comment prompts; different per platform |
| Check | `clipper/playbook.py` | `python -m clipper check *.mp4`: size, dead-zone length, black first frame, frozen ending, loudness |
| Post | `clipper/publish/` | Official APIs only. **Dry run unless `--live`** |
| Learn | `clipper/learn/` | `research`: top recent GTA Shorts, title patterns, comment timestamps ("0:12 💀") via YouTube Data API. `tune`: re-weights signals from our own clip results |

The rules behind all of this are in [docs/PLAYBOOK.md](docs/PLAYBOOK.md).

## Setup

Needs Python 3.11+ and ffmpeg.

```bash
pip install -e ".[dev]"            # add ,whisper for automatic transcripts
cp sources.example.toml sources.toml
cp .env.example .env               # fill in keys, then: set -a; . ./.env; set +a
pytest -q
```

## Use it

```bash
# 1. Find and cut clips (8 best by default) into clips/<run>/
python -m clipper clip stream.mp4 --source me --whisper --chat chat.txt --recorded 2026-11-19
#    add --ai for Claude ranking, --facecam 0:0:480:270 for cam-on-top

#    --cuts punch (only short cuts), --layout fill (centre crop to 9:16)
python -m clipper check clips/<run>/*.mp4     # playbook checks, also works on hand-made edits

# 2. Review the mp4s, then approve the good ones
python -m clipper approve clips/<run>/manifest.json 1 3 4

# 3. Post (prints what it would send; add --live to really post)
python -m clipper post clips/<run>/manifest.json
python -m clipper post clips/<run>/manifest.json --live

# 4. Learn
python -m clipper research          # needs YOUTUBE_API_KEY
python -m clipper tune              # reads data/performance.jsonl
```

## Whose footage

The bot refuses any source that isn't in `sources.toml`:
- `own`: your own gameplay.
- `campaign`: a paid clip campaign (Whop Content Rewards and similar), with the campaign link as proof.
- `public_permission`: a streamer who publicly says "clip me", with a link or screenshot as proof.

Every clip credits the source in the caption. Since Oct 1, 2026 YouTube cuts Shorts reach for plain re-uploads,
so the hook, captions and story edit are part of every clip.

## Accounts and keys

| Platform | What you need | Notes |
|---|---|---|
| YouTube research | API key with YouTube Data API v3 | 10,000 free units/day; one research run ≈ 900 |
| YouTube upload | OAuth client + refresh token | ≈1,600 units per upload, so ~6 uploads/day on the free quota |
| TikTok | Developer app with Content Posting API | Posts stay private until TikTok audits the app (`TIKTOK_AUDITED=1` after) |
| Instagram | Business/Creator account linked to a Facebook Page, Meta app, IG user id + token | Instagram pulls the video from a public URL (`CLIP_PUBLIC_BASE_URL`) |

## Ideas borrowed from other open-source clippers

See the vault note `Open-source clipper repos`: rolling loudness baseline and sentence-snapped cuts
(kiy0ni/auto-video-editor), AI score + hook + reason (Anil-matcha/AI-Youtube-Shorts-Generator, artbyjazi/autoclip),
facecam-top layout (LuisSotelo/vod-to-viral), explainable scores (Aseiel/VideoHighlighter).

## Next up

- Live stream watcher (record allowed streams as they happen, clip every 10 minutes)
- HUD reading (wanted stars, "WASTED") once GTA 6's HUD is known on launch day
- Vision-model labeling of moment type from a few frames
- Stats puller that fills `data/performance.jsonl` 48 h after each post
