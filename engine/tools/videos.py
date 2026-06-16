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


def fetch_feed(url: str, tries: int = 3):
    """Parse a YouTube RSS feed with retry — GitHub runners hit transient
    404/429/500 from YouTube under bursty load; a short backoff recovers them."""
    import time

    import feedparser
    feed = None
    for i in range(tries):
        feed = feedparser.parse(url)
        if feed.entries:
            return feed
        status = getattr(feed, "status", 0)
        if status in (200,) and not feed.entries:
            return feed                      # genuinely empty (e.g., brand-new channel)
        time.sleep(1.2 * (i + 1))            # 404/429/500/0 → back off and retry
    return feed


def collect(previous: list | None = None) -> list:
    """previous: prior payload's videos (unused now — channel ids are pinned in config)."""
    import feedparser

    week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=settings.VIDEO_WEEK_DAYS)

    def feed_url(src: dict) -> str:
        key = "playlist_id" if src["kind"] == "playlist" else "channel_id"
        return f"{FEED}{key}={src['ref']}"

    def fetch(src: dict) -> list:
        out = []
        try:
            feed = fetch_feed(feed_url(src))
            for e in feed.entries:                       # scan the whole feed window
                if len(out) >= settings.VIDEO_PER_SOURCE:
                    break
                vid = e.get("yt_videoid") or ""
                pub = e.get("published_parsed")
                link = (e.get("link") or "")
                if not vid or not pub:
                    continue
                if settings.SKIP_SHORTS and "/shorts/" in link:   # drop Shorts
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
                    "channel_id": src["ref"] if src["kind"] == "channel" else "",
                    "category": src["category"],
                    "geo": src["geo"],
                    "url": (link or WATCH + vid),
                    "embed": EMBED + vid,
                    "thumb": thumb,
                    "published": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ts": int(pub_dt.timestamp()),
                    "summary": _clean(e.get("summary") or "")[:500],
                })
        except Exception as ex:  # noqa: BLE001
            print(f"[videos] {src['name']} failed: {ex}")
        return out

    # Refresh the STALEST sources first (missing → oldest), capped per run, so
    # prioritized feeds get an un-throttled attempt; the rest ride on accumulation.
    import random
    fresh_ts = {}
    for v in (previous or []):
        ch = v.get("channel", "")
        fresh_ts[ch] = max(fresh_ts.get(ch, 0), v.get("ts", 0))
    srcs = list(settings.VIDEO_SOURCES)
    now_s = int(dt.datetime.now(dt.timezone.utc).timestamp())
    random.Random(now_s // 1800).shuffle(srcs)                  # rotate ties each 30-min run
    ordered = sorted(srcs, key=lambda s: fresh_ts.get(s["name"], 0))
    to_fetch = ordered[: getattr(settings, "VIDEO_FETCH_PER_RUN", len(ordered))]

    vids = []
    try:
        with cf.ThreadPoolExecutor(max_workers=4) as ex:   # gentle on YouTube to avoid throttling
            for items in ex.map(fetch, to_fetch):
                vids += items
    except Exception as e:  # noqa: BLE001
        print(f"[videos] fetch pool failed: {e}")

    # ACCUMULATE: YouTube throttles GitHub IPs, so each run only reaches a random
    # subset of feeds. Merge this run's fresh items with the previous payload's
    # still-fresh items (≤window) so a transient feed failure never wipes content —
    # coverage fills in over a few runs and persists until items age out.
    import collections
    week_cut = int(dt.datetime.now(dt.timezone.utc).timestamp()) - settings.VIDEO_WEEK_DAYS * 86400
    by_id = {}
    for v in (previous or []):
        if (v.get("video_id") and v.get("ts", 0) >= week_cut
                and "/shorts/" not in (v.get("url") or "")):
            by_id[v["video_id"]] = v
    for v in vids:                                 # fresh overlays previous (same id)
        by_id[v["video_id"]] = v
    per_ch = collections.defaultdict(list)         # cap newest N per channel → bounded
    for v in sorted(by_id.values(), key=lambda x: x["ts"], reverse=True):
        if len(per_ch[v["channel"]]) < settings.VIDEO_PER_SOURCE:
            per_ch[v["channel"]].append(v)
    out = sorted((v for lst in per_ch.values() for v in lst),
                 key=lambda x: x["ts"], reverse=True)
    fresh_ids = {v["video_id"] for v in vids}
    print(f"[videos] {len(out)} videos (merged, ≤{settings.VIDEO_WEEK_DAYS}d) · "
          f"{len(fresh_ids)} fresh this run · {len(per_ch)} channels")
    return out
