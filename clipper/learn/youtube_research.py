"""Learn what GTA clips win on YouTube, using only the official Data API v3.

What it collects (public data, no video downloads):
* top recent GTA Shorts: title, length, views, likes, comments, upload hour
* comment timestamps like "0:42 lmao": which second people found funniest
* title patterns that win (length, caps, numbers, emojis, where "GTA 6" sits)

Quota: search = 100 units, videos.list / commentThreads.list = 1 unit each.
The free daily quota is 10,000 units, so one run of ~10 searches is cheap.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import statistics
import urllib.parse
import urllib.request
from collections import Counter

API = "https://www.googleapis.com/youtube/v3/"

QUERIES = ["GTA 6 funny", "GTA 6 cops", "GTA 6 moments", "GTA 6 fail", "GTA 6 NPC",
           "GTA 5 funny moments", "GTA online funny", "GTA 6 first reaction"]

_TS = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _get(endpoint: str, key: str, **params) -> dict:
    params["key"] = key
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def iso_seconds(d: str) -> int:
    m = _DUR.fullmatch(d or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def comment_timestamps(texts: list[str], max_len: int = 180) -> Counter:
    """Seconds that commenters point at ("0:12 💀"). Peaks = the funniest beat."""
    c: Counter = Counter()
    for t in texts:
        for mm, ss in _TS.findall(t):
            sec = int(mm) * 60 + int(ss)
            if sec <= max_len:
                c[sec] += 1
    return c


def title_features(title: str) -> dict:
    words = title.split()
    return {
        "words": len(words),
        "caps_words": sum(w.isupper() and len(w) > 1 for w in words),
        "has_number": bool(re.search(r"\d", title.replace("6", "").replace("5", ""))),
        "has_emoji": bool(re.search(r"[\U0001F300-\U0001FAFF]", title)),
        "gta_first": title.lower().startswith("gta"),
        "question": "?" in title,
    }


def research(key: str, days: int = 14, per_query: int = 25, comments_for_top: int = 10) -> dict:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids: set[str] = set()
    for q in QUERIES:
        res = _get("search", key, part="id", q=q, type="video", videoDuration="short",
                   order="viewCount", publishedAfter=since, maxResults=per_query)
        ids.update(i["id"]["videoId"] for i in res.get("items", []))
    videos = []
    id_list = list(ids)
    for k in range(0, len(id_list), 50):
        res = _get("videos", key, part="snippet,statistics,contentDetails", id=",".join(id_list[k:k + 50]))
        for v in res.get("items", []):
            st = v.get("statistics", {})
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "published": v["snippet"]["publishedAt"],
                "seconds": iso_seconds(v["contentDetails"].get("duration", "")),
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
            })
    videos.sort(key=lambda v: v["views"], reverse=True)

    for v in videos[:comments_for_top]:
        try:
            res = _get("commentThreads", key, part="snippet", videoId=v["id"], maxResults=100,
                       order="relevance", textFormat="plainText")
            texts = [c["snippet"]["topLevelComment"]["snippet"]["textDisplay"] for c in res.get("items", [])]
            ts = comment_timestamps(texts, max(v["seconds"], 60))
            v["hot_seconds"] = ts.most_common(5)
            if v["seconds"]:
                v["hot_position"] = [round(s / v["seconds"], 2) for s, _ in ts.most_common(3)]
        except Exception as e:  # comments disabled etc.
            v["comment_error"] = str(e)[:80]
    return {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "videos": videos,
            "summary": summarize(videos)}


def summarize(videos: list[dict]) -> dict:
    if not videos:
        return {}
    top = videos[: max(1, len(videos) // 5)]       # top 20% by views
    rest = videos[len(top):] or top
    def avg(rows, f):
        vals = [f(r) for r in rows]
        return round(statistics.mean(vals), 2) if vals else 0
    hours = Counter(int(v["published"][11:13]) for v in top)
    words = Counter(w.lower().strip("!?.,") for v in top for w in v["title"].split() if len(w) > 2)
    return {
        "top_avg_seconds": avg(top, lambda v: v["seconds"]),
        "rest_avg_seconds": avg(rest, lambda v: v["seconds"]),
        "top_title_words": avg(top, lambda v: len(v["title"].split())),
        "top_caps_share": avg(top, lambda v: title_features(v["title"])["caps_words"] > 0),
        "top_emoji_share": avg(top, lambda v: title_features(v["title"])["has_emoji"]),
        "best_upload_hours_utc": [h for h, _ in hours.most_common(3)],
        "top_title_words_used": [w for w, _ in words.most_common(20)],
        "hot_positions": sorted(p for v in top for p in v.get("hot_position", [])),
    }


def main(out: str = "data/youtube_research.json") -> str:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("Set YOUTUBE_API_KEY (Google Cloud console → YouTube Data API v3).")
    data = research(key)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    return out
