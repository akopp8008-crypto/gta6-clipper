"""Instagram Reels via the Instagram Graph API (Business or Creator account).

Instagram fetches the video from a public URL, so set CLIP_PUBLIC_BASE_URL
to where rendered clips are hosted (for example a storage bucket).
"""
from __future__ import annotations

import os
import time
import urllib.parse
from pathlib import Path

from . import http

GRAPH = "https://graph.facebook.com/v21.0/"


def upload(path: str, caption: str, live: bool = False, wait_s: int = 300) -> dict:
    base = os.environ.get("CLIP_PUBLIC_BASE_URL", "").rstrip("/")
    video_url = f"{base}/{Path(path).name}" if base else "(set CLIP_PUBLIC_BASE_URL)"
    params = {"media_type": "REELS", "video_url": video_url, "caption": caption, "share_to_feed": "true"}
    if not live:
        return {"dry_run": True, "platform": "instagram", "file": path, "params": params}
    user, token = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]
    q = urllib.parse.urlencode({**params, "access_token": token})
    _, _, res = http("POST", f"{GRAPH}{user}/media?{q}")
    container = res["id"]
    deadline = time.time() + wait_s
    while time.time() < deadline:
        _, _, st = http("GET", f"{GRAPH}{container}?fields=status_code&access_token={token}")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram could not process the video: {st}")
        time.sleep(10)
    q = urllib.parse.urlencode({"creation_id": container, "access_token": token})
    _, _, pub = http("POST", f"{GRAPH}{user}/media_publish?{q}")
    return {"platform": "instagram", "id": pub.get("id")}
