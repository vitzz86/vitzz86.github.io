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
import collections
import datetime as dt
import re
import sys
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

FEED = "https://www.youtube.com/feeds/videos.xml?"
WATCH = "https://www.youtube.com/watch?v="
EMBED = "https://www.youtube.com/embed/"
LAST_AUDIT = {}


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


def _bad_title(title: str) -> bool:
    t = (title or "").strip().lower()
    return not t or t in {"private video", "deleted video"} or "video unavailable" in t


def _iso_dur(s: str) -> int | None:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return None
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def _api_durations(ids: list) -> dict:
    import json
    out = {}
    key = settings.YOUTUBE_API_KEY
    for i in range(0, len(ids), 50):
        batch = ",".join(ids[i:i + 50])
        url = ("https://www.googleapis.com/youtube/v3/videos?part=contentDetails"
               f"&id={batch}&key={key}")
        data = json.loads(_get(url, timeout=25))
        for it in data.get("items", []):
            out[it["id"]] = _iso_dur(it.get("contentDetails", {}).get("duration", ""))
    return out


def _api_uploads_playlist(kind: str, ref: str) -> str:
    """Return the playlist id to query. Channel refs may be UC ids or @handles."""
    if kind != "channel":
        return ref
    if ref.startswith("UC"):
        return "UU" + ref[2:]
    import json
    key = settings.YOUTUBE_API_KEY
    handle = ref if ref.startswith("@") else "@" + ref
    url = ("https://www.googleapis.com/youtube/v3/channels"
           f"?part=contentDetails&forHandle={handle}&key={key}")
    data = json.loads(_get(url, timeout=25))
    items = data.get("items") or []
    if not items:
        raise ValueError(f"channel handle unresolved: {ref}")
    uploads = (items[0].get("contentDetails", {})
               .get("relatedPlaylists", {})
               .get("uploads"))
    if not uploads:
        raise ValueError(f"uploads playlist missing: {ref}")
    return uploads


def _api_entries(kind: str, ref: str) -> list:
    """Pull recent uploads via the YouTube Data API (channel uploads playlist UU…,
    or an explicit playlist). Returns RSS-shaped dicts so the existing loops work;
    Shorts are flagged (link → /shorts/) via a batched duration lookup."""
    import json
    key = settings.YOUTUBE_API_KEY
    playlist = _api_uploads_playlist(kind, ref)
    url = ("https://www.googleapis.com/youtube/v3/playlistItems?part=snippet"
           f"&maxResults=20&playlistId={playlist}&key={key}")
    data = json.loads(_get(url, timeout=25))
    out, vids = [], []
    for it in data.get("items", []):
        sn = it.get("snippet", {})
        vid = (sn.get("resourceId") or {}).get("videoId")
        if not vid:
            continue
        pp = None
        try:
            d = dt.datetime.strptime(sn.get("publishedAt", ""), "%Y-%m-%dT%H:%M:%SZ")
            pp = (d.year, d.month, d.day, d.hour, d.minute, d.second, 0, 0, 0)
        except Exception:  # noqa: BLE001
            pass
        thumbs = sn.get("thumbnails", {})
        th = ((thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {})
              .get("url", ""))
        out.append({"yt_videoid": vid, "title": sn.get("title", ""),
                    "link": WATCH + vid, "published_parsed": pp,
                    "media_thumbnail": [{"url": th}] if th else None,
                    "summary": sn.get("description", "")})
        vids.append(vid)
    if vids:
        try:
            durs = _api_durations(vids)
            for e in out:
                d = durs.get(e["yt_videoid"])
                e["_dur"] = d                          # seconds (used for Shorts + 5-min podcast filter)
                if settings.SKIP_SHORTS and d is not None and d <= 70:
                    e["link"] = EMBED.replace("/embed/", "/shorts/") + e["yt_videoid"]
        except Exception as ex:  # noqa: BLE001
            print(f"[yt-api] duration lookup failed: {ex}")
    return out


