"""Intelligence Hub — Videos agent.

Captures the latest uploads (≤1 week) from market-update YouTube channels and
playlists (settings.VIDEO_SOURCES), keyless via YouTube's RSS feeds. @handles are
resolved to channel_ids at runtime (cached across runs via `previous`); playlists
use their playlist_id directly. Each video carries title, channel, published date,
thumbnail, an embed-ready id, category and geo, plus a cleaned description used as
the on-expand summary. Degrades to an empty list if YouTube is unreachable.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import re
import sys
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

FEED = "https://www.youtube.com/feeds/videos.xml?"
WATCH = "https://www.youtube.com/watch?v="
EMBED = "https://www.youtube.com/embed/"


def _get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _resolve_channel_id(handle: str, cache: dict) -> str | None:
    h = handle.lstrip("@")
    if h in cache:
        return cache[h]
    cid = None
    try:
        html = _get(f"https://www.youtube.com/@{h}/videos")
        m = (re.search(r'"channelId":"(UC[\w-]+)"', html)
             or re.search(r'channel/(UC[\w-]+)', html))
        cid = m.group(1) if m else None
    except Exception as e:  # noqa: BLE001
        print(f"[videos] channel-id resolve failed @{h}: {e}")
    cache[h] = cid
    return cid


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def collect(previous: list | None = None) -> list:
    """previous: prior payload's videos — reuse resolved channel ids to skip lookups."""
    import feedparser

    week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=settings.VIDEO_WEEK_DAYS)
    id_cache = {}
    for v in (previous or []):
        if v.get("channel_handle") and v.get("channel_id"):
            id_cache[v["channel_handle"].lstrip("@")] = v["channel_id"]

    def feed_url(src: dict) -> str | None:
        if src["kind"] == "playlist":
            return FEED + "playlist_id=" + src["ref"]
        cid = _resolve_channel_id(src["ref"], id_cache)
        return (FEED + "channel_id=" + cid) if cid else None

    def fetch(src: dict) -> list:
        url = feed_url(src)
        if not url:
            return []
        out = []
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[: settings.VIDEO_PER_SOURCE]:
                vid = e.get("yt_videoid") or ""
                pub = e.get("published_parsed")
                if not vid or not pub:
                    continue
                pub_dt = dt.datetime(*pub[:6], tzinfo=dt.timezone.utc)
                if pub_dt < week_ago:
                    continue
                mt = e.get("media_thumbnail")
                thumb = (mt[0].get("url") if mt else "") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                out.append({
                    "video_id": vid,
                    "title": (e.get("title") or "").strip()[:200],
                    "channel": src["name"],
                    "channel_handle": src["ref"] if src["kind"] == "channel" else "",
                    "channel_id": id_cache.get(src["ref"].lstrip("@"), "") if src["kind"] == "channel" else "",
                    "category": src["category"],
                    "geo": src["geo"],
                    "url": WATCH + vid,
                    "embed": EMBED + vid,
                    "thumb": thumb,
                    "published": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ts": int(pub_dt.timestamp()),
                    "summary": _clean(e.get("summary") or "")[:500],
                })
        except Exception as ex:  # noqa: BLE001
            print(f"[videos] {src['name']} failed: {ex}")
        return out

    vids = []
    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for items in ex.map(fetch, settings.VIDEO_SOURCES):
                vids += items
    except Exception as e:  # noqa: BLE001
        print(f"[videos] fetch pool failed: {e}")

    # de-dup by video_id (a clip can appear in several playlists), newest first
    seen, uniq = set(), []
    for v in sorted(vids, key=lambda v: v["ts"], reverse=True):
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            uniq.append(v)
    print(f"[videos] {len(uniq)} videos (≤{settings.VIDEO_WEEK_DAYS}d) "
          f"from {len(settings.VIDEO_SOURCES)} sources")
    return uniq
