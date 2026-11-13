---
type: research
topic: GTA 6 Clipping
researched: 2026-11-12
summary: "How to make short clips that get views on Shorts, TikTok and Reels: what each app ranks, the two clip lengths that win, hooks, captions, safe zones, titles, posting and campaign rules. Built into the bot on 2026-11-12."
source: Claude research 2026-11-12 (about 25 pages of creator, vendor and platform material, plus our own YouTube research and test clips)
updated: 2026-11-12
---
# Clipping playbook

> [!learn] In short
> **Every app asks one question first: did people stop scrolling and keep watching?** So every clip is one story a stranger understands, it opens on action with a hook on screen in frame one, and it is either **8-15 s (one beat)** or **50-75 s (a whole story)**, never 16-45 s. Captions are big, 1-3 words, in the middle of the screen, away from the app's buttons. Post 1-3 a day, every day, and let our own numbers decide what to repeat.

Builds on [[How to structure a clip]] and [[YouTube research 2026-11-08]]. Back to [[GTA 6 Clipping (index)]].

**How sure is this?** Platforms publish very little. Items marked **(official)** are YouTube, TikTok or Instagram statements (most of them quoted second-hand by blogs). Everything else is creator or vendor blog advice, or our own small data. Treat blog numbers as starting points, not facts.

---

## 1. What each app actually ranks

**All three:** a new clip goes to a small test audience first. If they keep watching, it goes to a bigger one, and so on. The first second decides most of it.

**YouTube Shorts**
- The key number is **"Stayed to watch"** (it used to be "Viewed vs. swiped away"): the share of people who didn't swipe past the first seconds **(official definition)**. YouTube publishes no "good" number. Blogs say 70%+ is great and under 30-40% means the hook is broken. Compare against our own median.
- Since 31 Mar 2025 every play and replay counts as a view; the old definition is now "engaged views", which is what pays **(official)**.
- No ideal length, no daily quota, and time of day isn't optimised for **(official, Shorts lead Todd Sherman, 2023)**. Deleting and re-posting a Short can look like spam **(official)**.
- Since 1 Oct 2026 **original** Shorts rank higher and plain re-uploads get less reach. That's why our clips always get a hook, captions and a story edit.
- Thumbnails are mostly never seen in the feed. The first frame is the thumbnail.

**TikTok**
- Strongest signals: watch time and completion, rewatches, then shares, comments and saves. The "70% completion" and "15-20% rewatch" figures you'll see are blog numbers; TikTok hasn't published any.
- Search matters: TikTok indexes caption text and on-screen text, so the first caption line should say what the clip is ("GTA 6 police chase").
- **Creator Rewards only pays for videos over 1 minute.** A 60 s+ story cut can earn there too.
- Reposts, watermarked cross-posts and remix chains are downranked. Never upload a file with another app's watermark.
- The US feed now runs on a model retrained by the US joint venture (2026), and creators reported reach swings in early 2026.

**Instagram Reels**
- Top three signals: **watch time, likes and sends** (DM shares) **(official, Mosseri)**. Sends matter most for reaching non-followers, and comments matter much less **(official, Oct 2026)**.
- So our IG caption asks people to **send** the clip ("Send this to the friend who drives like this"), not to comment.
- No penalty for videos edited in other apps, **but a visible watermark/logo from another app means less reach (official)**.
- Hashtags help search, not reach **(official)**. Scheduling doesn't hurt reach **(official)**.
- Accounts that repost others' content 10+ times in 30 days get pulled from recommendations. Our clips must always be real edits.
- **Trial Reels** go to non-followers first. Several different trials a day is fine; posting the same Reel as a trial over and over is not **(official, Oct 2026)**.

## 2. Length: the two cuts