def get_feed(kind: str, ref: str):
    """API-first (full coverage, no GitHub-IP throttle) with automatic RSS fallback."""
    import types
    if settings.YOUTUBE_API_KEY:
        try:
            entries = _api_entries(kind, ref)
            if entries:
                return types.SimpleNamespace(entries=entries, status=200)
        except Exception as e:  # noqa: BLE001
            print(f"[yt-api] {ref} failed → RSS fallback: {e}")
    key = "playlist_id" if kind == "playlist" else "channel_id"
    rss_ref = ref
    if kind == "channel" and not ref.startswith("UC"):
        rss_ref = _resolve_channel_id(ref, {}) or ref
    return fetch_feed(f"{FEED}{key}={rss_ref}")


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
            feed = get_feed(src["kind"], src["ref"])
            for e in feed.entries:                       # scan the whole feed window
                if len(out) >= settings.VIDEO_PER_SOURCE:
                    break
                vid = e.get("yt_videoid") or ""
                pub = e.get("published_parsed")
                link = (e.get("link") or "")
                if not vid or not pub:
                    continue
                title = (e.get("title") or "").strip()
                if _bad_title(title):
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
                    "title": title[:200],
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
    week_cut = int(dt.datetime.now(dt.timezone.utc).timestamp()) - settings.VIDEO_WEEK_DAYS * 86400
    valid_channels = {s["name"] for s in settings.VIDEO_SOURCES}
    by_id = {}
    for v in (previous or []):
        if (v.get("video_id") and v.get("ts", 0) >= week_cut
                and "/shorts/" not in (v.get("url") or "")
                and not _bad_title(v.get("title", ""))
                and v.get("channel") in valid_channels):   # drop sources removed from config
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
    present = {v["channel"] for v in out}
    missing = [s["name"] for s in settings.VIDEO_SOURCES if s["name"] not in present]
    source_counts = collections.Counter(v.get("channel") or "UNKNOWN" for v in out)
    category_counts = collections.Counter(v.get("category") or "UNKNOWN" for v in out)
    geo_counts = collections.Counter(v.get("geo") or "UNKNOWN" for v in out)
    fresh_by_source = collections.Counter(v.get("channel") or "UNKNOWN" for v in vids)
    global LAST_AUDIT
    LAST_AUDIT = {
        "video_count": len(out),
        "fresh_this_run": len(fresh_ids),
        "source_total": len(settings.VIDEO_SOURCES),
        "sources_present": len(present),
        "missing_sources": missing,
        "category": dict(category_counts),
        "geo": dict(geo_counts),
        "top_sources": dict(source_counts.most_common(12)),
        "fresh_by_source": dict(fresh_by_source.most_common(12)),
        "fetch_per_run": getattr(settings, "VIDEO_FETCH_PER_RUN", len(settings.VIDEO_SOURCES)),
        "window_days": settings.VIDEO_WEEK_DAYS,
    }
    print(f"[videos] {len(out)} videos (merged, ≤{settings.VIDEO_WEEK_DAYS}d) · "
          f"{len(fresh_ids)} fresh this run · {len(present)}/{len(settings.VIDEO_SOURCES)} sources")
    if missing:
        print(f"[videos] stale/missing (prioritized next run): {missing}")
    return out


def audit(items: list | None = None) -> dict:
    if LAST_AUDIT:
        return dict(LAST_AUDIT)
    rows = items or []
    present = {v.get("channel") for v in rows if v.get("channel")}
    return {
        "video_count": len(rows),
        "fresh_this_run": 0,
        "source_total": len(settings.VIDEO_SOURCES),
        "sources_present": len(present),
        "missing_sources": [s["name"] for s in settings.VIDEO_SOURCES if s["name"] not in present],
        "category": dict(collections.Counter(v.get("category") or "UNKNOWN" for v in rows)),
        "geo": dict(collections.Counter(v.get("geo") or "UNKNOWN" for v in rows)),
        "top_sources": dict(collections.Counter(v.get("channel") or "UNKNOWN" for v in rows).most_common(12)),
        "fresh_by_source": {},
        "fetch_per_run": getattr(settings, "VIDEO_FETCH_PER_RUN", len(settings.VIDEO_SOURCES)),
        "window_days": settings.VIDEO_WEEK_DAYS,
    }
