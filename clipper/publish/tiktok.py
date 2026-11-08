"""TikTok Content Posting API (direct post, single-chunk upload).

Until TikTok audits the developer app, posts can only be private
(SELF_ONLY). Set TIKTOK_AUDITED=1 after the audit passes.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import http

INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"


def upload(path: str, caption: str, live: bool = False) -> dict:
    size = Path(path).stat().st_size
    privacy = "PUBLIC_TO_EVERYONE" if os.environ.get("TIKTOK_AUDITED") == "1" else "SELF_ONLY"
    body = {
        "post_info": {"title": caption[:2200], "privacy_level": privacy,
                      "disable_comment": False, "disable_duet": False, "disable_stitch": False},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size,
                        "total_chunk_count": 1},
    }
    if not live:
        return {"dry_run": True, "platform": "tiktok", "file": path, "body": body}
    token = os.environ["TIKTOK_ACCESS_TOKEN"]
    _, _, res = http("POST", INIT, {"Authorization": f"Bearer {token}"}, body)
    up = res["data"]["upload_url"]
    http("PUT", up, {"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size - 1}/{size}",
                     "Content-Length": str(size)}, Path(path).read_bytes(), timeout=900)
    return {"platform": "tiktok", "publish_id": res["data"]["publish_id"], "privacy": privacy}
