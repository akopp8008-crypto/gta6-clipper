"""Post clips through the official APIs only (YouTube, TikTok, Instagram).

Every publisher defaults to dry run: it prints what it would send and
posts nothing. Pass live=True (CLI: --live) to really post.
"""
from __future__ import annotations

import json
import urllib.request


def http(method: str, url: str, headers: dict | None = None, body: bytes | dict | None = None,
         timeout: int = 300) -> tuple[int, dict, dict]:
    headers = dict(headers or {})
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json; charset=UTF-8")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"raw": raw[:200].decode(errors="ignore")}
        return r.status, dict(r.headers), data
