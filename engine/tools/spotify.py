"""Spotify now-playing (baked at cron time via a stored refresh token).

No always-on server: the refresh token mints a short-lived access token each run,
we read the currently-playing track, and bake it into data.json. Returns None
when nothing is playing or no credentials are configured.
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def _access_token() -> str | None:
    if not (settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET
            and settings.SPOTIFY_REFRESH_TOKEN):
        return None
    basic = base64.b64encode(
        f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": settings.SPOTIFY_REFRESH_TOKEN,
        }).encode(),
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=15)).get("access_token")
    except Exception as e:  # noqa: BLE001
        print(f"[spotify] token refresh failed: {e}")
        return None


def now_playing() -> dict | None:
    tok = _access_token()
    if not tok:
        return None
    try:
        req = urllib.request.Request(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status == 204:                 # nothing playing
                return None
            d = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"[spotify] now-playing failed: {e}")
        return None
    item = d.get("item") or {}
    if not item:
        return None
    art = item.get("album", {}).get("images", [])
    return {
        "track": item.get("name", ""),
        "artist": ", ".join(a["name"] for a in item.get("artists", [])),
        "is_playing": bool(d.get("is_playing")),
        "progress_ms": d.get("progress_ms", 0),
        "duration_ms": item.get("duration_ms", 0),
        "art": art[-1]["url"] if art else "",
        "url": item.get("external_urls", {}).get("spotify", ""),
    }