| Cut | Length | When | Why |
|---|---|---|---|
| **Punch** | 8-15 s | one setup line, one payoff, 1-2 s of reaction | highest completion and rewatch; our GTA sample: 0-15 s median 452k views |
| **Story** | 50-75 s | a full run-up with a payoff at the end | our sample: 61 s+ median 712k views and best engagement; 60 s+ earns TikTok Creator Rewards |
| ~~Middle~~ | 16-45 s | avoid | our sample: 79-147k median, the worst bucket |

Our own CoD test agreed: the 32 s clip did worse than the short ones. Other studies disagree on the exact lengths (ClipFlip's 44,000 clips: 7-15 s best on average, 60 s+ lower average but higher ceiling), so we keep testing both cuts. The bot now makes **both cuts of every moment** by default.

## 3. The first second

- **Open on action.** No intro, logo, menu, lobby or fade from black. Viewers decide in about 0.8 s (ClipFlip).
- **Hook text on screen from frame one to the end**, 3-7 words, so a late scroller still knows the question.
- Hook types that work: the stakes ("One bump. Six stars."), a promise ("Wait for the NPC"), POV ("POV: you trust the GPS"), or a flash of the payoff then back to the setup.
- Lead with tension, not with backstory. If the first line is weak, start on the sharpest line.
- Don't promise what the clip doesn't deliver; people swipe and the next test batch shrinks.

## 4. Pacing and endings

- Cut dead air. Fast clips got about 2.4x the views of slow polished ones (ClipFlip, their own data). No shot sits still over ~3 s in a punch cut.
- **Never cut inside the payoff**, and keep the tiny pause before a punchline.
- **End 1-2 s after the payoff, on moving footage.** No freeze frames, no hard stop mid-word (alex's own feedback, [[clip-ending-style]]). A short tail lets the clip loop, and loops count as views on Shorts.
- Audio: normalise to about -14 LUFS (what the apps play at) and fade only the last 0.25 s. A long fade-out kills the loop.

## 5. Captions and safe zones

- Most people watch with sound off, so captions are not optional. Captions lifted completion from ~37% to ~65% in one Reels study (Metricool).
- **1-3 words at a time, big (≈75 px), bold, white with a black outline, key words in yellow, small pop-in.** Break at pauses and sentence ends. Fix names and brands by hand.
- **Keep text out of the app's buttons (1080x1920):** top 220 px, bottom 480 px, left 90 px, right 150 px. That is the overlap of TikTok (top 108, bottom 320, right 120), Reels (top 210, bottom 310) and Shorts (top 120, bottom 300-360), plus room for the caption text the app draws at the bottom.
- Gameplay should fill the screen. A small 16:9 strip in a sea of blur looks low-effort; the bot now crops gameplay to 4:3 by default (`--layout zoom`), or full 9:16 for one centred subject (`--layout fill`).

## 6. Titles, captions and hashtags

- **YouTube title:** a statement or **"POV:"** line, about 9 words, one emoji (💀 did best), no question. Our sample: POV was 5x over-represented in top Shorts, questions under-performed, and starting with "GTA" didn't help.
- **TikTok / Instagram caption:** first line says what it is in search words ("GTA 6 police chase: …"), then credit, then one prompt (TikTok: a comment question; Instagram: "send this to…"), then **3-5 topic hashtags**. Drop #fyp/#viral: they say nothing about the clip.
- **Campaign clips:** paste the campaign's required block exactly (tags, #ad, song credit). The bot already does this from `sources.toml`.
- Each platform gets a different hook and title so the three uploads aren't identical copies.

## 7. Posting

- **1-3 clips a day, every day.** Consistency beats bursts. Never dump 10 at once, and never post 10 on day one of a new account (that's how accounts get throttled).
- Times (local, weak evidence): TikTok Tue-Thu 7-10 PM; Shorts weekdays 2-4 PM or Fri-Sat 4-7 PM; Reels weekdays 11 AM-1 PM. Our own GTA sample: top Shorts went up at 17:00, 00:00 and 05:00 UTC. YouTube says timing barely matters, so pick a steady slot and keep it.
- Judge a clip at 24-48 h, not after an hour. Test 5-10 clips before deciding a style works.
- Cross-posting one clip to all three apps is fine as long as each upload is clean (no watermark) and has its own title and caption.
- Never delete and re-post a flop on YouTube; post a new cut instead.

## 8. Clip campaigns (Content Rewards / Whop)

- Pay = views ÷ 1,000 × rate, capped per clip. Most campaigns pay **$0.80-$2.00 per 1,000 views** (median listed rate $1.09 across 707 live campaigns on 10 Nov 2026). Content Rewards keeps 10%.
- A clip earns only after it passes the campaign's minimum (a $2 minimum at $1 CPM = 2,000 views).
- New rule (since 25 Sep 2026): a clip earns for 30 days from the day it crosses the threshold.
- **Submit within 30 minutes of posting**, and only to platforms the campaign lists. One post goes in one campaign, once.
- Most rejections: missing tag/handle/#ad, wrong platform, banned edit style, reusing an edit across campaigns. Paste the required text from a saved template every time.
- **Buying views or offering prizes for views is a permanent ban.** (We already said no to promoted views on 8 Nov.)
- Run 2-3 campaigns at once, since budgets run out first come, first served.

## 9. Our own rules (unchanged)

- Only clip footage we have permission for: our own play, a clip campaign, or a streamer who publicly allows clipping. The bot refuses anything else.
- No GTA story spoilers or cutscenes (the bot blocks letterboxed footage), no pre-launch leaks, no YouTube downloading.
- No graphic violence in the first 8 s (YouTube ads).

## 10. What alex still has to set up

Uploading is still a dry run until these exist:
1. **YouTube:** a Google Cloud OAuth client and a refresh token for the channel.
2. **TikTok:** a developer app with the Content Posting API (posts stay private until TikTok audits the app).
3. **Instagram:** a Business or Creator account linked to a Facebook Page, plus a Meta app token and a public URL for the video files.

Until then, post by hand and log each clip's numbers (views, average % viewed, YouTube "Stayed to watch", shares/sends) in `data/performance.jsonl` so `python -m clipper tune` can learn.

## 11. Launch week plan (Nov 19-26)

1. Day 1-3: only first reactions, cops and NPC chaos, the moments everyone searches. Both cuts of each.
2. Every night: `python -m clipper check` on the day's clips, post 1-3 per platform, log the numbers.
3. Nov 22-26: re-run `python -m clipper research` for real GTA 6 gameplay data and update this note.
4. After ~20 posted clips: run `tune` and drop the cut length or hook style that loses.

## What changed in the bot (2026-11-12)

- Two cuts per moment (`--cuts punch,story`), with the payoff and reaction always kept and the graphic-violence rule respected.
- Captions: real word timing from Whisper, break at pauses, white with yellow key words and a pop, inside the safe zone.
- Gameplay crop (`--layout zoom|blur|fill`), loudness normalised to -14 LUFS, 0.25 s tail fade.
- New hooks, POV titles, searchable caption lines, send prompts on Instagram, no #fyp.
- `python -m clipper check clip.mp4`: flags wrong size, dead-zone length, black first frame, frozen ending, bad loudness.
- AI ranker prompt now scores "one story a stranger gets"; `tune` also learns from "Stayed to watch" and sends.

**Sources:** YouTube Help (Shorts analytics, view counting) via outlierkit.com, prepublish.ai, shortimize.com, gyre.pro · Mosseri statements via zoomsphere.com, highstyle.ai, creatorlanehq.com · TikTok: socialync.io, shortgen.io, stackinfluence.com, blog.eklipse.gg · Clipping: clipflip.io (44k-clip study), findclout.com, streamclipping.ai · Safe zones: reap.video, adaptlypost.com · Campaigns: contentrewards.com (payouts, rejections), clipspeed.ai, openclip.app, trends.vc · Timing: blog.eklipse.gg, buffer.com.

---
Part of [[GTA 6 Clipping (index)]] · [[Research Library]]
