"""YouTube Shorts upload via the Data API v3 (resumable upload, ~1,600 quota units)."""
from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

from . import http

UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"


def access_token() -> str:
    """Swap the saved refresh token for a fresh access token."""
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    _, _, data = http("POST", "https://oauth2.googleapis.com/token",
                      {"Content-Type": "application/x-www-form-urlencoded"}, body)
    return data["access_token"]


def upload(path: str, title: str, description: str, live: bool = False,
           privacy: str = "public") -> dict:
    meta = {
        "snippet": {"title": title, "description": description, "categoryId": "20",
                    "tags": ["GTA 6", "GTA VI", "Shorts"]},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    if not live:
        return {"dry_run": True, "platform": "youtube", "file": path, "meta": meta}
    token = access_token()
    data = Path(path).read_bytes()
    _, headers, _ = http("POST", UPLOAD, {
        "Authorization": f"Bearer {token}",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(len(data)),
    }, meta)
    location = headers.get("Location") or headers.get("location")
    _, _, res = http("PUT", location, {"Authorization": f"Bearer {token}",
                                       "Content-Type": "video/mp4"}, data, timeout=900)
    return {"platform": "youtube", "id": res.get("id"), "url": f"https://youtube.com/shorts/{res.get('id')}"}
